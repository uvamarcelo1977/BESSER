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

# Enumerations
Genre: Enumeration = Enumeration(
    name="Genre",
    literals={
            EnumerationLiteral(name="Poetry"),
			EnumerationLiteral(name="Thriller"),
			EnumerationLiteral(name="History"),
			EnumerationLiteral(name="Technology"),
			EnumerationLiteral(name="Romance"),
			EnumerationLiteral(name="Horror"),
			EnumerationLiteral(name="Adventure"),
			EnumerationLiteral(name="Philosophy"),
			EnumerationLiteral(name="Cookbooks"),
			EnumerationLiteral(name="Fantasy")
    }
)

# Classes
Book = Class(name="Book")
Library = Class(name="Library")
Author = Class(name="Author")

# Book class attributes and methods
Book_title: Property = Property(name="title", type=StringType)
Book_pages: Property = Property(name="pages", type=IntegerType)
Book_stock: Property = Property(name="stock", type=IntegerType)
Book_price: Property = Property(name="price", type=FloatType)
Book_release: Property = Property(name="release", type=DateType)
Book_genre: Property = Property(name="genre", type=Genre)
Book_m_decrease_stock: Method = Method(name="decrease_stock", parameters={Parameter(name='qty', type=IntegerType)}, implementation_type=MethodImplementationType.NONE)
Book.attributes={Book_genre, Book_pages, Book_price, Book_release, Book_stock, Book_title}
Book.methods={Book_m_decrease_stock}

# Library class attributes and methods
Library_name: Property = Property(name="name", type=StringType)
Library_web_page: Property = Property(name="web_page", type=StringType)
Library_address: Property = Property(name="address", type=StringType)
Library_telephone: Property = Property(name="telephone", type=StringType)
Library_m_cheapest_book_by: Method = Method(name="cheapest_book_by", parameters={Parameter(name='author', type=Author)}, type=StringType, implementation_type=MethodImplementationType.BAL)
Library_m_cheapest_book_by.code = """def cheapest_book_by(author:Author) -> str {
    cheapest:Book = null;
	price = 1000000000.0;
	for(book in this.books){
        if(book.authors.contains(author)
			&& book.price <= price){
            cheapest = book;
			price = book.price;
		}
    }
	return cheapest.title;
}"""
Library.attributes={Library_address, Library_name, Library_telephone, Library_web_page}
Library.methods={Library_m_cheapest_book_by}

# Author class attributes and methods
Author_name: Property = Property(name="name", type=StringType)
Author_birth: Property = Property(name="birth", type=DateType)
Author.attributes={Author_birth, Author_name}

# Relationships
books: BinaryAssociation = BinaryAssociation(
    name="books",
    ends={
        Property(name="library", type=Library, multiplicity=Multiplicity(1, 9999)),
        Property(name="books", type=Book, multiplicity=Multiplicity(0, 9999))
    }
)
books_1: BinaryAssociation = BinaryAssociation(
    name="books_1",
    ends={
        Property(name="authors", type=Author, multiplicity=Multiplicity(1, 9999)),
        Property(name="books", type=Book, multiplicity=Multiplicity(0, 9999))
    }
)


# OCL Constraints
book_positive_pages: Constraint = Constraint(
    name="book_positive_pages",
    context=Book,
    expression="context Book inv book_positive_pages: self.pages > 0",
    language="OCL"
)
book_nonneg_stock: Constraint = Constraint(
    name="book_nonneg_stock",
    context=Book,
    expression="context Book inv book_nonneg_stock: self.stock >= 0",
    language="OCL"
)
book_has_title: Constraint = Constraint(
    name="book_has_title",
    context=Book,
    expression="context Book inv book_has_title: self.title.size() > 0",
    language="OCL"
)
book_nonneg_price: Constraint = Constraint(
    name="book_nonneg_price",
    context=Book,
    expression="context Book inv book_nonneg_price: self.price >= 0",
    language="OCL"
)
library_has_books: Constraint = Constraint(
    name="library_has_books",
    context=Library,
    expression="context Library inv library_has_books: self.books->size() > 0",
    language="OCL"
)
library_named: Constraint = Constraint(
    name="library_named",
    context=Library,
    expression="context Library inv library_named: self.name.size() > 0",
    language="OCL"
)
author_named: Constraint = Constraint(
    name="author_named",
    context=Author,
    expression="context Author inv author_named: self.name.size() > 0",
    language="OCL"
)
Author_inv_8_1: Constraint = Constraint(
    name="Author_inv_8_1",
    context=Author,
    expression="context Author inv Author_inv_8_1 : self.books->forAll(b |b.release>=self.birth)",
    language="OCL"
)
Author_inv_9_1: Constraint = Constraint(
    name="Author_inv_9_1",
    context=Author,
    expression="context Author inv Author_inv_9_1 : self.name=\'borges\' implies  self.books->size()>0",
    language="OCL"
)
Author_inv_10_1: Constraint = Constraint(
    name="Author_inv_10_1",
    context=Author,
    expression="context Author inv Author_inv_10_1 : if self.name=\'cortazar\' then self.books->select(b|b.pages>10)->size()>2 else false endif",
    language="OCL"
)
Library_inv_11_1: Constraint = Constraint(
    name="Library_inv_11_1",
    context=Library,
    expression="context Library inv Library_inv_11_1 : self.books-> collect(b |b.authors) ->size()>5",
    language="OCL"
)

# Domain Model
domain_model = DomainModel(
    name="Library_with_OCL",
    types={Book, Library, Author, Genre},
    associations={books, books_1},
    constraints={book_positive_pages, book_nonneg_stock, book_has_title, book_nonneg_price, library_has_books, library_named, author_named, Author_inv_8_1, Author_inv_9_1, Author_inv_10_1, Library_inv_11_1},
    generalizations={},
    metadata=None
)


######################
# PROJECT DEFINITION #
######################

from besser.BUML.metamodel.project import Project
from besser.BUML.metamodel.structural.structural import Metadata

metadata = Metadata(description="")
project = Project(
    name="Genealogy_besser",
    models=[domain_model],
    owner="BESSER User",
    metadata=metadata
)
