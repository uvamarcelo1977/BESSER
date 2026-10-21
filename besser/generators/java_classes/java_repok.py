"""Utilities for generating Java class invariants."""

import json
import logging
import re

from besser.BUML.metamodel.structural import Class, DomainModel
from besser.BUML.notations.ocl.api import parse_ocl
from besser.BUML.notations.ocl.error_handling import BOCLSyntaxError
from besser.generators.java_classes.ocl_to_java import (
    OCLToJavaVisitor,
    OCLTranslationError,
)

_CONSTRAINT_KIND = re.compile(r"^\s*context\s+\w+\s+(inv|pre|post|init)\b", re.IGNORECASE)


def gen_java_repok(model: DomainModel) -> tuple[dict[str, list[dict]], set[str]]:
    """Translate class invariants and report classes used by ``allInstances``."""
    invariants: dict[str, list[dict]] = {}
    all_instances: set[str] = set()
    constraints = sorted(model.constraints, key=lambda item: (item.context.name, item.name))

    for constraint in constraints:
        expression = constraint.expression.strip()
        header = _CONSTRAINT_KIND.match(expression)
        if header and header.group(1).lower() != "inv":
            continue
        if not header:
            expression = f"context {constraint.context.name} inv: {expression}"

        result = {
            "name": constraint.name,
            "ocl": " ".join(constraint.expression.split()).replace("\\u", "\\\\u"),
            "java": None,
            "error": None,
            "imports": [],
        }
        visitor = OCLToJavaVisitor(constraint.context, model)
        try:
            parsed = parse_ocl(expression, model, constraint.context)
            result["java"] = visitor.visit(parsed.ast).code
            result["imports"] = sorted(visitor.imports)
            all_instances.update(visitor.all_instances)
        except (BOCLSyntaxError, OCLTranslationError, ValueError) as error:
            result["error"] = str(error)
            result["failure_message"] = json.dumps(
                f"OCL invariant {constraint.name} is not translatable: {error}"
            )
            logging.warning(
                "Could not translate OCL invariant %s.%s: %s",
                constraint.context.name,
                constraint.name,
                error,
            )
        invariants.setdefault(constraint.context.name, []).append(result)

    return invariants, all_instances


def java_repok_info(model: DomainModel) -> tuple[dict[str, dict], set[str]]:
    """Build template data for repOk methods and optional instance registries."""
    invariant_lists, all_instances = gen_java_repok(model)
    classes_with_invariants = set(invariant_lists)
    metadata: dict[str, dict] = {}
    for class_obj in model.classes_sorted_by_inheritance():
        own_invariants = invariant_lists.get(class_obj.name, [])
        if not own_invariants:
            continue
        metadata[class_obj.name] = {
            "invariants": own_invariants,
            "imports": sorted({
                imported
                for invariant in own_invariants
                for imported in invariant["imports"]
            }),
            "calls_super": any(
                parent.name in classes_with_invariants for parent in class_obj.all_parents()
            ),
        }

    model_class_names = {
        item.name for item in model.types if isinstance(item, Class)
    }
    unknown_registries = all_instances - model_class_names
    if unknown_registries:
        raise ValueError(
            "allInstances references unknown classes: "
            + ", ".join(sorted(unknown_registries))
        )
    return metadata, all_instances
