
import os

from jinja2 import Environment, FileSystemLoader

from besser.BUML.metamodel.structural import (
    DomainModel,
    Enumeration,
)
from besser.generators import GeneratorInterface
from besser.generators.alloy_generator.translate_ocl_alloy import TranslatorState
from besser.generators.alloy_generator.utils_alloy import (
    collect_enumerations,
    generate_date_block,
)

class AlloyGenerator(GeneratorInterface):
    """
    AlloyGenerator: translates BESSER/BUML domain models to Alloy specifications.

    Current implementation translates class diagrams into Alloy models.

    The generator renders Jinja2 templates to produce a ``.als`` file containing:

    - Type signatures for basic or standard built-in datatypes (``str``, ``Int``, enumerations).
    - Signatures that represent classes, with fields that represent class attributes and
      navigable association ends.
    - Facts that enforce cardinality constraints for non-default multiplicities.
    - Facts enforcing transpose relational equivalence for bidirectional associations.
    - Facts capturing OCL constraints in the model.
    - A predicate without any additional constraints, to be used for model consistency checking.
    - A run command associated with the above predicate.
    """

    def __init__(self, model: DomainModel, output_dir: str | None = None, scope: int = 5):
        """
            Constructor for AlloyGenerator. Takes the domain model, output directory, and scope as parameters.
        """
        super().__init__(model, output_dir)
        self.scope = scope
        templates_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "templates")
        self.env = Environment(
            loader=FileSystemLoader(templates_path),
            trim_blocks=True,
            lstrip_blocks=True,
            extensions=["jinja2.ext.do"],
        )

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _render_spec(
        self,
        basic_signatures: set,
        sigs_nv: list[str],
        enums: dict,
        estado: TranslatorState,
        date_block: str,
        facts_rules: list[str],
    ) -> str:
        """
        Renders all Jinja2 templates and appends association facts.

        Returns:
            The complete ``.als`` specification as a single string.
        """
        parts: list[str] = []

        template = self.env.get_template("alloy_signatures_basic.j2")
        initial_signatures = template.render(
            basic_signatures=basic_signatures,
            enum_types={x for x in self.model.elements if isinstance(x, Enumeration)},
            has_date_values=bool(estado.dates) or ("date" in basic_signatures),
        )
        parts.append(initial_signatures)
        if date_block:
            parts.append(date_block)

        for class_obj in self.model.classes_sorted_by_inheritance():
            template = self.env.get_template("alloy_model.j2")
            relevant_associations = [
                assoc for assoc in self.model.associations
                if any(end.type.name == class_obj.name for end in assoc.ends)
            ]
            generated_code = template.render(class_obj=class_obj, associations=relevant_associations)
            parts.append(generated_code)

        template = self.env.get_template("alloy_final_als.j2")
        final = template.render(
            fun_types=[],
            constraints=self.model.constraints,
            sigsnv=sigs_nv,
            scope=self.scope,
        )
        parts.append(final)

        if facts_rules:
            parts.append("\n" + "\n".join(facts_rules))

        return "".join(parts)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def generate(self) -> None:
        """
        Generates an Alloy specification based on the provided B-UML model and saves it to
        the specified output directory.
        If the output directory was not specified, the code generated will be stored in the
        <current directory>/output folder.

        Returns:
            None, but store the generated specification in a file named model.als
        """
        file_path = self.build_generation_path(file_name="model.als")

        from besser.generators.alloy_generator.instance_generator.alloy_solver import (
            build_inheritance_and_attribute_maps,
            process_associations,
            translate_constraints,
        )

        inherits_from, data, basic_signatures, sigs_nv = (
            build_inheritance_and_attribute_maps(self.model)
        )
        facts_rules = process_associations(self.model, data)
        enums = collect_enumerations(self.model)
        estado = translate_constraints(self.model, inherits_from, data, enums)
        date_block = generate_date_block(estado, basic_signatures, self.scope)
        spec = self._render_spec(
            basic_signatures, sigs_nv, enums, estado, date_block, facts_rules
        )

        with open(file_path, mode="w", encoding="utf-8") as f:
            f.write(spec)
