import logging
import os
import tempfile
from pathlib import Path
from besser.BUML.metamodel.structural import DomainModel
from besser.generators.alloy.alloy_generator import AlloyGenerator
from besser.generators.alloy.instance_generator.alloy_analyzer_executor import AlloyAnalyzerExecutor, AlloyResult
from besser.generators.alloy.instance_generator.alloy_instance_to_BUML import AlloyToBUML

logger = logging.getLogger(__name__)

class AlloySolver:

    def __init__(self, model: DomainModel, output_dir: str | None = None, scope: int = 5):
        if output_dir is None:
            self._temp_dir = tempfile.TemporaryDirectory(prefix="alloy_")
            output_dir = self._temp_dir.name
        self.scope = scope
        self.model = model
        self.output_dir = output_dir
        self.alloy_output_dir = os.path.join(self.output_dir, "alloy_output")
        # TODO PABLO: I don't like that we need to create an AlloyGenerator object
        # each time we want to generate instances. Needs refactor!
        generator = AlloyGenerator(model=self.model, output_dir=output_dir, scope=scope)
        generator.generate()
        self.specification = os.path.join(output_dir, "model.als")
        self.executor = AlloyAnalyzerExecutor()

    def check_consistency(self) -> AlloyResult:
        """Execute the Alloy Analyzer and check model satisfiability.
        Returns an AlloyResult indicating whether the model is satisfiable 
        (SAT), unsatisfiable (UNSAT), or if the analysis timed out (TIMEOUT).
        """
        (result, instance_xml_files) = self.executor.execute_alloy_analyzer(self.specification, self.alloy_output_dir)
        return result

    def generate_object_diagrams(self, num_instances: int = 1):
        """Generates BUML object diagrams from satisfying Alloy instances.
        Returns an AlloyResult indicating the result of the analysis and a list of 
        BUML instances. The list is empty if no satisfying instances were found or if 
        the analysis timed out.
        BUML instances are also persisted in files ``output_dir/buml_object_instance0.py``, 
        ``output_dir/buml_object_instance1.py``, etc. 
        """
        # TODO PABLO: I don't like the repeated output of this method. I think we should
        # either return the list of instances or write them to files, but not both.
        (res, instance_xml_files) = self.executor.execute_alloy_analyzer(self.specification, 
                                            self.alloy_output_dir, num_instances=num_instances)
        buml_instances = []
        for xml_path in instance_xml_files:
            converter = AlloyToBUML(xml_path)
            buml_instances.append(converter.generate_object_diagram())

        os.makedirs(self.output_dir, exist_ok=True)
        #Clean up any previous instance files before writing new ones
        for file in Path(self.output_dir).glob("buml_object_instance*.py"):
            file.unlink()

        # Write the generated BUML instances to files    
        for i, instance in enumerate(buml_instances, start=0):
            instance_path = os.path.join(self.output_dir, f"buml_object_instance{i}.py")
            with open(instance_path, "w", encoding="utf-8") as f:
                f.write(instance)
        return (res, buml_instances)

# TODO PABLO: Needs revision. Implement this later!
#    def generate_integrated_buml_model(
#        self,
#        xml_instance_path: str | None = None,
#    ) -> str | None:
#        """Generates a BUML script combining the original class diagram with the
#        object diagram derived from a satisfying Alloy instance."""
#        if xml_instance_path is None:
#            xml_instance_path = self.generate_instance_xml()
#            if not xml_instance_path:
#                return None
#        tmp_buml = os.path.join(self.output_dir, "_tmp_buml_content.py")
#        domain_model_to_code(model=self.model, file_path=tmp_buml)
#        try:
#            with open(tmp_buml, "r", encoding="utf-8") as f:
#                original_buml_content = f.read()
#        finally:
#            if os.path.exists(tmp_buml):
#                os.unlink(tmp_buml)
#        integrator = BUMLModelIntegrator(original_buml_content, xml_instance_path)
#        integrated_code = integrator.generate_integrated_model()
#        if integrated_code is None:
#            return None
#        integrated_path = os.path.join(self.output_dir, "buml_integrated_model.py")
#        with open(integrated_path, "w", encoding="utf-8") as f:
#            f.write(integrated_code)
#        return integrated_code
