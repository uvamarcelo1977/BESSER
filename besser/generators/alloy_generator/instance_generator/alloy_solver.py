"""
SAT based semantic consistency checker for UML-BESSER class diagrams.

This module contains functions that:
- implement the translation from UML-BESSER class diagrams and OCL constraints into Alloy,
- use Alloy to generate bounded instances as witnesses of satisfiability/consistency
- translate Alloy instances into UML object diagrams.
"""

import asyncio
import copy
import json
import logging
import os
import re
import subprocess
import tempfile
import xml.etree.ElementTree as ET
from collections import defaultdict
from collections.abc import AsyncGenerator
from contextlib import nullcontext
from pathlib import Path
from typing import Any

from besser.BUML.metamodel.structural import DomainModel, Enumeration
from besser.generators.alloy_generator.alloy_generator import AlloyGenerator
from besser.generators.alloy_generator.translate_ocl_alloy import (
    EnumReferenceError,
    TranslatorState,
    ocl_to_alloy,
)
from besser.generators.alloy_generator.utils_alloy import (
    build_consistency_rule,
    sanitize_alloy_name,
)
from besser.utilities.web_modeling_editor.backend.models.diagram import DiagramInput
from besser.utilities.web_modeling_editor.backend.services.converters import (
    process_class_diagram,
)
from besser.utilities.web_modeling_editor.backend.services.converters.buml_to_json.object_diagram_converter import (
    object_buml_to_json,
)
from besser.utilities.web_modeling_editor.backend.services.validators.ocl_checker import (
    check_ocl_constraint,
)

logger = logging.getLogger(__name__)

SCOPE_STEPS = [5, 8, 9, 10]  # Scopes to be used when checking semantic consistency
TIMEOUT_SECONDS = 50
TIMEOUT_CALL_ALLOY = 40


#----------------------------------------------------------------------
# BUML -> Alloy translation helpers
#----------------------------------------------------------------------

def build_inheritance_and_attribute_maps(
    model: DomainModel,
) -> tuple[dict, dict, set, list[str]]:
    """Builds inheritance, attribute, and signature maps from *model*.

    Returns:
        A tuple ``(inherits_from, data, basic_signatures, sigs_nv)``.
    """
    inherits_from: dict = defaultdict(list)
    data: dict = defaultdict(list)
    basic_signatures: set = set()
    sigs_nv: list[str] = []

    for class_obj in model.classes_sorted_by_inheritance():
        sigs_nv.append(class_obj.name)

        if len(class_obj.parents()) == 0:
            inherits_from[class_obj.name].append("_")
        else:
            for parent in class_obj.parents():
                inherits_from[class_obj.name].append(parent.name)

        for attr in class_obj.attributes:
            attr_type = "date" if attr.type.name in ("date", "datetime", "time", "timedelta") else attr.type.name
            data[class_obj.name].append(f"{attr.name}:{attr_type}")
            if not isinstance(attr.type, Enumeration):
                basic_signatures.add(attr_type)
                sigs_nv.append(attr_type)

    return inherits_from, data, basic_signatures, sigs_nv


def process_associations(model: DomainModel, data: dict) -> list[str]:
    """Processes associations, building consistency facts and updating *data*.

    Returns:
        A list of Alloy fact strings for associations.
    """
    facts_rules: list[str] = []

    for assoc in model.associations:
        d, h = assoc.ends
        mult_b = [h.multiplicity.min, h.multiplicity.max]
        mult_a = [d.multiplicity.min, d.multiplicity.max]
        arrow_a_b = bool(h.is_navigable)
        arrow_b_a = bool(d.is_navigable)

        facts_rules.append(
            build_consistency_rule(
                d.type.name, h.name, mult_b,
                h.type.name, d.name, mult_a,
                arrow_a_b, arrow_b_a,
            )
        )
        data[h.type.name].append(f"{d.name}:{d.type.name}")
        data[d.type.name].append(f"{h.name}:{h.type.name}")

        if arrow_a_b and arrow_b_a:
            facts_rules.append(
                f"fact{{{d.type.name}_{h.name}= ~{h.type.name}_{d.name}}}"
            )

    return facts_rules


def translate_constraints(
    model: DomainModel, inherits_from: dict, data: dict, enums: dict
) -> TranslatorState:
    """Translates OCL constraints to Alloy facts in-place.

    Returns:
        A :class:`TranslatorState` object, carrying accumulated state (e.g. date
        literals discovered during translation).
    """
    state = TranslatorState()
    for constraint in model.constraints:
        context = constraint.context.name
        ocl_str = constraint.expression.split(":", 1)[1]
        constraint.expression = ocl_to_alloy(
            inherits_from, data, ocl_str, context, state, enums
        )
    return state


def resolve_first_instance_xml(
    exec_output_dir: str | Path, solutions: list[dict] | None = None
) -> str | None:
    """
    Determines the absolute path to the XML file holding the first instance/solution
    produced by the Alloy Analyzer.

    Tries to resolve the file referenced by *solutions* (as read from ``receipt.json``)
    first, falling back to scanning *exec_output_dir* for any ``.xml`` file.
    """
    output_dir = Path(exec_output_dir)

    if solutions:
        for solution in solutions:
            for instance in solution.get("instances", []) or []:
                if isinstance(instance, dict):
                    name = instance.get("xml") or instance.get("filename") or instance.get("path")
                else:
                    name = instance
                if not name:
                    continue
                candidate = output_dir / name
                if candidate.is_file():
                    return str(candidate.resolve())

    if output_dir.is_dir():
        for entry in sorted(output_dir.iterdir()):
            if entry.is_file() and entry.suffix == ".xml":
                return str(entry.resolve())

    return None


