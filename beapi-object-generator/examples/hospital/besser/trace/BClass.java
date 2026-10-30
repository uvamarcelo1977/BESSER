package besser.trace;

import java.lang.annotation.Documented;
import java.lang.annotation.ElementType;
import java.lang.annotation.Retention;
import java.lang.annotation.RetentionPolicy;
import java.lang.annotation.Target;

/**
 * Marks a Java type as the implementation of a B-UML class.
 *
 * <p>The {@code id} is the link to the model; keep it unchanged when renaming
 * or restructuring the Java type.
 */
@Documented
@Retention(RetentionPolicy.RUNTIME)
@Target(ElementType.TYPE)
public @interface BClass {

    /** Stable identifier of the model class. */
    String id();

    /** Name of the class in the model. */
    String name();

    /** Name of the B-UML domain model the class belongs to. */
    String model();

    boolean isAbstract() default false;

    /** Java types implementing the model-level parents (generalizations). */
    Class<?>[] parents() default {};
}
