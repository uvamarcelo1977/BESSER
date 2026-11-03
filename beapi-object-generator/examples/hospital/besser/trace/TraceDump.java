import besser.trace.*;
import java.lang.reflect.AnnotatedElement;
import java.lang.reflect.Member;
import java.util.stream.Stream;

public class TraceDump {
    public static void main(String[] args) throws Exception {
        for (String className : args) {
            Class<?> c = Class.forName(className);
            BClass bc = c.getAnnotation(BClass.class);
            if (bc == null) continue;
            System.out.println(bc.name() + " -> " + c.getName() + "  [" + bc.id() + "]");
            Stream.concat(Stream.of(c.getDeclaredFields()), Stream.of(c.getDeclaredMethods()))
                .forEach(m -> {
                    BAttribute a = ((AnnotatedElement) m).getAnnotation(BAttribute.class);
                    BAssociationEnd e = ((AnnotatedElement) m).getAnnotation(BAssociationEnd.class);
                    String javaName = ((Member) m).getName();
                    if (a != null) System.out.println("  attribute " + a.name() + " : " + a.type() + " -> " + javaName);
                    if (e != null) System.out.println("  end       " + e.association() + "." + e.name()
                        + " : " + e.type().getSimpleName() + " -> " + javaName);
                });
        }
    }
}