#----------------------------------------------------------------------
# Alloy XML -> BUML object diagram conversion
#----------------------------------------------------------------------

class AlloyToBesserConverter:
    """Converts Alloy XML instances to BESSER objects."""

    def __init__(self, xml_file: str):
        """
        Initializes the converter with the given Alloy XML file.

        Args:
            xml_file: Path to Alloy XML file
        """
        self.xml_file = xml_file
        self.tree = ET.parse(xml_file)
        self.root = self.tree.getroot()

        # Data structures to store parsed information
        self.signatures = {}  # sig_id -> {label, atoms}
        self.fields = {}  # field_id -> {label, parent_id, tuples}
        self.atoms_by_sig = {}  # sig_label -> [atoms]
        self.builtin_sigs = {'seq/Int', 'Int', 'String', 'univ', 'boolean/Bool',
                            'boolean/True', 'boolean/False'}

    def parse_xml(self):
        """Parses the Alloy XML file and extracts signatures, fields, and atoms."""

        # Parse signatures
        for sig in self.root.findall('.//sig'):
            sig_id = sig.get('ID')
            sig_label = sig.get('label')
            parent_id = sig.get('parentID')

            # Ignore built-in signatures
            if sig_label in self.builtin_sigs:
                continue

            atoms = [atom.get('label') for atom in sig.findall('atom')]

            self.signatures[sig_id] = {
                'label': sig_label,
                'atoms': atoms,
                'builtin': sig.get('builtin') == 'yes',
                'parent_id': parent_id,
            }

            # Organize atoms by signature label
            if not self.signatures[sig_id]['builtin']:
                self.atoms_by_sig[sig_label] = atoms

        # Parse fields
        for field in self.root.findall('.//field'):
            field_id = field.get('ID')
            field_label = field.get('label')
            parent_id = field.get('parentID')

            tuples = []
            for tuple_elem in field.findall('tuple'):
                atoms = [atom.get('label') for atom in tuple_elem.findall('atom')]
                if len(atoms) >= 2:
                    tuples.append((atoms[0], atoms[1]))

            self.fields[field_id] = {
                'label': field_label,
                'parent_id': parent_id,
                'tuples': tuples
            }

    def get_class_name(self, sig_label: str) -> str:
        """
        Extracts the class name from a signature label.
        Args:
            sig_label: label of the signature (e.g., 'this/Player')

        Returns:
            Class name (e.g., 'Player')
        """
        if '/' in sig_label:
            return sig_label.split('/')[-1]
        return sig_label

    def remove_class_prefix(self, field_name: str, class_name: str) -> str:
        """
        Removes the class prefix from a field name.
        Args:
            field_name: field name (e.g., 'Player_name')
            class_name: class name (e.g., 'Player')

        Returns:
            Field name without prefix (e.g., 'name')
        """
        prefix = f"{class_name}_"
        if field_name.startswith(prefix):
            return field_name[len(prefix):]
        elif field_name.__contains__("_"):
            return field_name[field_name.index("_")+1:]
        return field_name

    def is_enum_value(self, atom_label: str) -> bool:
        """Determines if an atom is an enumeration value."""
        return atom_label.startswith('ENUM_')

    def get_enum_value(self, atom_label: str) -> str:
        """
        Extracts the enumeration value from an atom label.
        Args:
            atom_label: atom label (e.g., 'ENUM_Position_CENTER$0')

        Returns:
            Enumeration value (e.g., 'CENTER')
        """
        # Format: ENUM_EnumName_VALUE$n
        parts = atom_label.split('_')
        if len(parts) >= 3:
            value = '_'.join(parts[2:])  # take everything after ENUM_EnumName_
            # Remove suffix $n
            if '$' in value:
                value = value.split('$')[0]
            return value
        return atom_label

    def is_primitive_type(self, atom_label: str) -> bool:
        """Determines if an atom represents a primitive type."""
        try:
            int(atom_label)
            return True
        except ValueError:
            pass
        return '$' in atom_label

    def get_primitive_value(self, atom_label: str, atom_type: str | None = None) -> Any:
        """
        Extracts the primitive value of an atom.
        Args:
            atom_label: atom label
            atom_type: expected type (Int, String, etc.)

        Returns:
            Converted primitive value
        """
        # Integers
        try:
            return int(atom_label)
        except ValueError:
            pass

        # Strings - return identifier without suffix
        if '$' in atom_label:
            base_name = atom_label.split('$')[0]
            return f'"{base_name}"'  # Return as quoted string

        return f'"{atom_label}"'

    DATE_SIG_PATTERN = re.compile(r"^d\d{8}$")

    def _date_sig_label(self) -> str | None:
        """Returns the label of the 'date' signature (e.g., 'this/date') if it exists."""
        for sig_label in self.atoms_by_sig:
            if self.get_class_name(sig_label) == "date":
                return sig_label
        return None

    def is_date_value(self, atom_label: str) -> bool:
        """
        Determines if an atom represents a date value.

        Recognizes both literals of the form ``dMMDDYYYY`` (as emitted by OCL constraints)
        and free atoms of the ``date`` signature generated by Alloy (e.g., ``date$0``, ``date$01``,
        or other strings).
        """
        base = atom_label.split("$")[0]
        if self.DATE_SIG_PATTERN.match(base):
            return True
        date_sig_label = self._date_sig_label()
        return bool(date_sig_label and atom_label in self.atoms_by_sig[date_sig_label])

    def get_date_value(self, atom_label: str) -> str:
        """
        Extracts the date value from an atom.

        Literals of the form ``dMMDDYYYY`` are decoded to 'DD-MM-YYYY'; other atoms of the ``date``
        signature are returned as found by Alloy, enclosed in quotes (e.g., '"date$0"').
        Args:
            atom_label: atom label (e.g., 'd01012000$0' or 'date$01')

        Returns:
            Date value as a string with quotes (e.g., '"01-01-2000"')
        """
        base = atom_label.split("$")[0]
        if self.DATE_SIG_PATTERN.match(base):
            return f'"{base[3:5]}-{base[1:3]}-{base[5:9]}"'
        return f'"{atom_label}"'

    def is_domain_class_name(self, class_name: str) -> bool:
        """Determines if *class_name* is a user domain class."""
        if not class_name:
            return False
        if self.is_enum_value(class_name) or class_name.startswith("ENUM_"):
            return False
        if class_name in ("str", "Bool", "True", "False", "date", "Ord"):
            return False
        return not self.DATE_SIG_PATTERN.match(class_name)

    def is_object_reference(self, atom_label: str) -> bool:
        """
        Determines if an atom is a reference to another domain object.
        Args:
            atom_label: atom label to check

        Returns:
            True if it is a reference to an object, False if it is primitive
        """
        # Domain objects are represented with format ClassName$N
        if '$' in atom_label:
            base = atom_label.split('$')[0]

            # Exclude special types and types that are not domain objects
            if base in ['str', 'pepe', 'Position'] or base.startswith('ENUM_'):
                return False

            # Check if it exists in atoms_by_sig with the prefix this/
            for sig_label in self.atoms_by_sig:
                class_name = self.get_class_name(sig_label)
                if (class_name == base
                        and atom_label in self.atoms_by_sig[sig_label]
                        and class_name not in ['str', 'Bool', 'True', 'False']):
                    return True
        return False

    def get_fields_for_signature(self, sig_label: str) -> dict[str, list[tuple]]:
        sig_id = None
        for sid, sig_data in self.signatures.items():
            if sig_data['label'] == sig_label:
                sig_id = sid
                break

        if not sig_id:
            return {}

        fields_dict = {}
        for field_data in self.fields.values():
            if field_data['parent_id'] == sig_id:
                field_name = field_data['label']
                fields_dict[field_name] = field_data['tuples']

        return fields_dict

    def _pair_association_fields(self) -> dict[str, frozenset]:
        """
        Pairs the two ends of the same bidirectional association.

        The Alloy encoding represents a bidirectional association as two fields with exactly transposed
        sets of tuples. This mapping allows one to deduplicate only those two halves without collapsing
        distinct associations between the same pair of objects.
        """
        field_tuples: dict[str, set[tuple]] = {}
        for field_data in self.fields.values():
            label = field_data['label']
            field_tuples[label] = set(field_data['tuples'])

        used: set[str] = set()
        paired: dict[str, frozenset] = {}
        for field_label, tuples in field_tuples.items():
            if field_label in used or not tuples:
                continue

            transposed = {(to_atom, from_atom) for from_atom, to_atom in tuples}
            partner = None
            for other_label, other_tuples in field_tuples.items():
                if other_label in used or other_label == field_label or not other_tuples:
                    continue
                if other_tuples == transposed:
                    partner = other_label
                    break

            if partner:
                assoc = frozenset([field_label, partner])
                paired[field_label] = assoc
                paired[partner] = assoc
                used.update([field_label, partner])
            else:
                paired[field_label] = frozenset([field_label])

        return paired

    def generate_object_diagram_code(self) -> str:
        """
        Generates BUML code for the object diagram derived from the XML.

        Only the most specific concrete class of each atom is instantiated,
        inherited attributes are incorporated, and multiple associations
        between the same classes or objects are preserved.
        """
        code_lines = []

        # Identify the domain classes. The enumeration signatures should not
        # be materialized as objects.
        domain_classes = set()
        for sig_label, atoms in self.atoms_by_sig.items():
            if not sig_label.startswith("this/"):
                continue
            class_name = self.get_class_name(sig_label)
            if not self.is_domain_class_name(class_name):
                continue
            if atoms and all(self.is_enum_value(atom) for atom in atoms):
                continue
            domain_classes.add(class_name)

        def signature_depth(sig_id: str | None) -> int:
            depth = 0
            current_id = sig_id
            while current_id and current_id in self.signatures:
                parent_id = self.signatures[current_id].get('parent_id')
                if not parent_id or parent_id not in self.signatures:
                    break
                depth += 1
                current_id = parent_id
            return depth

        domain_signatures = []
        for sig_id, sig_data in self.signatures.items():
            class_name = self.get_class_name(sig_data['label'])
            if class_name not in domain_classes:
                continue
            domain_signatures.append({
                'class_name': class_name,
                'atoms': set(sig_data['atoms']),
                'depth': signature_depth(sig_id),
            })

        def leaf_class_for(atom_label: str) -> str | None:
            """Returns the most specific concrete class that contains the atom."""
            containing = [sig for sig in domain_signatures if atom_label in sig['atoms']]
            if not containing:
                return None
            leaf_sig = max(
                containing,
                key=lambda sig: (sig['depth'], -len(sig['atoms']), sig['class_name'])
            )
            return leaf_sig['class_name']

        created_objects = {}  # atom_label -> variable_name
        relations = []  # [(from_var, relation_name, to_atom, field_name), ...]

        for sig_label, atoms in self.atoms_by_sig.items():
            class_name = self.get_class_name(sig_label)

            if class_name not in domain_classes:
                continue

            for i, atom_label in enumerate(atoms):
                if leaf_class_for(atom_label) != class_name:
                    continue

                obj_var = f"{class_name.lower()}_{i}_obj"
                obj_name = atom_label.replace('$', '_')

                created_objects[atom_label] = obj_var
                attributes = {}

                # Traverse all fields to also include attributes and associations
                # inherited from ancestor classes.
                for field_data in self.fields.values():
                    field_name = field_data['label']
                    tuples = field_data['tuples']
                    attr_name = self.remove_class_prefix(field_name, class_name)

                    for tuple_from, tuple_to in tuples:
                        if tuple_from != atom_label:
                            continue

                        if self.is_date_value(tuple_to):
                            attributes[attr_name] = self.get_date_value(tuple_to)
                        elif self.is_object_reference(tuple_to):
                            relations.append((obj_var, attr_name, tuple_to, field_name))
                        elif self.is_enum_value(tuple_to):
                            enum_value = self.get_enum_value(tuple_to)
                            attributes[attr_name] = f'"{enum_value}"'
                        else:
                            attributes[attr_name] = self.get_primitive_value(tuple_to)

                attribute_mapping_parts = []
                for attr_name, attr_value in attributes.items():
                    attribute_mapping_parts.append(f"{attr_name!r}: {attr_value}")

                if attribute_mapping_parts:
                    code_lines.append(
                        f'{obj_var} = {class_name}("{obj_name}").attributes(**{{{", ".join(attribute_mapping_parts)}}}).build()'
                    )
                else:
                    code_lines.append(
                        f'{obj_var} = {class_name}("{obj_name}").build()'
                    )

        code_lines.append("")

        if relations:
            code_lines.append("# Set relations between objects")

        paired_fields = self._pair_association_fields()
        seen_links = set()
        deduplicated_relations = []
        for from_var, relation_name, to_atom, field_name in relations:
            if to_atom not in created_objects:
                continue
            to_var = created_objects[to_atom]
            assoc_id = paired_fields.get(field_name, frozenset([field_name]))
            canonical = (frozenset([from_var, to_var]), assoc_id)
            if canonical in seen_links:
                continue
            seen_links.add(canonical)
            deduplicated_relations.append((from_var, relation_name, to_atom))

        relations = deduplicated_relations

        # Group relations by (from_var, relation_name) to handle multiplicity 'many'
        grouped_relations = {}
        for from_var, relation_name, to_atom in relations:
            if to_atom in created_objects:
                key = (from_var, relation_name)
                if key not in grouped_relations:
                    grouped_relations[key] = []
                grouped_relations[key].append(created_objects[to_atom])

        for (from_var, relation_name), to_vars in grouped_relations.items():
            unique_targets = sorted(set(to_vars))
            if len(unique_targets) == 1:
                code_lines.append(
                    f"setattr({from_var}, {relation_name!r}, {unique_targets[0]})"
                )
            else:
                targets_expr = ", ".join(unique_targets)
                code_lines.append(
                    f"setattr({from_var}, {relation_name!r}, {{{targets_expr}}})"
                )

        if relations:
            code_lines.append("")

        code_lines.append("# Object Model instance")
        all_objects = ", ".join(created_objects.values())
        code_lines.append("object_model: ObjectModel = ObjectModel(")
        code_lines.append('    name="Object_Diagram",')
        code_lines.append(f"    objects={{{all_objects}}}")
        code_lines.append(")")
        return "\n".join(code_lines)

    def to_json(self, reference_class_model: dict[str, Any]) -> dict[str, Any]:
        """
        Converts the parsed Alloy instance into the frontend ObjectDiagram JSON format.

        Args:
            reference_class_model: Reference class diagram JSON, used to map attribute types.

        Returns:
            Dictionary representing the object diagram in JSON format.
        """
        code = self.generate_object_diagram_code()
        return object_buml_to_json(code, reference_class_model)


