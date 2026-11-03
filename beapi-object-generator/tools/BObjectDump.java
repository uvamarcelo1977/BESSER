import besser.trace.BAssociationEnd;
import besser.trace.BAttribute;
import besser.trace.BClass;
import besser.trace.BEnumeration;
import besser.trace.BLiteral;

import java.io.EOFException;
import java.io.FileInputStream;
import java.io.ObjectInputStream;
import java.lang.reflect.Method;
import java.time.temporal.TemporalAccessor;
import java.util.ArrayDeque;
import java.util.ArrayList;
import java.util.Collection;
import java.util.Collections;
import java.util.Comparator;
import java.util.Deque;
import java.util.IdentityHashMap;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

public final class BObjectDump {
    private BObjectDump() {
    }

    public static void main(String[] args) throws Exception {
        if (args.length < 1 || args.length > 2) {
            System.err.println("Usage: java BObjectDump <input.ser> [max-structures]");
            System.exit(2);
        }

        int max = args.length == 2 ? Integer.parseInt(args[1]) : Integer.MAX_VALUE;
        if (max < 1) {
            throw new IllegalArgumentException("max-structures must be greater than zero");
        }

        List<Object> structures = new ArrayList<Object>();
        try (ObjectInputStream in = new ObjectInputStream(new FileInputStream(args[0]))) {
            while (structures.size() < max) {
                try {
                    structures.add(serializeStructure(in.readObject()));
                } catch (EOFException end) {
                    break;
                }
            }
        }
        writeJson(structures, System.out);
        System.out.println();
    }

    private static Map<String, Object> serializeStructure(Object root) throws Exception {
        BClass rootClass = classAnnotation(root);
        Map<Object, String> ids = new IdentityHashMap<Object, String>();
        Deque<Object> pending = new ArrayDeque<Object>();
        List<Object> objects = new ArrayList<Object>();
        Map<String, Map<String, Object>> links = new LinkedHashMap<String, Map<String, Object>>();

        ids.put(root, "o1");
        pending.add(root);
        while (!pending.isEmpty()) {
            Object object = pending.removeFirst();
            BClass classInfo = classAnnotation(object);
            Map<String, Object> entry = new LinkedHashMap<String, Object>();
            entry.put("id", ids.get(object));
            entry.put("class", classInfo.name());
            entry.put("classId", classInfo.id());

            List<Method> methods = annotatedMethods(object.getClass());
            List<Object> attributes = new ArrayList<Object>();
            for (Method method : methods) {
                BAttribute attribute = method.getAnnotation(BAttribute.class);
                if (attribute == null)
                    continue;
                Map<String, Object> item = new LinkedHashMap<String, Object>();
                item.put("id", attribute.id());
                item.put("name", attribute.name());
                item.put("type", attribute.type());
                item.put("value", jsonValue(method.invoke(object)));
                attributes.add(item);
            }
            entry.put("attributes", attributes);
            objects.add(entry);

            for (Method method : methods) {
                BAssociationEnd end = method.getAnnotation(BAssociationEnd.class);
                if (end == null)
                    continue;
                Object value = method.invoke(object);
                for (Object target : associationTargets(value)) {
                    if (target == null)
                        continue;
                    classAnnotation(target);
                    if (!ids.containsKey(target)) {
                        ids.put(target, "o" + (ids.size() + 1));
                        pending.addLast(target);
                    }
                    String sourceId = ids.get(object);
                    String targetId = ids.get(target);
                    String first = sourceId.compareTo(targetId) < 0 ? sourceId : targetId;
                    String second = sourceId.compareTo(targetId) < 0 ? targetId : sourceId;
                    String key = end.associationId() + ":" + first + ":" + second;
                    if (!links.containsKey(key)) {
                        Map<String, Object> link = new LinkedHashMap<String, Object>();
                        link.put("associationId", end.associationId());
                        link.put("association", end.association());
                        link.put("source", sourceId);
                        link.put("sourceClass", classInfo.name());
                        link.put("sourceEndId", end.id());
                        link.put("sourceEnd", end.name());
                        link.put("sourceEndLower", end.lower());
                        link.put("sourceEndUpper", end.upper());
                        link.put("target", targetId);
                        link.put("targetClass", classAnnotation(target).name());
                        link.put("targetEnd", end.opposite());
                        links.put(key, link);
                    }
                }
            }
        }

        Map<String, Object> structure = new LinkedHashMap<String, Object>();
        structure.put("model", rootClass.model());
        structure.put("root", "o1");
        structure.put("objects", objects);
        structure.put("links", new ArrayList<Object>(links.values()));
        return structure;
    }

    private static BClass classAnnotation(Object object) {
        BClass result = object.getClass().getAnnotation(BClass.class);
        if (result == null) {
            throw new IllegalArgumentException(
                    "Reachable object " + object.getClass().getName() + " has no @BClass annotation");
        }
        return result;
    }

    private static List<Method> annotatedMethods(Class<?> type) {
        List<Method> methods = new ArrayList<Method>();
        for (Method method : type.getMethods()) {
            if (method.getAnnotation(BAttribute.class) != null
                    || method.getAnnotation(BAssociationEnd.class) != null) {
                methods.add(method);
            }
        }
        Collections.sort(methods, new Comparator<Method>() {
            @Override
            public int compare(Method left, Method right) {
                return left.getName().compareTo(right.getName());
            }
        });
        return methods;
    }

    private static Collection<?> associationTargets(Object value) {
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

    private static Object jsonValue(Object value) throws Exception {
        if (value == null || value instanceof String || value instanceof Number || value instanceof Boolean)
            return value;
        if (value instanceof Enum<?>) {
            Enum<?> enumValue = (Enum<?>) value;
            BEnumeration enumInfo = value.getClass().getAnnotation(BEnumeration.class);
            if (enumInfo == null)
                throw new IllegalArgumentException("Enum " + value.getClass().getName() + " has no @BEnumeration");
            BLiteral literal = value.getClass().getField(enumValue.name()).getAnnotation(BLiteral.class);
            Map<String, Object> result = new LinkedHashMap<String, Object>();
            result.put("enumeration", enumInfo.name());
            result.put("literal", literal == null ? enumValue.name() : literal.name());
            return result;
        }
        if (value instanceof TemporalAccessor)
            return value.toString();
        throw new IllegalArgumentException("Unsupported @BAttribute value type: " + value.getClass().getName());
    }

    private static void writeJson(Object value, java.io.PrintStream output) {
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
                writeJson(String.valueOf(entry.getKey()), output);
                output.print(':');
                writeJson(entry.getValue(), output);
                first = false;
            }
            output.print('}');
        } else if (value instanceof Iterable<?>) {
            output.print('[');
            boolean first = true;
            for (Object item : (Iterable<?>) value) {
                if (!first)
                    output.print(',');
                writeJson(item, output);
                first = false;
            }
            output.print(']');
        } else {
            throw new IllegalArgumentException("Cannot encode JSON value " + value.getClass().getName());
        }
    }
}
