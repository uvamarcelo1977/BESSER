package besser.trace;

import java.lang.annotation.Documented;
import java.lang.annotation.ElementType;
import java.lang.annotation.Retention;
import java.lang.annotation.RetentionPolicy;
import java.lang.annotation.Target;

/**
 * Marks the Java member that realizes a navigable end of a B-UML association.
 *
 * <p>The association itself has no Java element of its own; it is identified
 * by {@code associationId}, which is the same on both ends. As with
 * {@link BAttribute}, move the annotation to a no-argument method returning
 * the end's value if you change how the end is stored.
 */
@Documented
@Retention(RetentionPolicy.RUNTIME)
@Target({ElementType.FIELD, ElementType.METHOD})
public @interface BAssociationEnd {

    /** Stable identifier of this association end. */
    String id();

    /** Name of the end in the model. */
    String name();

    /** Java type implementing the model class at this end. */
    Class<?> type();

    int lower() default 1;

    /** Upper bound; {@link BTrace#MANY} for "*". */
    int upper() default 1;

    /** Name of the association in the model. */
    String association();

    /** Stable identifier of the association, shared by both ends. */
    String associationId();

    /** Name of the opposite end, or "" if there is none. */
    String opposite() default "";

    boolean composite() default false;

    boolean navigable() default true;
}
