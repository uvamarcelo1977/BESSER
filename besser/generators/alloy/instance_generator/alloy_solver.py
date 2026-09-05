"""
Alloy solver and satisfiability checking for UML-BESSER models.

This module contains:
- the orchestration of the Alloy Analyzer to generate bounded instances as
  witnesses of satisfiability/consistency,
- the BUML object-diagram / JSON generation and model integration that build
  on :mod:`besser.generators.alloy.instance_generator.alloy_converter`.

The translation of Alloy instances back into UML object diagrams lives in
:mod:`besser.generators.alloy.instance_generator.alloy_converter`.
"""

import logging
import os
import tempfile
from typing import Any

from besser.BUML.metamodel.structural import DomainModel
from besser.generators.alloy.alloy_generator import AlloyGenerator
from besser.utilities.buml_code_builder.domain_model_builder import domain_model_to_code
from besser.generators.alloy.instance_generator.alloy_converter import (
    AlloyToBesserConverter,
    BUMLModelIntegrator,
    alloy_xml_to_frontend_object_model,
)
from besser.generators.alloy.instance_generator.alloy_solver_utils import (
    execute_alloy_analyzer,
    parse_receipt,
    resolve_first_instance_xml,
)
from besser.generators.alloy.translate_ocl_alloy import (
    EnumReferenceError,
)

logger = logging.getLogger(__name__)

#----------------------------------------------------------------------
# Alloy invocation and satisfiability checking
#----------------------------------------------------------------------

class AlloySolver:

    def __init__(self, model: DomainModel, output_dir: str | None = None, scope: int = 5):
        if output_dir is None:
            self._temp_dir = tempfile.TemporaryDirectory(prefix="alloy_")
            output_dir = self._temp_dir.name
        else:
            self._temp_dir = None
        self.scope = scope
        self.model = model
        self.output_dir = output_dir
        generator = AlloyGenerator(model=self.model, output_dir=output_dir, scope=scope)
        generator.generate()
        self.file = os.path.join(output_dir, "model.als")

    def check_consistency(
        self,
        output_type: str = "json",
    ) -> bool | None:
        """Execute the Alloy Analyzer and check model satisfiability.

        Returns ``True`` if satisfiable (SAT), ``False`` if unsatisfiable (UNSAT),
        or ``None`` when the satisfiability could not be determined (error).

        As a side effect, this method populates the following state attributes,
        which consumers can read for additional data:
        - ``self.satisfiable``: ``bool`` or ``None`` (same as the return value)
        - ``self.command_name``: name of the first Alloy run/check command
        - ``self.solutions``: list of solutions (instances) found by the Analyzer
        - ``self.exec_output_dir``: directory where the Analyzer placed its output
        - ``self.last_error``: structured error dict when the check fails (``None``
          on success), with keys ``sat``, ``isValid``, ``message``, ``errors``,
          ``warnings``.
        """
        self.exec_output_dir = os.path.join(self.output_dir, "alloy_exec_output")
        self.satisfiable = None
        self.command_name = None
        self.solutions = []
        self.last_error = None
        try:
            result, error = execute_alloy_analyzer(
                self.file, self.exec_output_dir, output_type=output_type
            )
        except (EnumReferenceError, ValueError) as exc:
            self.last_error = {
                "sat": None,
                "isValid": False,
                "message": str(exc),
                "errors": [str(exc)],
                "warnings": [],
            }
            return None
        if error:
            self.last_error = error
            return None
        parsed, parse_error = parse_receipt(self.exec_output_dir, result)
        if parse_error:
            self.last_error = parse_error
            return None
        sat, command_name, solutions = parsed
        self.satisfiable = sat
        self.command_name = command_name
        self.solutions = solutions
        return sat

    def generate_instance_xml(self) -> str | None:
        """Run the satisfiability check and resolve the first instance XML.

        Returns the path to the XML file, or ``None`` if unsatisfiable.
        """
        satisfiable = self.check_consistency(output_type="xml")
        if satisfiable is not True:
            return None
        return resolve_first_instance_xml(self.exec_output_dir, self.solutions)

    def generate_object_diagram_code(
        self,
        xml_instance_path: str | None = None,
    ) -> str | None:
        """Generates BUML object-diagram code from a satisfying Alloy instance."""
        if xml_instance_path is None:
            xml_instance_path = self.generate_instance_xml()
            if not xml_instance_path:
                return None
        converter = AlloyToBesserConverter(xml_instance_path)
        converter.parse_xml()
        return converter.generate_object_diagram_code()

    def generate_object_diagram_json(
        self,
        reference_class_model: dict[str, Any],
        xml_instance_path: str | None = None,
    ) -> dict[str, Any] | None:
        """Generates the frontend ObjectDiagram JSON from a satisfying Alloy instance."""
        if xml_instance_path is None:
            xml_instance_path = self.generate_instance_xml()
            if not xml_instance_path:
                return None
        return alloy_xml_to_frontend_object_model(xml_instance_path, reference_class_model)

    def generate_integrated_buml_model(
        self,
        xml_instance_path: str | None = None,
    ) -> str | None:
        """Generates a BUML script combining the original class diagram with the
        object diagram derived from a satisfying Alloy instance."""
        if xml_instance_path is None:
            xml_instance_path = self.generate_instance_xml()
            if not xml_instance_path:
                return None
        tmp_buml = os.path.join(self.output_dir, "_tmp_buml_content.py")
        domain_model_to_code(model=self.model, file_path=tmp_buml)
        try:
            with open(tmp_buml, "r", encoding="utf-8") as f:
                original_buml_content = f.read()
        finally:
            if os.path.exists(tmp_buml):
                os.unlink(tmp_buml)
        integrator = BUMLModelIntegrator(original_buml_content, xml_instance_path)
        return integrator.generate_integrated_model()


def run_alloy_sat_validation(
    buml_model: DomainModel,
    all_warnings: list[str] | None = None,
    scope: int = 5,
    output_type: str = "json",
    output_dir: str | None = None,
) -> tuple[tuple[Any, ...] | None, dict[str, Any] | None, str]:
    """Translate a BUML class diagram + OCL constraints into Alloy, execute
    the Alloy Analyzer, and return the consistency-check result.

    This is a thin wrapper around :meth:`AlloySolver.check_consistency` (the
    single source of truth for the Alloy execution). It builds the solver, folds
    in the web-layer ``warnings``, and exposes the result in the legacy
    ``(parsed_data, error_response, exec_output_dir)`` shape where
    *parsed_data* is ``(sat, command_name, solutions)``.
    """
    warnings = all_warnings or []
    try:
        solver = AlloySolver(buml_model, scope=scope, output_dir=output_dir)
    except ValueError as exc:
        msg = str(exc)
        return None, {
            "sat": None,
            "isValid": False,
            "message": msg,
            "errors": [msg] if msg else [],
            "warnings": warnings,
        }, output_dir or "output"
    solver.check_consistency(output_type=output_type)
    if solver.satisfiable is None:
        return None, {**solver.last_error, "warnings": warnings}, solver.exec_output_dir
    return (
        (solver.satisfiable, solver.command_name, solver.solutions),
        None,
        solver.exec_output_dir,
    )