class BUMLModelIntegrator:
    """Integrates an original BUML model with an object diagram generated from Alloy."""

    def __init__(self, original_buml_content: str, xml_instance_file: str):
        """
        Initializes the integrator.

        Args:
            original_buml_content: Source code of the original BUML file (class diagram)
            xml_instance_file: Path to the Alloy instance XML file
        """
        self.xml_instance_file = xml_instance_file
        self.original_content = original_buml_content

    def extract_structural_model_section(self) -> str:
        """
        Extracts the structural model section (class diagram) from the original BUML content.

        Returns:
            The code of the structural model section.
        """
        patterns = [
            r'################\s*\n#\s*OBJECT MODEL\s*#',
            r'##############\s*\n\s*from besser\.BUML\.metamodel\.object',
            r'######################\s*\n#\s*PROJECT DEFINITION\s*#'
        ]

        end_pos = len(self.original_content)
        for pattern in patterns:
            match = re.search(pattern, self.original_content, re.IGNORECASE)
            if match:
                end_pos = min(end_pos, match.start())

        structural_section = self.original_content[:end_pos].rstrip()
        return structural_section

    def extract_project_section(self) -> str:
        """
        Extracts the project definition section from the original BUML content if it exists.

        Returns:
            The code of the project section or an empty string if not found.
        """
        pattern = r'######################\s*\n#\s*PROJECT DEFINITION\s*#\s*\n######################\s*\n(.*)'
        match = re.search(pattern, self.original_content, re.DOTALL)

        if match:
            project_section = match.group(0).strip()

            models_pattern = r'(models=\[)([^\]]+)(\])'

            def replace_models(match):
                prefix = match.group(1)
                models_list = match.group(2).strip()
                suffix = match.group(3)

                if 'object_model' in models_list:
                    return match.group(0)

                if models_list:
                    return f"{prefix}{models_list}, object_model{suffix}"
                return f"{prefix}object_model{suffix}"

            project_section = re.sub(models_pattern, replace_models, project_section)

            return project_section
        return ""

    def generate_integrated_model(self, output_file: str | None = None) -> str:
        """
        Generates the complete integrated BUML model.

        Args:
            output_file: File to save the model (optional)

        Returns:
            The code of the integrated model.
        """
        structural_section = self.extract_structural_model_section()

        converter = AlloyToBesserConverter(self.xml_instance_file)
        converter.parse_xml()
        object_diagram_code = converter.generate_object_diagram_code()

        project_section = self.extract_project_section()

        integrated_lines = []

        integrated_lines.append(structural_section)
        integrated_lines.append("")
        integrated_lines.append("")

        integrated_lines.append("################")
        integrated_lines.append("# OBJECT MODEL #")
        integrated_lines.append("################")
        integrated_lines.append("")
        integrated_lines.append("from besser.BUML.metamodel.object import ObjectModel")
        integrated_lines.append("import datetime")
        integrated_lines.append("")
        integrated_lines.append(object_diagram_code)
        integrated_lines.append("")
        integrated_lines.append("")

        if project_section:
            integrated_lines.append(project_section)

        integrated_model = "\n".join(integrated_lines)

        if output_file:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(integrated_model)

        return integrated_model


