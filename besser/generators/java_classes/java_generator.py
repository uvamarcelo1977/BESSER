import os
from jinja2 import Environment, FileSystemLoader
from besser.BUML.metamodel.structural import DomainModel, Enumeration
from besser.generators import GeneratorInterface
from .java_trace import JavaTraceAnnotations

try:
    from besser.utilities import sort_by_timestamp as _declaration_order
except ImportError:  # BESSER versions without element timestamps
    def _declaration_order(elements):
        return sorted(elements, key=lambda element: element.name)


class JavaGenerator(GeneratorInterface):

    def __init__(self, model: DomainModel, output_dir: str = None):
        super().__init__(model, output_dir)

    def generate(self):
        # The environment and template do not depend on the class: build them once.
        templates_path = os.path.join(os.path.dirname(
            os.path.abspath(__file__)), "templates")
        env = Environment(loader=FileSystemLoader(
            templates_path), trim_blocks=True, lstrip_blocks=True, extensions=['jinja2.ext.do'])

        # Traceability: annotation renderer for the templates, plus the
        # annotation declarations (package besser.trace) in the output.
        trace = JavaTraceAnnotations(self.model)
        env.globals["trace"] = trace
        trace.copy_annotation_sources(self)

        template = env.get_template('java_template.py.j2')
        package_name = ""
        if self.output_dir is not None:
            if 'tmp' in self.output_dir or 'AppData' in self.output_dir:
                package_name = None
            else:
                package_name = self.output_dir
        else:
            package_name = None

        # Enumerations: without them, enum-typed attributes do not compile.
        enum_template = env.get_template('java_enum_template.py.j2')
        enumerations = sorted((t for t in self.model.types if isinstance(t, Enumeration)),
                              key=lambda e: e.name)
        for enum_obj in enumerations:
            file_path = self.build_generation_path(file_name=enum_obj.name+".java")
            with open(file_path, mode="w") as f:
                f.write(enum_template.render(enum_obj=enum_obj,
                                             literals=_declaration_order(enum_obj.literals),
                                             package_name=package_name))
                print("Code generated in the location: " + file_path)

        processed_associations = []
        for class_obj in self.model.classes_sorted_by_inheritance():
            file_path = self.build_generation_path(file_name=class_obj.name+".java")
            with open(file_path, mode="w") as f:
                generated_code = template.render(class_obj=class_obj,
                                                 processed_associations=processed_associations,
                                                 package_name=package_name)
                f.write(generated_code)
                print("Code generated in the location: " + file_path)
