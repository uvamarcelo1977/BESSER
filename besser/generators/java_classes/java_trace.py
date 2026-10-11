"""Traceability annotations for the BESSER Java generator.

Renders the @BClass, @BAttribute, @BAssociationEnd, @BEnumeration and
@BLiteral annotations that link generated Java code back to B-UML model
elements, and copies the annotation type declarations (package
``besser.trace``) into the generation output.
"""
import os
import shutil
import uuid

from besser.BUML.metamodel.structural import (
    Class, DomainModel, Enumeration, EnumerationLiteral, Property,
    UNLIMITED_MAX_MULTIPLICITY,
)

TRACE_PACKAGE = "besser.trace"

_ANNOTATION_SOURCES = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "templates", "java_trace")

# Fixed namespace: the same model element always yields the same id.
_BESSER_TRACE_NS = uuid.UUID("f6f9040e-d104-4385-9f1d-a9d6ed54466a")

_MAX_LINE = 100


class JavaTraceAnnotations:
    """Exposed to the Jinja templates as the global ``trace``."""

    def __init__(self, model: DomainModel):
        self.model = model

    # ------------------------------------------------------------------ ids
    def element_id(self, kind: str, qualified_name: str) -> str:
        """Stable id for a model element.

        B-UML elements have no persistent identifier, so the id is derived
        from the element's qualified name: it is stable across regenerations
        but changes when the element is renamed. Replace this method once the
        metamodel carries persistent ids.
        """
        key = f"{self.model.name}/{kind}/{qualified_name}"
        return str(uuid.uuid5(_BESSER_TRACE_NS, key))

    # ---------------------------------------------------------- annotations
    def class_annotation(self, class_obj: Class) -> str:
        args = [
            ("id", _string(self.element_id("class", class_obj.name))),
            ("name", _string(class_obj.name)),
            ("model", _string(self.model.name)),
        ]
        if class_obj.is_abstract:
            args.append(("isAbstract", "true"))
        parents = sorted(parent.name for parent in class_obj.parents())
        if parents:
            literals = ", ".join(f"{name}.class" for name in parents)
            args.append(("parents", "{" + literals + "}"))
        return _render("BClass", args, indent=0)

    def attribute_annotation(self, attr: Property) -> str:
        owner = attr.owner.name
        args = [
            ("id", _string(self.element_id("attribute", f"{owner}::{attr.name}"))),
            ("name", _string(attr.name)),
            ("type", _string(attr.type.name)),
        ]
        args += _multiplicity(attr)
        if attr.is_id:
            args.append(("isId", "true"))
        if attr.is_read_only:
            args.append(("readOnly", "true"))
        if attr.is_derived:
            args.append(("derived", "true"))
        return _render("BAttribute", args)

    def association_end_annotation(self, end: Property) -> str:
        association = end.owner
        others = [e for e in association.ends if e is not end]
        args = [
            ("id", _string(self.element_id(
                "association_end", f"{association.name}::{end.name}"))),
            ("name", _string(end.name)),
            ("type", f"{end.type.name}.class"),
        ]
        args += _multiplicity(end)
        args += [
            ("association", _string(association.name)),
            ("associationId", _string(
                self.element_id("association", association.name))),
        ]
        if len(others) == 1:
            args.append(("opposite", _string(others[0].name)))
        if end.is_composite:
            args.append(("composite", "true"))
        if not end.is_navigable:
            args.append(("navigable", "false"))
        return _render("BAssociationEnd", args)

    def enumeration_annotation(self, enum_obj: Enumeration) -> str:
        args = [
            ("id", _string(self.element_id("enumeration", enum_obj.name))),
            ("name", _string(enum_obj.name)),
            ("model", _string(self.model.name)),
        ]
        return _render("BEnumeration", args, indent=0)

    def literal_annotation(self, enum_obj: Enumeration,
                           literal: EnumerationLiteral) -> str:
        args = [
            ("id", _string(self.element_id(
                "literal", f"{enum_obj.name}::{literal.name}"))),
            ("name", _string(literal.name)),
        ]
        return _render("BLiteral", args)

    # --------------------------------------------------------------- output
    def import_statement(self) -> str:
        return f"import {TRACE_PACKAGE}.*;"

    def copy_annotation_sources(self, generator) -> None:
        """Write the annotation declarations to <output>/besser/trace/."""
        for file_name in sorted(os.listdir(_ANNOTATION_SOURCES)):
            if not file_name.endswith(".java"):
                continue
            target = generator.build_generation_path(
                file_name=os.path.join(*TRACE_PACKAGE.split("."), file_name))
            os.makedirs(os.path.dirname(target), exist_ok=True)
            shutil.copyfile(os.path.join(_ANNOTATION_SOURCES, file_name), target)


# ---------------------------------------------------------------- helpers
def _string(value: str) -> str:
    escaped = str(value).replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def _bound(value: int) -> str:
    return "BTrace.MANY" if value >= UNLIMITED_MAX_MULTIPLICITY else str(value)


def _multiplicity(prop: Property) -> list:
    """lower/upper, omitted when equal to the annotation defaults (1..1)."""
    args = []
    if prop.multiplicity.min != 1:
        args.append(("lower", str(prop.multiplicity.min)))
    if prop.multiplicity.max != 1:
        args.append(("upper", _bound(prop.multiplicity.max)))
    return args


def _render(annotation: str, args: list, indent: int = 4) -> str:
    """One line if it fits, otherwise one element per line."""
    pairs = [f"{key} = {value}" for key, value in args]
    single = f"@{annotation}({', '.join(pairs)})"
    if indent + len(single) <= _MAX_LINE:
        return single
    pad = " " * (indent + 4)
    return f"@{annotation}(\n" + ",\n".join(pad + p for p in pairs) + ")"