#----------------------------------------------------------------------
# Alloy invocation and satisfiability checking
#----------------------------------------------------------------------

class AlloySolver:

    def __init__(self, model: DomainModel, output_dir: str | None = None, scope: int = 5):
        if output_dir is None:
            output_dir = "output"
        self.scope = scope
        self.model = copy.deepcopy(model)
        self.output_dir = output_dir
        self._sanitize_model_names()
        generator = AlloyGenerator(model=self.model, output_dir=output_dir, scope=scope)
        generator.generate()
        self.file = os.path.join(output_dir, "model.als")

    def _sanitize_model_names(self) -> None:
        """Sanitizes class and attribute names in-place for Alloy compatibility."""
        for class_obj in self.model.classes_sorted_by_inheritance():
            class_obj.name = sanitize_alloy_name(class_obj.name)
            for attr in class_obj.attributes:
                attr.name = sanitize_alloy_name(attr.name)

    @staticmethod
    def _resolve_alloy_jar_path() -> str | None:
        env_path = os.getenv("BESSER_ALLOY_JAR")
        if env_path:
            candidate = Path(env_path).expanduser().resolve()
            if candidate.exists() and candidate.is_file():
                return str(candidate)
            logger.warning("BESSER_ALLOY_JAR points to a missing file: %s", env_path)

        besser_dir = Path(__file__).resolve().parent.parent.parent.parent  # besser/
        candidate = besser_dir / "BUML" / "notations" / "ocl" / "consistency" / "alloy.jar"
        if candidate.exists() and candidate.is_file():
            return str(candidate)

        logger.warning("Alloy jar not found. Set BESSER_ALLOY_JAR or place alloy.jar in a known location.")
        return None

    @staticmethod
    def _execute_alloy_analyzer(
        als_path: str, exec_output_dir: str, output_type: str = "json", num_instances: int = 5
    ) -> tuple[subprocess.CompletedProcess | None, dict[str, Any] | None]:
        jar_path = AlloySolver._resolve_alloy_jar_path()
        if not jar_path:
            return None, {
                "sat": None,
                "isValid": False,
                "message": "Could not determine satisfiability (Alloy jar not found).",
                "errors": ["Alloy JAR not found. Set BESSER_ALLOY_JAR or place alloy.jar in a known location."],
                "warnings": [],
            }
        try:
            result = subprocess.run(
                [
                    "java", "-jar", jar_path, "exec", "-n", "-f",
                    "-o", exec_output_dir, "-t", output_type, "-r", str(num_instances), als_path,
                ],
                capture_output=True,
                text=True,
                timeout=TIMEOUT_CALL_ALLOY,
            )
        except subprocess.TimeoutExpired:
            return None, {
                "sat": None,
                "isValid": False,
                "message": (
                    f"Alloy execution timed out after {TIMEOUT_CALL_ALLOY} seconds "
                    "— model may be unsatisfiable or too complex."
                ),
                "errors": [f"Alloy execution timed out after {TIMEOUT_CALL_ALLOY} seconds."],
                "warnings": [],
            }
        return result, None

    @staticmethod
    def _parse_receipt(
        exec_output_dir: str,
        result: subprocess.CompletedProcess,
        structural_warnings: list[str] | None = None,
    ) -> tuple[tuple[Any, ...] | None, dict[str, Any] | None]:
        warnings = structural_warnings or []
        receipt_path = os.path.join(exec_output_dir, "receipt.json")

        if not os.path.exists(receipt_path):
            output = result.stdout + result.stderr
            logger.warning("Alloy exec produced no receipt.json. Output: %s", output[:500])
            return None, {
                "sat": None,
                "isValid": False,
                "message": "Could not determine satisfiability (no receipt.json produced).",
                "errors": [output[:500]],
                "warnings": warnings,
            }

        with open(receipt_path, "r", encoding="utf-8") as f:
            receipt = json.load(f)

        commands = receipt.get("commands", {})
        if not commands:
            return None, {
                "sat": None,
                "isValid": False,
                "message": "No commands were executed in the Alloy model.",
                "errors": ["The generated .als file contains no run/check commands."],
                "warnings": warnings,
            }

        first_command_name = next(iter(commands))
        first_command = commands[first_command_name]
        solutions = first_command.get("solution", [])
        sat = any(sol.get("instances") for sol in solutions)
        return (sat, first_command_name, solutions), None

    def check_consistency(
        self,
        structural_warnings: list[str] | None = None,
        output_type: str = "json",
        temp_dir: str | None = None,
    ) -> tuple[bool, tuple[Any, ...] | None, dict[str, Any] | None, str]:
        cm = tempfile.TemporaryDirectory() if temp_dir is None else nullcontext(temp_dir)
        with cm as td:
            exec_output_dir = os.path.join(td, "alloy_exec_output")
            try:
                result, error = self._execute_alloy_analyzer(
                    self.file, exec_output_dir, output_type=output_type
                )
            except EnumReferenceError as exc:
                return False, None, {
                    "sat": None,
                    "isValid": False,
                    "message": str(exc),
                    "errors": [str(exc)],
                    "warnings": structural_warnings or [],
                }, exec_output_dir
            except ValueError as exc:
                return False, None, {
                    "sat": None,
                    "isValid": False,
                    "message": str(exc),
                    "errors": [str(exc)],
                    "warnings": structural_warnings or [],
                }, exec_output_dir
            if error:
                return False, None, error, exec_output_dir
            parsed, parse_error = self._parse_receipt(
                exec_output_dir, result, structural_warnings
            )
            if parse_error:
                return False, None, parse_error, exec_output_dir
            sat = parsed[0] if parsed else False
            return sat, parsed, None, exec_output_dir

    def run_sat_validation(
        self,
        structural_warnings: list[str] | None = None,
        output_type: str = "json",
        temp_dir: str | None = None,
    ) -> tuple[tuple[Any, ...] | None, dict[str, Any] | None, str]:
        """Run Alloy satisfiability validation returning a simplified result.

        Wraps :meth:`check_consistency` to collapse the 4-tuple into a 3-tuple
        ``(parsed, error, exec_output_dir)`` for callers that only need the
        parsed result or the error dict.

        Returns:
            On success: ``(parsed, None, exec_output_dir)``.
            On failure: ``(None, error_dict, exec_output_dir)``.
        """
        is_sat, parsed, error, exec_output_dir = self.check_consistency(
            structural_warnings, output_type, temp_dir
        )
        if error:
            return None, error, exec_output_dir
        return parsed, None, exec_output_dir

    def generate_instance_xml(
        self,
        structural_warnings: list[str] | None = None,
        output_type: str = "xml",
        output_dir: str | None = None,
    ) -> str | None:
        """
        Runs the satisfiability check and resolves the path to the first
        generated instance XML file.

        If *output_dir* is ``None``, the Alloy execution artifacts are written
        to a temporary directory that is cleaned up before this method
        returns, so the result will be ``None`` in that case.
        """
        is_sat, parsed, error, exec_output_dir = self.check_consistency(
            structural_warnings, output_type, output_dir
        )
        if error or not is_sat or not parsed:
            return None
        _, _, solutions = parsed
        return resolve_first_instance_xml(exec_output_dir, solutions)

    def generate_object_diagram_code(
        self,
        xml_instance_path: str | None = None,
        output_dir: str | None = None,
    ) -> str | None:
        """Generates BUML object-diagram code from a satisfying Alloy instance."""
        if xml_instance_path is None:
            xml_instance_path = self.generate_instance_xml(output_dir=output_dir)
            if not xml_instance_path:
                return None
        converter = AlloyToBesserConverter(xml_instance_path)
        converter.parse_xml()
        return converter.generate_object_diagram_code()

    def generate_object_diagram_json(
        self,
        reference_class_model: dict[str, Any],
        xml_instance_path: str | None = None,
        output_dir: str | None = None,
    ) -> dict[str, Any] | None:
        """Generates the frontend ObjectDiagram JSON from a satisfying Alloy instance."""
        if xml_instance_path is None:
            xml_instance_path = self.generate_instance_xml(output_dir=output_dir)
            if not xml_instance_path:
                return None
        converter = AlloyToBesserConverter(xml_instance_path)
        converter.parse_xml()
        return converter.to_json(reference_class_model)

    def generate_integrated_buml_model(
        self,
        original_buml_content: str,
        xml_instance_path: str | None = None,
        output_dir: str | None = None,
    ) -> str | None:
        """Generates a BUML script combining the original class diagram with the
        object diagram derived from a satisfying Alloy instance."""
        if xml_instance_path is None:
            xml_instance_path = self.generate_instance_xml(output_dir=output_dir)
            if not xml_instance_path:
                return None
        integrator = BUMLModelIntegrator(original_buml_content, xml_instance_path)
        return integrator.generate_integrated_model()


