import java.io.EOFException;
import java.io.FileInputStream;
import java.io.ObjectInputStream;
import java.io.PrintStream;
import java.lang.reflect.Method;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Paths;
import java.time.temporal.TemporalAccessor;
import java.util.ArrayDeque;
import java.util.ArrayList;
import java.util.Collection;
import java.util.Collections;
import java.util.Comparator;
import java.util.Deque;
import java.util.HashMap;
import java.util.IdentityHashMap;
import java.util.LinkedHashMap;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;

/**
 * Like BObjectDump, but driven by the abstraction function JSON written by abstraction_function.py
 * (format besser-abstraction-function/1.0) instead of the BESSER annotations: the Java classes carry
 * no annotations. Java 8, no dependencies. Same output format as BObjectDump.
 *
 * <pre>
 *   verify  abstraction.json                     check the compiled classes against the abstraction
 *   dump    abstraction.json objects.ser [max]   object graphs -> object-diagram JSON
 * </pre>
 *
 * The abstraction only knows simple Java type names; the package of the classes (all in the same one)
 * is given with -Dbesser.package=pkg (default: the default package).
 */
public final class BAbstractionDump {
    /** Upper bound used for "*" (same value as BTrace.MANY). */
    static final int MANY = -1;

    private BAbstractionDump() {
    }

    public static void main(String[] args) throws Exception {
        boolean verify = args.length == 2 && args[0].equals("verify");
        boolean dump = (args.length == 3 || args.length == 4) && args[0].equals("dump");
        if (!verify && !dump) {
            System.err.println("Usage: java BAbstractionDump verify <abstraction.json>"
                    + " | dump <abstraction.json> <in.ser> [max-structures]");
            System.exit(2);
        }
        Abstraction abstraction = new Abstraction(args[1], System.getProperty("besser.package", ""));
        if (verify) {
            List<String> problems = abstraction.verify();
            for (String problem : problems)
                System.out.println(problem);
            System.exit(problems.isEmpty() ? 0 : 1);
        }
        int max = args.length == 4 ? Integer.parseInt(args[3]) : Integer.MAX_VALUE;
        if (max < 1)
            throw new IllegalArgumentException("max-structures must be greater than zero");
        List<Object> structures = new ArrayList<Object>();
        try (ObjectInputStream in = new ObjectInputStream(new FileInputStream(args[2]))) {
            while (structures.size() < max) {
                try {
                    structures.add(abstraction.serializeStructure(in.readObject()));
                } catch (EOFException end) {
                    break;
                }
            }
        }
        Json.write(structures, System.out);
        System.out.println();
    }

    // =====================================================================================
    // Abstraction model (view of the JSON) and the abstraction function itself
    // =====================================================================================

    static final class Attribute {
        String id, name, type, getter;
    }

    static final class End {
        String associationId, association, id, name, type, opposite, owner, getter, adder, setter;
        int lower, upper;
    }

    static final class ClassInfo {
        String id, name, javaType;
        List<String> parents = new ArrayList<String>();
        List<Attribute> attributes = new ArrayList<Attribute>();
        List<End> ends = new ArrayList<End>();   // ends realized as a field of this Java class
    }

    static final class EnumInfo {
        String name, javaType;
        Map<String, String> literals = new LinkedHashMap<String, String>();   // Java constant -> B-UML literal
    }

    static final class Abstraction {
        final String model, javaPackage;
        final Map<String, ClassInfo> classes = new LinkedHashMap<String, ClassInfo>();   // by B-UML name
        final Map<String, ClassInfo> classesByJava = new HashMap<String, ClassInfo>();
        final Map<String, EnumInfo> enumsByJava = new HashMap<String, EnumInfo>();
        final Map<ClassInfo, List<Attribute>> attributeCache = new HashMap<ClassInfo, List<Attribute>>();
        final Map<ClassInfo, List<End>> endCache = new HashMap<ClassInfo, List<End>>();

