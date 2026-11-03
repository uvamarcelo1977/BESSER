package besser.trace;

import java.lang.annotation.Documented;
import java.lang.annotation.ElementType;
import java.lang.annotation.Retention;
import java.lang.annotation.RetentionPolicy;
import java.lang.annotation.Target;

/** Marks the Java enum constant (or other member) that realizes a B-UML enumeration literal. */
@Documented
@Retention(RetentionPolicy.RUNTIME)
@Target({ElementType.FIELD, ElementType.METHOD})
public @interface BLiteral {

    /** Stable identifier of the model literal. */
    String id();

    /** Name of the literal in the model. */
    String name();
}