#----------------------------------------------------------------------

def _alloy_xml_to_frontend_object_model(
    xml_instance_path: str, reference_class_model: dict[str, Any]
) -> dict[str, Any]:
    """
    Converts an Alloy instance into an object diagram.
    
    The Alloy instance is received in XML format. The result is provided
    in the JSON format for ObjectDiagram, expected by the frontend.
    """ 
    converter = AlloyToBesserConverter(xml_instance_path)
    converter.parse_xml()
    return converter.to_json(reference_class_model)

#----------------------------------------------------------------------
def convert_json_to_buml(input_data: DiagramInput) -> DomainModel | dict[str, Any]:
    """
    Converts a diagram in JSON format to a corresponding BUML model.

    If the provided diagram is not a class diagram, no conversion is performed, 
    and a dictionary containing an unsupported operation message is produced.
    """
    diagram_type = input_data.model.get("type") if input_data.model else None
    if diagram_type != "ClassDiagram":
        return {
            "sat": None,
            "isValid": False,
            "message": "Semantic  Check is only available for Class Diagrams.",
            "errors": [],
            "warnings": [],
        }
    json_data = {"title": input_data.title, "model": input_data.model}
    return process_class_diagram(json_data)

#----------------------------------------------------------------------
def validate_buml_structure(buml_model: DomainModel) -> tuple[list[str], list[str]]:
    """
    Checks the structural (syntactic) consistency of a BUML model. 

    Delegates the checking into buml_model.validate() functionality.

    When validation does not raise exceptions, the obtained errors and warnings is returned.
    If exceptions are thrown, a message indicating structural validation error is produced. 
    """
    try:
        result = buml_model.validate(raise_exception=False)
        return result.get("errors", []), result.get("warnings", [])
    except Exception as e:
        return [f"Structural validation error: {e!s}"], []