        Abstraction(String path, String javaPackage) throws Exception {
            this.javaPackage = javaPackage;
            Map<String, Object> root = Json.object(
                    Json.parse(new String(Files.readAllBytes(Paths.get(path)), StandardCharsets.UTF_8)));
            model = Json.string(Json.object(root.get("model")), "name");

            for (Object e : Json.list(root.get("enumerations"))) {
                Map<String, Object> enumeration = Json.object(e);
                EnumInfo info = new EnumInfo();
                info.name = Json.string(enumeration, "name");
                info.javaType = Json.string(Json.object(enumeration.get("java")), "type");
                for (Object l : Json.list(enumeration.get("literals"))) {
                    Map<String, Object> literal = Json.object(l);
                    info.literals.put(Json.string(Json.object(literal.get("java")), "constant"),
                            Json.string(literal, "name"));
                }
                enumsByJava.put(info.javaType, info);
            }

            for (Object c : Json.list(root.get("classes"))) {
                Map<String, Object> cls = Json.object(c);
                ClassInfo info = new ClassInfo();
                info.id = Json.string(cls, "id");
                info.name = Json.string(cls, "name");
                info.javaType = Json.string(Json.object(cls.get("java")), "type");
                for (Object p : Json.list(cls.get("parents")))
                    info.parents.add((String) p);
                for (Object a : Json.list(cls.get("attributes"))) {
                    Map<String, Object> attribute = Json.object(a);
                    Attribute item = new Attribute();
                    item.id = Json.string(attribute, "id");
                    item.name = Json.string(attribute, "name");
                    item.type = Json.string(attribute, "type");
                    item.getter = Json.string(Json.object(attribute.get("java")), "get");
                    info.attributes.add(item);
                }
                classes.put(info.name, info);
                classesByJava.put(info.javaType, info);
            }

            for (Object a : Json.list(root.get("associations"))) {
                Map<String, Object> association = Json.object(a);
                for (Object e : Json.list(association.get("ends"))) {
                    Map<String, Object> end = Json.object(e);
                    if (end.get("java") == null)
                        continue;   // no Java class holds this end
                    Map<String, Object> java = Json.object(end.get("java"));
                    End item = new End();
                    item.associationId = Json.string(association, "id");
                    item.association = Json.string(association, "name");
                    item.id = Json.string(end, "id");
                    item.name = Json.string(end, "name");
                    item.type = Json.string(end, "type");
                    item.opposite = (String) end.get("opposite");
                    item.lower = ((Number) end.get("lower")).intValue();
                    item.upper = end.get("upper") instanceof Number ? ((Number) end.get("upper")).intValue() : MANY;
                    item.owner = Json.string(java, "owner");
                    item.getter = Json.string(java, "get");
                    item.adder = (String) java.get("add");
                    item.setter = (String) java.get("set");
                    ClassInfo owner = classes.get(item.owner);
                    if (owner == null)
                        throw new IllegalArgumentException("Association end " + item.name
                                + " is owned by unknown class " + item.owner);
                    owner.ends.add(item);
                }
            }
        }

        /** The class and its ancestors, breadth first (a class before its parents). */
        List<ClassInfo> lineage(ClassInfo cls) {
            Set<ClassInfo> seen = new LinkedHashSet<ClassInfo>();
            Deque<ClassInfo> todo = new ArrayDeque<ClassInfo>(Collections.singletonList(cls));
            while (!todo.isEmpty()) {
                ClassInfo current = todo.removeFirst();
                if (seen.add(current))
                    for (String parent : current.parents)
                        if (classes.containsKey(parent))
                            todo.addLast(classes.get(parent));
            }
            return new ArrayList<ClassInfo>(seen);
        }

        /** Own and inherited attributes, sorted by getter name (the order BObjectDump uses). */
        List<Attribute> attributes(ClassInfo cls) {
            List<Attribute> result = attributeCache.get(cls);
            if (result == null) {
                Map<String, Attribute> byGetter = new LinkedHashMap<String, Attribute>();
                for (ClassInfo c : lineage(cls))
                    for (Attribute a : c.attributes)
                        if (!byGetter.containsKey(a.getter))   // a subclass getter overrides the parent's
                            byGetter.put(a.getter, a);
                result = new ArrayList<Attribute>(byGetter.values());
                Collections.sort(result, new Comparator<Attribute>() {
                    @Override
                    public int compare(Attribute left, Attribute right) {
                        return left.getter.compareTo(right.getter);
                    }
                });
                attributeCache.put(cls, result);
            }
            return result;
        }

        /** Own and inherited association ends, sorted by getter name. */
        List<End> ends(ClassInfo cls) {
            List<End> result = endCache.get(cls);
            if (result == null) {
                Map<String, End> byGetter = new LinkedHashMap<String, End>();
                for (ClassInfo c : lineage(cls))
                    for (End e : c.ends)
                        if (!byGetter.containsKey(e.getter))
                            byGetter.put(e.getter, e);
                result = new ArrayList<End>(byGetter.values());
                Collections.sort(result, new Comparator<End>() {
                    @Override
                    public int compare(End left, End right) {
                        return left.getter.compareTo(right.getter);
                    }
                });
                endCache.put(cls, result);
            }
            return result;
        }

