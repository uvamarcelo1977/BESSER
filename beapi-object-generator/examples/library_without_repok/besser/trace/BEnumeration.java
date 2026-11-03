package besser.trace;

import java.lang.annotation.Documented;
import java.lang.annotation.ElementType;
import java.lang.annotation.Retention;
import java.lang.annotation.RetentionPolicy;
import java.lang.annotation.Target;

/** Marks a Java type as the implementation of a B-UML enumeration. */
@Documented
@Retention(RetentionPolicy.RUNTIME)
@Target(ElementType.TYPE)
public @interface BEnumeration {

    /** Stable identifier of the model enumeration. */
    String id();

    /** Name of the enumeration in the model. */
    String name();

    /** Name of the B-UML domain model the enumeration belongs to. */
    String model();
}