#----------------------------------------------------------------------

def validate_ocl_constraints(
    buml_model: DomainModel,
    structural_warnings: list[str] | None = None,
) -> tuple[list[str], dict[str, Any] | None]:
    """
    Validates the syntax of OCL constraints, resorting to check_ocl_constraint() 
    functionality.

    Since semantic consistency check requires the OCL syntax checking to fully pass,
    all errors and warnings of the syntactic check are treated as errors.

    Result is a dictionary with errors and warnings if validation failed, 
    None if validation passed.
    Parameter structural_warnings is streamed into the output too. 
    """
    ocl_result = check_ocl_constraint(buml_model, object_model=None)
    ocl_errors = list(ocl_result.get("invalid_constraints", []))


    # Promote OCL warnings (malformed syntax or missing classes/fields) to blocking
    # errors, as valid OCL invariants are essential for SAT execution.
    conversion_warnings = list(getattr(buml_model, "ocl_warnings", []) or [])
    ocl_tokens = ("ocl", "constraint", "precondition", "postcondition", "invariant")
    blocking_ocl_conversion_issues = [
        warning.replace("Warning", "Error")
        for warning in conversion_warnings
        if any(token in warning.lower() for token in ocl_tokens)
    ]
    ocl_errors.extend(blocking_ocl_conversion_issues)

    if not ocl_result.get("success", True) or ocl_errors:
        ocl_errors.append(ocl_result.get("message", "OCL validation failed."))
    all_warnings = structural_warnings or []
    if ocl_errors:
        return all_warnings, {
            "sat": None,
            "isValid": False,
            "message": " OCL constraints are invalid — SAT check skipped.",
            "errors": ocl_errors,
            "warnings": all_warnings,
        }
    return all_warnings, None

