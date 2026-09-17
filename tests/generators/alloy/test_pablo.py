import os
from besser.BUML.metamodel.structural import DomainModel, Class, Property, \
    Multiplicity, BinaryAssociation, StringType, IntegerType, DateType
from besser.generators.alloy.instance_generator.alloy_analyzer_executor import AlloyResult
from besser.generators.alloy.instance_generator import AlloySolver


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


#os.environ['JAVA_HOME'] = '/opt/homebrew/Cellar/openjdk@21/21.0.11/libexec/openjdk.jdk/Contents/Home'
#os.environ['BESSER_ALLOY_JAR'] = '/Users/pponzio/code/besser/releases/BESSER/besser/BUML/notations/ocl/consistency/alloy.jar'

os.environ['JAVA_HOME'] = '/usr/lib/jvm/java-21-openjdk-amd64'
os.environ['BESSER_ALLOY_JAR'] = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..', 'besser', 'BUML', 'notations', 'ocl', 'consistency', 'alloy.jar')



# Semantic consistency check
solver = AlloySolver(library_model, output_dir="otdir")
result = solver.check_consistency()
assert result == AlloyResult.SAT, "The model is not consistent."

# Generate two BUML object diagram using Alloy
solver = AlloySolver(library_model, output_dir="otdir")
(res, instance_xml_files) = solver.generate_object_diagrams(num_instances=2)
assert result == AlloyResult.SAT, "The model is not consistent."
assert len(instance_xml_files) == 2, "The number of generated instances is not correct."



solver = AlloySolver(library_model, output_dir="otdir_2")
# Agregué en generate_object_diagrams un parámetro  raw_metamodel_syntax=True para generar 
# el modelo BUML de objetos ajustando a la notación más clara.
# Cuando raw_metamodel_syntax=False (por defecto) lo genera en un formato que lo acepta 
# object_buml_to_json , si lo generamos directamente en el formato último que compartiste Pablo
#  object_buml_to_json no lo soporta. Habría que tocar ese método pero no lo hice porque 
# no sé si conviene tocar lo que ellos ya tienen listo.

#De todas formas la notación más clara no la levanta bien el editor besser correctamente(el de ellos).

(res, instance_xml_files) = solver.generate_object_diagrams(num_instances=2,raw_metamodel_syntax=True)
assert result == AlloyResult.SAT, "The model is not consistent."
assert len(instance_xml_files) == 2, "The number of generated instances is not correct."



# Genera el código completo del modelo BUML integrado a partir de la instancia generada.
# Diagrama BUML completo (clases + objetos).
#solver = AlloySolver(library_model, output_dir="clsobjdir")
#buml_diagram_code = solver.generate_integrated_buml_model()
#assert buml_diagram_code is not None, "The integrated BUML model code generation failed."


# Limpieza: elimina los archivos y directorios creados por la ejecución del test.
# comentar las lineas siguientes para mantener los archivos generados.
#for artifact_dir in (outputdir,):
#    if os.path.isdir(artifact_dir):
#        for file_name in os.listdir(artifact_dir):
#            file_path = os.path.join(artifact_dir, file_name)
#            if os.path.isfile(file_path):
#                os.unlink(file_path)
#        os.rmdir(artifact_dir)




