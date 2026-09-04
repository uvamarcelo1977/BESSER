
import json
import logging
import os
import re
import subprocess
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

TIMEOUT_CALL_ALLOY = 40


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


def resolve_alloy_jar_path() -> str | None:
    """Locates the ``alloy.jar`` file used to run the Alloy Analyzer.

    Resolution order:
    1. ``BESSER_ALLOY_JAR`` environment variable.
    2. Bundled jar at ``besser/BUML/notations/ocl/consistency/alloy.jar``.
    """
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


def execute_alloy_analyzer(
    als_path: str, exec_output_dir: str, output_type: str = "json", num_instances: int = 1
) -> tuple[subprocess.CompletedProcess | None, dict[str, Any] | None]:
    """Run the Alloy Analyzer as a subprocess.

    Returns ``(result, error_dict)``.  On success *error_dict* is ``None``;
    on failure (jar missing or timeout) *result* is ``None`` and *error_dict*
    contains a standard error response.
    """
    jar_path = resolve_alloy_jar_path()
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


def parse_receipt(
    exec_output_dir: str,
    result: subprocess.CompletedProcess,
    structural_warnings: list[str] | None = None,
) -> tuple[tuple[Any, ...] | None, dict[str, Any] | None]:
    """Parse the ``receipt.json`` produced by the Alloy Analyzer.

    Returns ``(parsed_tuple, error_dict)``.  On success *error_dict* is
    ``None`` and *parsed_tuple* is ``(sat, command_name, solutions)``.
    """
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


# ---------------------------------------------------------------------------
# Pure helpers for converting Alloy atoms/signatures into BUML object values
# ---------------------------------------------------------------------------

DATE_SIG_PATTERN = re.compile(r"^d\d{8}$")


def get_class_name(sig_label: str) -> str:
    """
    Extracts the class name from a signature label.
    Args:
        sig_label: label of the signature (e.g., 'this/Player')

    Returns:
        Class name (e.g., 'Player')
    """
    if "/" in sig_label:
        return sig_label.split("/")[-1]
    return sig_label


def remove_class_prefix(field_name: str, class_name: str) -> str:
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
        return field_name[field_name.index("_") + 1:]
    return field_name


def is_enum_value(atom_label: str) -> bool:
    """Determines if an atom is an enumeration value."""
    return atom_label.startswith("ENUM_")


def get_enum_value(atom_label: str) -> str:
    """
    Extracts the enumeration value from an atom label.
    Args:
        atom_label: atom label (e.g., 'ENUM_Position_CENTER$0')

    Returns:
        Enumeration value (e.g., 'CENTER')
    """
    # Format: ENUM_EnumName_VALUE$n
    parts = atom_label.split("_")
    if len(parts) >= 3:
        value = "_".join(parts[2:])  # take everything after ENUM_EnumName_
        # Remove suffix $n
        if "$" in value:
            value = value.split("$")[0]
        return value
    return atom_label


def get_primitive_value(atom_label: str, atom_type: str | None = None) -> Any:
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
    if "$" in atom_label:
        base_name = atom_label.split("$")[0]
        return f'"{base_name}"'  # Return as quoted string

    return f'"{atom_label}"'


def get_date_value(atom_label: str) -> str:
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
    if DATE_SIG_PATTERN.match(base):
        return f'"{base[3:5]}-{base[1:3]}-{base[5:9]}"'
    return f'"{atom_label}"'


def is_domain_class_name(class_name: str) -> bool:
    """Determines if *class_name* is a user domain class."""
    if not class_name:
        return False
    if is_enum_value(class_name) or class_name.startswith("ENUM_"):
        return False
    if class_name in ("str", "Bool", "True", "False", "date", "Ord"):
        return False
    return not DATE_SIG_PATTERN.match(class_name)