        ClassInfo classOf(Object object) {
            ClassInfo result = classesByJava.get(object.getClass().getSimpleName());
            if (result == null)
                throw new IllegalArgumentException("Reachable object " + object.getClass().getName()
                        + " is not a class of the abstraction function");
            return result;
        }

        Class<?> load(String javaType) throws ClassNotFoundException {
            return Class.forName(javaPackage.isEmpty() ? javaType : javaPackage + "." + javaType);
        }

        // --------------------------------------------------------------------- verify

        /** Everything the abstraction names must exist in the compiled classes. */
        List<String> verify() {
            List<String> problems = new ArrayList<String>();
            for (EnumInfo e : enumsByJava.values()) {
                try {
                    Class<?> type = load(e.javaType);
                    if (!type.isEnum())
                        problems.add("enumeration " + e.name + ": " + type.getName() + " is not an enum");
                    for (String constant : e.literals.keySet())
                        try {
                            type.getField(constant);
                        } catch (NoSuchFieldException missing) {
                            problems.add("enumeration " + e.name + ": no constant " + constant);
                        }
                } catch (ClassNotFoundException missing) {
                    problems.add("enumeration " + e.name + ": class " + missing.getMessage() + " not found");
                }
            }
            for (ClassInfo c : classes.values()) {
                Class<?> type;
                try {
                    type = load(c.javaType);
                } catch (ClassNotFoundException missing) {
                    problems.add("class " + c.name + ": class " + missing.getMessage() + " not found");
                    continue;
                }
                for (Attribute a : c.attributes)
                    checkMethod(problems, type, "attribute " + c.name + "." + a.name, a.getter);
                for (End e : c.ends) {
                    String what = "association end " + e.association + "." + e.name + " (in " + c.name + ")";
                    checkMethod(problems, type, what, e.getter);
                    ClassInfo target = classes.get(e.type);
                    Class<?> targetType = null;
                    try {
                        targetType = target == null ? null : load(target.javaType);
                    } catch (ClassNotFoundException missing) {
                        // reported for the target class itself
                    }
                    if (targetType == null)
                        continue;
                    if (e.adder != null)
                        checkMethod(problems, type, what, e.adder, targetType);
                    if (e.setter != null)
                        checkMethod(problems, type, what, e.setter, targetType);
                }
            }
            return problems;
        }

        private static void checkMethod(List<String> problems, Class<?> type, String what, String name,
                                        Class<?>... parameters) {
            try {
                type.getMethod(name, parameters);
            } catch (NoSuchMethodException missing) {
                StringBuilder signature = new StringBuilder();
                for (Class<?> p : parameters)
                    signature.append(signature.length() == 0 ? "" : ", ").append(p.getSimpleName());
                problems.add(what + ": " + type.getName() + " has no public method " + name + "(" + signature + ")");
            }
        }

        // --------------------------------------------------------------------- dump