#----------------------------------------------------------------------
def run_alloy_sat_validation(
    buml_model: DomainModel,
    all_warnings: list[str] | None = None,
    scope: int = 5,
    output_type: str = "json",
    temp_dir: str | None = None,
) -> tuple[tuple[Any, ...] | None, dict[str, Any] | None, str]:
    """
    Translates UMLB class diagram and OCL constraints into Alloy specification,
    executes Alloy Analyzer to check for consistency, 
    and parses the Alloy consistency check result. 

    Delegates consistency checkint to AlloySolver.run_sat_validation().

    Result is (parsed_data, error_response, exec_output_dir), where
    - parsed_data indicates sat/unsat outcome,
    - error_response contains errors when validation fails,
    - exec_output_dir is the directory where the obtained SAT instances are placed
    by the Alloy Analyzer.
    """
    warnings = all_warnings or []
    cm = tempfile.TemporaryDirectory() if temp_dir is None else nullcontext(temp_dir)
    with cm as td:
        try:
            solver = AlloySolver(buml_model, scope=scope, output_dir=td)
            parsed, error, exec_output_dir = solver.run_sat_validation(
                structural_warnings=warnings, output_type=output_type, temp_dir=td,
            )
            if error:
                return None, {**error, "warnings": warnings}, exec_output_dir
            return parsed, None, exec_output_dir
        except ValueError as exc:
            # OCL-to-Alloy translation errors (e.g. self.allInstances()) surface
            # during AlloySolver construction / generation. Surface them as a
            # regular error response so the SSE streams can report them instead
            # of letting the exception escape the async generator.
            msg = str(exc)
            return None, {
                "sat": None,
                "isValid": False,
                "message": msg,
                "errors": [msg] if msg else [],
                "warnings": warnings,
            }, str(td)

async def check_alloy_consistency_stream(input_data: DiagramInput) -> AsyncGenerator[str, None]:
    """
    Performs semantic satisfiability check of a BUML class diagram.

    The semantic satisfiability check involves:
    - syntactic check of the structure of the class diagram
    - syntactic check of the OCL constraints, if present
    - translation of class diagram and OCL constraints into an Alloy specification
    - Checks for consistency of the Alloy specification for increasingly larger
    scopes, stopping when SAT is found, timeout is reached, or all scopes are 
    exhausted.

    Result is yielded as SSE-formatted strings. 
    """
    buml_model = convert_json_to_buml(input_data)
    if isinstance(buml_model, dict):
        yield _sse({**buml_model, "done": True})
        return

    structural_errors, structural_warnings = validate_buml_structure(buml_model)
    if structural_errors:
        yield _sse({
            "sat": None,
            "isValid": False,
            "message": " Structural validation failed — SAT check skipped.",
            "errors": structural_errors,
            "warnings": structural_warnings,
            "done": True,
        })
        return

    all_warnings, ocl_error = validate_ocl_constraints(buml_model, structural_warnings)
    if ocl_error:
        yield _sse({**ocl_error, "done": True})
        return

    # Steps 4-6: iterate scopes
    for scope in SCOPE_STEPS:
        yield _sse({
            "sat": None,
            "done": False,
            "message": f"🔍 Trying scope {scope}...",
            "scope": scope,
        })

        try:
            parsed, error, _ = await asyncio.wait_for(
                asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda s=scope: run_alloy_sat_validation(buml_model, all_warnings, scope=s)
                ),
                timeout=TIMEOUT_SECONDS,
            )
        except asyncio.TimeoutError:
            yield _sse({
                "sat": False,
                "isValid": False,
                "done": True,
                "message": f"⏱️ Timeout after {TIMEOUT_SECONDS}s with scope {scope} — model may be unsatisfiable.",
                "errors": [],
                "warnings": all_warnings,
            })
            return

        if error:
            yield _sse({**error, "done": True})
            return

        sat, first_command_name, _ = parsed
        if sat:
            yield _sse({
                "sat": True,
                "isValid": True,
                "done": True,
                "message": f" SAT found with scope {scope} (command: {first_command_name}).",
                "errors": [],
                "warnings": all_warnings,
                "scope": scope,
            })
            return

        yield _sse({
            "sat": False,
            "done": False,
            "message": f" UNSAT with scope {scope}. Trying larger scope...",
            "scope": scope,
        })

    # All scopes exhausted without finding SAT
    yield _sse({
        "sat": False,
        "isValid": False,
        "done": True,
        "message": f" UNSAT with all scopes tried ({SCOPE_STEPS}). Model is likely unsatisfiable.",
        "errors": [],
        "warnings": all_warnings,
    })


