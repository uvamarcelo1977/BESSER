####################
# STRUCTURAL MODEL #
####################

from besser.BUML.metamodel.structural import (
    Class, Property, Method, Parameter,
    BinaryAssociation, Generalization, DomainModel,
    Enumeration, EnumerationLiteral, Multiplicity,
    StringType, IntegerType, FloatType, BooleanType,
    TimeType, DateType, DateTimeType, TimeDeltaType,
    AnyType, Constraint, AssociationClass, Metadata, MethodImplementationType
)

# Classes
Library = Class(name="Library")
Book = Class(name="Book")
Author = Class(name="Author")

# Library class attributes and methods
Library_name: Property = Property(name="name", type=StringType)
Library_address: Property = Property(name="address", type=StringType)
Library.attributes={Library_address, Library_name}

# Book class attributes and methods
Book_title: Property = Property(name="title", type=StringType)
Book_pages: Property = Property(name="pages", type=IntegerType)
Book_release: Property = Property(name="release", type=DateType)
Book.attributes={Book_pages, Book_release, Book_title}

# Author class attributes and methods
Author_name: Property = Property(name="name", type=StringType)
Author_email: Property = Property(name="email", type=StringType)
Author.attributes={Author_email, Author_name}

# Relationships
lib_book_assoc: BinaryAssociation = BinaryAssociation(
    name="lib_book_assoc",
    ends={
        Property(name="locatedIn", type=Library, multiplicity=Multiplicity(1, 1)),
        Property(name="has", type=Book, multiplicity=Multiplicity(0, 9999))
    }
)
book_author_assoc: BinaryAssociation = BinaryAssociation(
    name="book_author_assoc",
    ends={
        Property(name="publishes", type=Book, multiplicity=Multiplicity(0, 9999)),
        Property(name="writtenBy", type=Author, multiplicity=Multiplicity(1, 9999))
    }
)

# Domain Model
domain_model = DomainModel(
    name="Library_model",
    types={Library, Book, Author},
    associations={lib_book_assoc, book_author_assoc},
    generalizations={},
    metadata=None
)


################
# OBJECT MODEL #
################

from besser.BUML.metamodel.object import ObjectModel
import datetime

author_0_obj = Author("Author_0").attributes(**{'name': "Str", 'email': "Str"}).build()
author_1_obj = Author("Author_1").attributes(**{'name': "Str", 'email': "Str"}).build()
author_2_obj = Author("Author_2").attributes(**{'name': "Str", 'email': "Str"}).build()
author_3_obj = Author("Author_3").attributes(**{'name': "Str", 'email': "Str"}).build()
author_4_obj = Author("Author_4").attributes(**{'name': "Str", 'email': "Str"}).build()
book_0_obj = Book("Book_0").attributes(**{'pages': 13, 'release': datetime.date(2037, 5, 11), 'title': "Str"}).build()
book_1_obj = Book("Book_1").attributes(**{'pages': 14, 'release': datetime.date(2037, 5, 11), 'title': "Str"}).build()
book_2_obj = Book("Book_2").attributes(**{'pages': -12, 'release': datetime.date(2037, 5, 11), 'title': "Str"}).build()
book_3_obj = Book("Book_3").attributes(**{'pages': 14, 'release': datetime.date(2037, 5, 11), 'title': "Str"}).build()
book_4_obj = Book("Book_4").attributes(**{'pages': 13, 'release': datetime.date(2037, 5, 11), 'title': "Str"}).build()
library_0_obj = Library("Library_0").attributes(**{'address': "Str", 'name': "Str"}).build()
library_1_obj = Library("Library_1").attributes(**{'address': "Str", 'name': "Str"}).build()
library_2_obj = Library("Library_2").attributes(**{'address': "Str", 'name': "Str"}).build()
library_3_obj = Library("Library_3").attributes(**{'address': "Str", 'name': "Str"}).build()
library_4_obj = Library("Library_4").attributes(**{'address': "Str", 'name': "Str"}).build()

# Set relations between objects
setattr(author_0_obj, 'publishes', book_4_obj)
setattr(author_1_obj, 'publishes', {book_2_obj, book_3_obj})
setattr(author_2_obj, 'publishes', {book_1_obj, book_4_obj})
setattr(author_3_obj, 'publishes', {book_1_obj, book_3_obj, book_4_obj})
setattr(author_4_obj, 'publishes', {book_0_obj, book_2_obj})
setattr(book_0_obj, 'locatedIn', library_4_obj)
setattr(book_1_obj, 'locatedIn', library_3_obj)
setattr(book_2_obj, 'locatedIn', library_4_obj)
setattr(book_3_obj, 'locatedIn', library_2_obj)
setattr(book_4_obj, 'locatedIn', library_4_obj)

# Object Model instance
object_model: ObjectModel = ObjectModel(
    name="Object_Diagram",
    objects={author_0_obj, author_1_obj, author_2_obj, author_3_obj, author_4_obj, book_0_obj, book_1_obj, book_2_obj, book_3_obj, book_4_obj, library_0_obj, library_1_obj, library_2_obj, library_3_obj, library_4_obj}
)


######################
# PROJECT DEFINITION #
######################

from besser.BUML.metamodel.project import Project
from besser.BUML.metamodel.structural.structural import Metadata

metadata = Metadata(description="Project generated from an Alloy-consistent instance.")
project = Project(
    name="Alloy_Instance_Project",
    models=[domain_model, object_model],
    owner="BESSER User",
    metadata=metadata
)