        Map<String, Object> serializeStructure(Object root) throws Exception {
            Map<Object, String> ids = new IdentityHashMap<Object, String>();
            Deque<Object> pending = new ArrayDeque<Object>();
            List<Object> objects = new ArrayList<Object>();
            Map<String, Map<String, Object>> links = new LinkedHashMap<String, Map<String, Object>>();

            classOf(root);
            ids.put(root, "o1");
            pending.add(root);
            while (!pending.isEmpty()) {
                Object object = pending.removeFirst();
                ClassInfo classInfo = classOf(object);
                Map<String, Object> entry = new LinkedHashMap<String, Object>();
                entry.put("id", ids.get(object));
                entry.put("class", classInfo.name);
                entry.put("classId", classInfo.id);

                List<Object> attributes = new ArrayList<Object>();
                for (Attribute attribute : attributes(classInfo)) {
                    Map<String, Object> item = new LinkedHashMap<String, Object>();
                    item.put("id", attribute.id);
                    item.put("name", attribute.name);
                    item.put("type", attribute.type);
                    item.put("value", jsonValue(invoke(object, attribute.getter)));
                    attributes.add(item);
                }
                entry.put("attributes", attributes);
                objects.add(entry);

                for (End end : ends(classInfo)) {
                    for (Object target : targets(invoke(object, end.getter))) {
                        if (target == null)
                            continue;
                        ClassInfo targetInfo = classOf(target);
                        if (!ids.containsKey(target)) {
                            ids.put(target, "o" + (ids.size() + 1));
                            pending.addLast(target);
                        }
                        String sourceId = ids.get(object);
                        String targetId = ids.get(target);
                        boolean ordered = sourceId.compareTo(targetId) < 0;
                        String key = end.associationId + ":" + (ordered ? sourceId : targetId) + ":"
                                + (ordered ? targetId : sourceId);
                        if (!links.containsKey(key)) {
                            Map<String, Object> link = new LinkedHashMap<String, Object>();
                            link.put("associationId", end.associationId);
                            link.put("association", end.association);
                            link.put("source", sourceId);
                            link.put("sourceClass", classInfo.name);
                            link.put("sourceEndId", end.id);
                            link.put("sourceEnd", end.name);
                            link.put("sourceEndLower", end.lower);
                            link.put("sourceEndUpper", end.upper);
                            link.put("target", targetId);
                            link.put("targetClass", targetInfo.name);
                            link.put("targetEnd", end.opposite);
                            links.put(key, link);
                        }
                    }
                }
            }

            Map<String, Object> structure = new LinkedHashMap<String, Object>();
            structure.put("model", model);
            structure.put("root", "o1");
            structure.put("objects", objects);
            structure.put("links", new ArrayList<Object>(links.values()));
            return structure;
        }

        private static Object invoke(Object object, String getter) throws Exception {
            Method method = object.getClass().getMethod(getter);
            return method.invoke(object);
        }

        private static Collection<?> targets(Object value) {
            if (value == null)
                return Collections.emptyList();
            if (value instanceof Collection<?>)
                return (Collection<?>) value;
            if (value instanceof Iterable<?>) {
                List<Object> result = new ArrayList<Object>();
                for (Object item : (Iterable<?>) value)
                    result.add(item);
                return result;
            }
            if (value.getClass().isArray()) {
                List<Object> result = new ArrayList<Object>();
                for (int i = 0; i < java.lang.reflect.Array.getLength(value); i++)
                    result.add(java.lang.reflect.Array.get(value, i));
                return result;
            }
            return Collections.singletonList(value);
        }

        private Object jsonValue(Object value) {
            if (value == null || value instanceof String || value instanceof Number || value instanceof Boolean)
                return value;
            if (value instanceof Enum<?>) {
                Enum<?> constant = (Enum<?>) value;
                EnumInfo info = enumsByJava.get(constant.getDeclaringClass().getSimpleName());
                if (info == null)
                    throw new IllegalArgumentException("Enum " + constant.getDeclaringClass().getName()
                            + " is not an enumeration of the abstraction function");
                String literal = info.literals.get(constant.name());
                Map<String, Object> result = new LinkedHashMap<String, Object>();
                result.put("enumeration", info.name);
                result.put("literal", literal == null ? constant.name() : literal);
                return result;
            }
            if (value instanceof Character)
                return value.toString();
            if (value instanceof TemporalAccessor)
                return value.toString();
            throw new IllegalArgumentException("Unsupported attribute value type: " + value.getClass().getName());
        }
    }

    // =====================================================================================
    // Minimal JSON reader / writer
    // =====================================================================================

    static final class Json {
        private final String text;
        private int pos;

        private Json(String text) {
            this.text = text;
        }

        static Object parse(String text) {
            Json parser = new Json(text);
            Object value = parser.value();
            parser.skipSpaces();
            if (parser.pos != text.length())
                throw parser.error("unexpected trailing content");
            return value;
        }

        @SuppressWarnings("unchecked")
        static Map<String, Object> object(Object value) {
            if (!(value instanceof Map))
                throw new IllegalArgumentException("JSON object expected, found " + value);
            return (Map<String, Object>) value;
        }

        @SuppressWarnings("unchecked")
        static List<Object> list(Object value) {
            return value == null ? Collections.emptyList() : (List<Object>) value;
        }

        static String string(Map<String, Object> object, String key) {
            Object value = object.get(key);
            if (!(value instanceof String))
                throw new IllegalArgumentException("JSON key '" + key + "' must be a string in " + object);
            return (String) value;
        }

