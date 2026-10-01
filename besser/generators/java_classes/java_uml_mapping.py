"""Mapping from the Java representation (concrete ADT) to the UML/B-UML
model (abstract ADT).

For every UML class, ``JavaUmlMapping`` decides which "abstraction getters"
have to be generated: one parameterless method per own attribute and per
navigable association end that becomes a field in that class. Each getter is
annotated with ``@toModel`` so that a runtime reconstructor can find it by
reflection. The decision logic lives here; the Jinja template only prints it.
"""

from besser.BUML.metamodel.structural import Class, Enumeration

ANNOTATION_NAME = "toModel"


class AbstractionGetter:
    """Everything the template needs to print one abstraction getter."""

    def __init__(self, target_class: str, field: str, return_type: str,
                 kind: str = "attribute", association: str = "", is_collection: bool = False):
        self.target_class = target_class
        self.field = field
        self.kind = kind
        self.association = association
        self.name = "get_" + field
        self.return_type = f"Set<{return_type}>" if is_collection else return_type
        self.return_expr = f"new HashSet<>(this.{field})" if is_collection else f"this.{field}"
        self.is_collection = is_collection


class JavaUmlMapping:
    """Computes the abstraction getters of the classes of a ``DomainModel``.

    Args:
        env (jinja2.Environment): the environment used by ``JavaGenerator``;
            it is used to reuse the ``get_field`` macro of ``java_fields.py.j2``
            so attribute types are exactly the ones the templates already emit.
    """

    def __init__(self, env):
        self._get_field = env.get_template("java_fields.py.j2").module.get_field

    @staticmethod
    def annotation_source(package_name: str = None) -> str:
        """Source code of the ``toModel`` annotation."""
        package = f"package {package_name};\n\n" if package_name else ""
        return package + f"""import java.lang.annotation.ElementType;
import java.lang.annotation.Retention;
import java.lang.annotation.RetentionPolicy;
import java.lang.annotation.Target;

@Retention(RetentionPolicy.RUNTIME)
@Target(ElementType.METHOD)
public @interface {ANNOTATION_NAME} {{
    String targetClass();
    String field();
    String kind();
    String association();
}}
"""

    def get_abstraction_getters(self, class_obj: Class, processed_associations: list) -> list:
        """Abstraction getters of ``class_obj``: own attributes first, then
        the association ends that ``java_template.py.j2`` turns into fields
        (same rules: two-ended associations only, not yet processed, navigable end).

        Must be called before rendering the class, since the template adds
        self-associations to ``processed_associations``.
        """
        getters = []
        for attr in class_obj.attributes:
            java_type = attr.type.name if isinstance(attr.type, Enumeration) \
                else self._get_field(attr.type.name).strip()
            getters.append(AbstractionGetter(class_obj.name, attr.name, java_type))

        for association in class_obj.associations:
            if len(association.ends) != 2 or association.name in processed_associations:
                continue
            ends = list(association.ends)
            if ends[0].type.name == ends[1].type.name:
                # Self-association: every navigable end is a field.
                field_ends = ends
            else:
                # The template keeps the last end typed otherwise than the class.
                field_ends = [end for end in ends if end.type.name != class_obj.name][-1:]
            for end in field_ends:
                if end.is_navigable:
                    getters.append(AbstractionGetter(class_obj.name, end.name, end.type.name,
                                                     "association", association.name,
                                                     end.multiplicity.max > 1))
        return getters
