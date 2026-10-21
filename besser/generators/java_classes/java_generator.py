import os

from jinja2 import Environment, FileSystemLoader
from besser.BUML.metamodel.structural import DomainModel
from besser.generators import GeneratorInterface
from besser.utilities import sort_by_timestamp
from besser.generators.java_classes.java_trace import JavaTraceAnnotations
from besser.generators.java_classes.java_repok import java_repok_info

class JavaGenerator(GeneratorInterface):

    def __init__(self, model: DomainModel, output_dir: str = None, package_name: str = None):
        super().__init__(model, output_dir)
        self.package_name = package_name

    def generate(self):
        templates_path = os.path.join(os.path.dirname(
            os.path.abspath(__file__)), "templates")
        env = Environment(loader=FileSystemLoader(
            templates_path), trim_blocks=True, lstrip_blocks=True, extensions=['jinja2.ext.do'])

        # Traceability: annotation renderer for the templates, plus the
        # annotation declarations (package besser.trace) in the output.
        trace = JavaTraceAnnotations(self.model)
        env.globals["trace"] = trace
        trace.copy_annotation_sources(self)

        package_name = self.package_name

        for enum_obj in self.model.get_enumerations():
            file_path = self.build_generation_path(file_name=enum_obj.name + ".java")
            template = env.get_template('java_enum_template.py.j2')
            with open(file_path, mode="w") as f:
                f.write(template.render(enum_obj=enum_obj, literals=sort_by_timestamp(enum_obj.literals),
                                        package_name=package_name))
                print("Code generated in the location: " + file_path)

        processed_associations = []
        repok_by_class, registry_classes = java_repok_info(self.model)
        for class_obj in self.model.classes_sorted_by_inheritance():
            file_path = self.build_generation_path(file_name=class_obj.name + ".java")
            template = env.get_template('java_template.py.j2')
            with open(file_path, mode="w") as f:
                generated_code = template.render(class_obj=class_obj,
                                                 processed_associations=processed_associations,
                                                 package_name=package_name,
                                                 repok=repok_by_class.get(class_obj.name),
                                                 registry=class_obj.name in registry_classes)
                f.write(generated_code)
                print("Code generated in the location: " + file_path)