        private Object value() {
            skipSpaces();
            if (pos >= text.length())
                throw error("unexpected end of input");
            char c = text.charAt(pos);
            if (c == '{') {
                pos++;
                Map<String, Object> result = new LinkedHashMap<String, Object>();
                skipSpaces();
                if (peek('}'))
                    return result;
                do {
                    skipSpaces();
                    String key = stringLiteral();
                    skipSpaces();
                    expect(':');
                    result.put(key, value());
                    skipSpaces();
                } while (peek(','));
                expect('}');
                return result;
            }
            if (c == '[') {
                pos++;
                List<Object> result = new ArrayList<Object>();
                skipSpaces();
                if (peek(']'))
                    return result;
                do {
                    result.add(value());
                    skipSpaces();
                } while (peek(','));
                expect(']');
                return result;
            }
            if (c == '"')
                return stringLiteral();
            if (text.startsWith("true", pos)) {
                pos += 4;
                return Boolean.TRUE;
            }
            if (text.startsWith("false", pos)) {
                pos += 5;
                return Boolean.FALSE;
            }
            if (text.startsWith("null", pos)) {
                pos += 4;
                return null;
            }
            int start = pos;
            while (pos < text.length() && "+-0123456789.eE".indexOf(text.charAt(pos)) >= 0)
                pos++;
            if (start == pos)
                throw error("unexpected character '" + c + "'");
            String number = text.substring(start, pos);
            if (number.contains(".") || number.contains("e") || number.contains("E"))
                return Double.valueOf(number);
            return Long.valueOf(number);
        }

        private String stringLiteral() {
            expect('"');
            StringBuilder result = new StringBuilder();
            while (true) {
                if (pos >= text.length())
                    throw error("unterminated string");
                char c = text.charAt(pos++);
                if (c == '"')
                    return result.toString();
                if (c != '\\') {
                    result.append(c);
                    continue;
                }
                char escaped = text.charAt(pos++);
                switch (escaped) {
                    case 'b': result.append('\b'); break;
                    case 'f': result.append('\f'); break;
                    case 'n': result.append('\n'); break;
                    case 'r': result.append('\r'); break;
                    case 't': result.append('\t'); break;
                    case 'u':
                        result.append((char) Integer.parseInt(text.substring(pos, pos + 4), 16));
                        pos += 4;
                        break;
                    default: result.append(escaped);   // " \ /
                }
            }
        }

        private void skipSpaces() {
            while (pos < text.length() && Character.isWhitespace(text.charAt(pos)))
                pos++;
        }

        private boolean peek(char c) {
            if (pos < text.length() && text.charAt(pos) == c) {
                pos++;
                return true;
            }
            return false;
        }

        private void expect(char c) {
            if (!peek(c))
                throw error("'" + c + "' expected");
        }

        private IllegalArgumentException error(String message) {
            return new IllegalArgumentException("Invalid JSON at offset " + pos + ": " + message);
        }

        static void write(Object value, PrintStream output) {
            if (value == null) {
                output.print("null");
            } else if (value instanceof String) {
                output.print('"');
                String text = (String) value;
                for (int i = 0; i < text.length(); i++) {
                    char c = text.charAt(i);
                    switch (c) {
                        case '"': output.print("\\\""); break;
                        case '\\': output.print("\\\\"); break;
                        case '\b': output.print("\\b"); break;
                        case '\f': output.print("\\f"); break;
                        case '\n': output.print("\\n"); break;
                        case '\r': output.print("\\r"); break;
                        case '\t': output.print("\\t"); break;
                        default:
                            if (c < 0x20)
                                output.printf("\\u%04x", (int) c);
                            else
                                output.print(c);
                    }
                }
                output.print('"');
            } else if (value instanceof Number || value instanceof Boolean) {
                output.print(value);
            } else if (value instanceof Map<?, ?>) {
                output.print('{');
                boolean first = true;
                for (Map.Entry<?, ?> entry : ((Map<?, ?>) value).entrySet()) {
                    if (!first)
                        output.print(',');
                    write(String.valueOf(entry.getKey()), output);
                    output.print(':');
                    write(entry.getValue(), output);
                    first = false;
                }
                output.print('}');
            } else if (value instanceof Iterable<?>) {
                output.print('[');
                boolean first = true;
                for (Object item : (Iterable<?>) value) {
                    if (!first)
                        output.print(',');
                    write(item, output);
                    first = false;
                }
                output.print(']');
            } else {
                throw new IllegalArgumentException("Cannot encode JSON value " + value.getClass().getName());
            }
        }
    }
}
