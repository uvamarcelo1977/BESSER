package besser.trace;

import java.lang.annotation.Documented;
import java.lang.annotation.ElementType;
import java.lang.annotation.Retention;
import java.lang.annotation.RetentionPolicy;
import java.lang.annotation.Target;

/**
 * Marks the Java member that realizes a B-UML attribute.
 *
 * <p>Generated on the field. If you change the representation (split the
 * field, change its type, compute it), move the annotation to a no-argument
 * method that returns the model-level value: that method is the trace
 * between your representation and the model.
 */
@Documented
@Retention(RetentionPolicy.RUNTIME)
@Target({ElementType.FIELD, ElementType.METHOD})
public @interface BAttribute {

    /** Stable identifier of the model attribute. */
    String id();

    /** Name of the attribute in the model. */
    String name();

    /** B-UML type name ("str", "int", "date", an enumeration name, ...). */
    String type();

    int lower() default 1;

    /** Upper bound; {@link BTrace#MANY} for "*". */
    int upper() default 1;

    boolean isId() default false;

    boolean readOnly() default false;

    boolean derived() default false;
}