async def generate_alloy_do_stream(input_data: DiagramInput) -> AsyncGenerator[str, None]:
    """
    Generates object diagram that complies with constraints of a BUML class diagram,
    incluing OCL constraints, if present.

    The generation of the semantically consistent object diagram involves:
    - syntactic check of the structure of the class diagram
    - syntactic check of the OCL constraints, if present
    - translation of class diagram and OCL constraints into an Alloy specification
    - Checks for consistency of the Alloy specification for increasingly larger
    scopes, stopping when SAT is found, timeout is reached, or all scopes are
    exhausted.
    - Translation of one (the first) Alloy instance back into a front-end object 
    diagram.

    Yields SSE-formatted progress events per scope. Stops at the first SAT
    instance (converting it to a frontend Object Diagram), on timeout, or when
    all scopes are exhausted.
    """
    # Steps 1-3: pre-validation (same flow as check_alloy_consistency_stream)
    buml_model = convert_json_to_buml(input_data)
    if isinstance(buml_model, dict):
        yield _sse({**buml_model, "done": True})
        return

    structural_errors, structural_warnings = validate_buml_structure(buml_model)
    if structural_errors:
        yield _sse({
            "sat": None,
            "isValid": False,
            "message": " Structural validation failed — SAT check skipped.",
            "errors": structural_errors,
            "warnings": structural_warnings,
            "done": True,
        })
        return

    all_warnings, ocl_error = validate_ocl_constraints(buml_model, structural_warnings)
    if ocl_error:
        yield _sse({**ocl_error, "done": True})
        return

    # Steps 4-6: iterate scopes until SAT is found
    with tempfile.TemporaryDirectory() as temp_dir:
        for scope in SCOPE_STEPS:
            yield _sse({
                "sat": None,
                "done": False,
                "message": f"🔍 Trying scope {scope}...",
                "scope": scope,
            })

            try:
                parsed, error, exec_output_dir = await asyncio.wait_for(
                    asyncio.get_event_loop().run_in_executor(
                        None,
                        lambda s=scope: run_alloy_sat_validation(
                            buml_model, all_warnings, scope=s, output_type="xml",
                            temp_dir=os.path.join(temp_dir, f"scope_{s}"),
                        )
                    ),
                    timeout=TIMEOUT_SECONDS,
                )
            except asyncio.TimeoutError:
                yield _sse({
                    "sat": False,
                    "isValid": False,
                    "done": True,
                    "message": f"⏱️ Timeout after {TIMEOUT_SECONDS}s with scope {scope} — model may be unsatisfiable.",
                    "errors": [],
                    "warnings": all_warnings,
                })
                return

            if error:
                yield _sse({**error, "done": True})
                return

            sat, first_command_name, solutions = parsed
            if not sat:
                yield _sse({
                    "sat": False,
                    "done": False,
                    "message": f" UNSAT with scope {scope}. Trying larger scope...",
                    "scope": scope,
                })
                continue

            # SAT → locate XML instance → convert to frontend Object Diagram JSON
            yield _sse({
                "sat": True,
                "done": False,
                "message": (
                    f"✅ SAT found with scope {scope} "
                    f"(command: {first_command_name}). Generating Object Diagram..."
                ),
                "scope": scope,
            })

            loop = asyncio.get_event_loop()
            try:
                xml_instance_path = await loop.run_in_executor(
                    None, resolve_first_instance_xml, exec_output_dir, solutions
                )
                if not xml_instance_path:
                    logger.warning("SAT=true but no Alloy XML instance was found in %s", exec_output_dir)
                    yield _sse({
                        "sat": True,
                        "isValid": False,
                        "done": True,
                        "message": (
                            f" Model is satisfiable (command: {first_command_name}), "
                            "but no instance XML was found."
                        ),
                        "errors": [],
                        "warnings": all_warnings,
                        "scope": scope,
                    })
                    return

                object_model = await loop.run_in_executor(
                    None, _alloy_xml_to_frontend_object_model, xml_instance_path, input_data.model
                )
            except Exception as exc:
                logger.exception("Failed to convert Alloy instance to frontend ObjectDiagram")
                yield _sse({
                    "sat": True,
                    "isValid": False,
                    "done": True,
                    "message": (
                        f" Model is satisfiable (command: {first_command_name}), "
                        "but instance conversion failed."
                    ),
                    "error": str(exc),
                    "warnings": all_warnings,
                    "scope": scope,
                })
                return

            yield _sse({
                "sat": True,
                "isValid": True,
                "done": True,
                "message": f" Model is satisfiable (command: {first_command_name}).",
                "errors": [],
                "warnings": all_warnings,
                "scope": scope,
                "object_model": object_model,
            })
            return

        # All scopes exhausted without finding SAT
        yield _sse({
            "sat": False,
            "isValid": False,
            "done": True,
            "message": f" UNSAT with all scopes tried ({SCOPE_STEPS}). Model is likely unsatisfiable.",
            "errors": [],
            "warnings": all_warnings,
        })


def _sse(data: dict[str, Any]) -> str:
    """
    Formats a dict as an SSE data line.
    """
    return f"data: {json.dumps(data)}\n\n"
