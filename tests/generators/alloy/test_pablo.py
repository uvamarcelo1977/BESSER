from besser.BUML.metamodel.structural import DomainModel, Class, Property, \
    Multiplicity, BinaryAssociation, StringType, IntegerType, DateType
from besser.generators.python_classes.python_classes_generator import PythonGenerator
from besser.generators.sql_alchemy.sql_alchemy_generator import SQLAlchemyGenerator
from besser.generators.sql.sql_generator import SQLGenerator
from besser.generators.rest_api.rest_api_generator import RESTAPIGenerator
from besser.generators.rdf.rdf_generator import RDFGenerator
from besser.generators.backend.backend_generator import BackendGenerator
from besser.generators.alloy.alloy_generator import AlloyGenerator

# Library attributes definition
library_name: Property = Property(name="name", type=StringType)
address: Property = Property(name="address", type=StringType)
# Library class definition
library: Class = Class(name="Library", attributes={library_name, address})

# Book attributes definition
title: Property = Property(name="title", type=StringType)
pages: Property = Property(name="pages", type=IntegerType)
release: Property = Property(name="release", type=DateType)
# Book class definition
book: Class = Class(name="Book", attributes={title, pages, release})

# Author attributes definition
author_name: Property = Property(name="name", type=StringType)
email: Property = Property(name="email", type=StringType)
# Author class definition
author: Class = Class(name="Author", attributes={author_name, email})

# Library-Book association definition
located_in: Property = Property(name="locatedIn", type=library, multiplicity=Multiplicity(1, 1))
has: Property = Property(name="has", type=book, multiplicity=Multiplicity(0, "*"))
lib_book_association: BinaryAssociation = BinaryAssociation(name="lib_book_assoc", ends={located_in, has})

# Book-Author association definition
publishes: Property = Property(name="publishes", type=book, multiplicity=Multiplicity(0, "*"))
written_by: Property = Property(name="writtenBy", type=author, multiplicity=Multiplicity(1, "*"))
book_author_association: BinaryAssociation = BinaryAssociation(name="book_author_assoc", ends={written_by, publishes})

# Domain model definition
library_model: DomainModel = DomainModel(name="Library_model", types={library, book, author},
                                         associations={lib_book_association, book_author_association})

outputdir = "output"
# Code Generation
generator = AlloyGenerator(model=library_model, output_dir=outputdir)
generator.generate()

from besser.generators.alloy.instance_generator import AlloySolver
# Semantic consistency check
solver = AlloySolver(library_model)
result = solver.check_consistency()
assert result == True, "The model is not consistent."

buml_object_instance = solver.generate_object_diagram_code()
assert buml_object_instance is not None, "The object diagram code generation failed."

from besser.generators.alloy.instance_generator import alloy_xml_to_frontend_object_model
from besser.utilities.web_modeling_editor.backend.services.converters.buml_to_json import class_buml_to_json

xml_path = solver.generate_instance_xml()
reference_model = class_buml_to_json(library_model)
json_object_instance = alloy_xml_to_frontend_object_model(xml_path, reference_model)
assert json_object_instance is not None, "The object diagram JSON generation failed."

buml_diagram_code = solver.generate_integrated_buml_model()
assert buml_diagram_code is not None, "The integrated BUML model code generation failed."


