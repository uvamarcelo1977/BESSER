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

CopyStatus: Enumeration = Enumeration(
    name="CopyStatus",
    literals={
            EnumerationLiteral(name="AVAILABLE"),
			EnumerationLiteral(name="BORROWED"),
			EnumerationLiteral(name="RESERVED")
    }
)

# Classes
Book = Class(name="Book")
Library = Class(name="Library")
Author = Class(name="Author")
BookItem = Class(name="BookItem")
User = Class(name="User")

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

# BookItem class attributes and methods
BookItem_id: Property = Property(name="id", type=StringType)
BookItem_publisher: Property = Property(name="publisher", type=StringType)
BookItem_status: Property = Property(name="status", type=CopyStatus)
BookItem.attributes={BookItem_id, BookItem_publisher, BookItem_status}

# User class attributes and methods
User_name: Property = Property(name="name", type=StringType)
User_password: Property = Property(name="password", type=StringType)
User_id: Property = Property(name="id", type=StringType)
User.attributes={User_id, User_name, User_password}

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
BookItem_Book: BinaryAssociation = BinaryAssociation(
    name="BookItem_Book",
    ends={
        Property(name="booksitems", type=BookItem, multiplicity=Multiplicity(0, 9999)),
        Property(name="book", type=Book, multiplicity=Multiplicity(1, 1))
    }
)

# Association Classes
User_BookItem: BinaryAssociation = BinaryAssociation(
    name="User_BookItem",
    ends={
        Property(name="users", type=User, multiplicity=Multiplicity(0, 9999)),
        Property(name="items", type=BookItem, multiplicity=Multiplicity(0, 9999))
    }
)

Loan_borrowDate: Property = Property(name="borrowDate", type=DateType)
Loan_dueDate: Property = Property(name="dueDate", type=DateType)
Loan_returnDate: Property = Property(name="returnDate", type=DateType)
Loan = AssociationClass(
    name="Loan",
    attributes={Loan_borrowDate, Loan_dueDate, Loan_returnDate}, association=User_BookItem
)



# OCL Constraints

# --- Book ---
# Operador and (encadenado)
Book_inv_positiveValues: Constraint = Constraint(
    name="Book_inv_positiveValues",
    context=Book,
    expression="context Book inv Book_inv_positiveValues : self.pages > 0 and self.stock >= 0 and self.price > 0.0",
    language="OCL"
)
# not + isEmpty()
Book_inv_hasAuthor: Constraint = Constraint(
    name="Book_inv_hasAuthor",
    context=Book,
    expression="context Book inv Book_inv_hasAuthor : not self.authors->isEmpty()",
    language="OCL"
)
# forAll con navegacion
Book_inv_releaseAfterAuthorBirth: Constraint = Constraint(
    name="Book_inv_releaseAfterAuthorBirth",
    context=Book,
    expression="context Book inv Book_inv_releaseAfterAuthorBirth : self.authors->forAll(a | a.birth < self.release)",
    language="OCL"
)
# implies
Book_inv_longBooksPrice: Constraint = Constraint(
    name="Book_inv_longBooksPrice",
    context=Book,
    expression="context Book inv Book_inv_longBooksPrice : self.pages > 1000 implies self.price >= 20.0",
    language="OCL"
)
# if-then-else
Book_inv_priceByPages: Constraint = Constraint(
    name="Book_inv_priceByPages",
    context=Book,
    expression="context Book inv Book_inv_priceByPages : if self.pages > 500 then self.price >= 15.0 else self.price >= 1.0 endif",
    language="OCL"
)
# xor + exists
Book_inv_stockXorItems: Constraint = Constraint(
    name="Book_inv_stockXorItems",
    context=Book,
    expression="context Book inv Book_inv_stockXorItems : (self.stock = 0) xor self.booksitems->exists(i | i.id <> '')",
    language="OCL"
)
# select + isEmpty() + size()
Book_inv_unloanedItemsWithinStock: Constraint = Constraint(
    name="Book_inv_unloanedItemsWithinStock",
    context=Book,
    expression="context Book inv Book_inv_unloanedItemsWithinStock : self.booksitems->select(i | i.users->isEmpty())->size() <= self.stock",
    language="OCL"
)
# collect + excludes
Book_inv_authorNamesNotEmpty: Constraint = Constraint(
    name="Book_inv_authorNamesNotEmpty",
    context=Book,
    expression="context Book inv Book_inv_authorNamesNotEmpty : self.authors->collect(a | a.name)->excludes('')",
    language="OCL"
)
# Aritmetica (*)
Book_inv_inventoryValue: Constraint = Constraint(
    name="Book_inv_inventoryValue",
    context=Book,
    expression="context Book inv Book_inv_inventoryValue : self.price * self.stock <= 1000000.0",
    language="OCL"
)
# allInstances() + forAll con dos iteradores
Book_inv_uniqueTitle: Constraint = Constraint(
    name="Book_inv_uniqueTitle",
    context=Book,
    expression="context Book inv Book_inv_uniqueTitle : Book::allInstances()->forAll(b1, b2 | b1 <> b2 implies b1.title <> b2.title)",
    language="OCL"
)

# --- Author ---
# Invariante original del JSON
Author_inv_1_1: Constraint = Constraint(
    name="Author_inv_1_1",
    context=Author,
    expression="context Author inv Author_inv_1_1 : self.books->size()>1",
    language="OCL"
)
# forAll + includes
Author_inv_bidirectional: Constraint = Constraint(
    name="Author_inv_bidirectional",
    context=Author,
    expression="context Author inv Author_inv_bidirectional : self.books->forAll(b | b.authors->includes(self))",
    language="OCL"
)
# Date::today()
Author_inv_bornInThePast: Constraint = Constraint(
    name="Author_inv_bornInThePast",
    context=Author,
    expression="context Author inv Author_inv_bornInThePast : self.birth < Date::today()",
    language="OCL"
)
# allInstances() + select + size()
Author_inv_uniqueName: Constraint = Constraint(
    name="Author_inv_uniqueName",
    context=Author,
    expression="context Author inv Author_inv_uniqueName : Author::allInstances()->select(a | a.name = self.name)->size() = 1",
    language="OCL"
)

# --- Library ---
# collect + sum()
Library_inv_totalStock: Constraint = Constraint(
    name="Library_inv_totalStock",
    context=Library,
    expression="context Library inv Library_inv_totalStock : self.books->collect(b | b.stock)->sum() > 0",
    language="OCL"
)
# Operador or
Library_inv_contact: Constraint = Constraint(
    name="Library_inv_contact",
    context=Library,
    expression="context Library inv Library_inv_contact : self.web_page <> '' or self.telephone <> ''",
    language="OCL"
)
# reject + size()
Library_inv_notAllOutOfStock: Constraint = Constraint(
    name="Library_inv_notAllOutOfStock",
    context=Library,
    expression="context Library inv Library_inv_notAllOutOfStock : self.books->reject(b | b.stock > 0)->size() < self.books->size()",
    language="OCL"
)
# select encadenado con forAll
Library_inv_expensiveBooksLong: Constraint = Constraint(
    name="Library_inv_expensiveBooksLong",
    context=Library,
    expression="context Library inv Library_inv_expensiveBooksLong : self.books->select(b | b.price > 100.0)->forAll(b | b.pages >= 100)",
    language="OCL"
)

# --- BookItem ---
# implies + size() + navegacion encadenada
BookItem_inv_loanedInLibrary: Constraint = Constraint(
    name="BookItem_inv_loanedInLibrary",
    context=BookItem,
    expression="context BookItem inv BookItem_inv_loanedInLibrary : self.users->size() > 0 implies self.book.library->size() >= 1",
    language="OCL"
)
# oclIsTypeOf
BookItem_inv_bookIsBook: Constraint = Constraint(
    name="BookItem_inv_bookIsBook",
    context=BookItem,
    expression="context BookItem inv BookItem_inv_bookIsBook : self.book.oclIsTypeOf(Book) and self.publisher <> ''",
    language="OCL"
)

# --- User ---
# size() sobre String + and
User_inv_passwordLength: Constraint = Constraint(
    name="User_inv_passwordLength",
    context=User,
    expression="context User inv User_inv_passwordLength : self.password.size() >= 8 and self.password <> self.name",
    language="OCL"
)
# select + navegacion + size()
User_inv_maxExpensiveItems: Constraint = Constraint(
    name="User_inv_maxExpensiveItems",
    context=User,
    expression="context User inv User_inv_maxExpensiveItems : self.items->select(i | i.book.price > 50.0)->size() <= 3",
    language="OCL"
)
# collect + asSet() + size()
User_inv_noDuplicateBooks: Constraint = Constraint(
    name="User_inv_noDuplicateBooks",
    context=User,
    expression="context User inv User_inv_noDuplicateBooks : self.items->collect(i | i.book)->asSet()->size() = self.items->size()",
    language="OCL"
)
# allInstances() + forAll + implies
User_inv_uniqueId: Constraint = Constraint(
    name="User_inv_uniqueId",
    context=User,
    expression="context User inv User_inv_uniqueId : User::allInstances()->forAll(u | u <> self implies u.id <> self.id)",
    language="OCL"
)

# --- Loan ---
# Comparacion de fechas en clase asociacion
Loan_inv_dueAfterBorrow: Constraint = Constraint(
    name="Loan_inv_dueAfterBorrow",
    context=Loan,
    expression="context Loan inv Loan_inv_dueAfterBorrow : self.dueDate > self.borrowDate",
    language="OCL"
)
# null + implies
Loan_inv_returnAfterBorrow: Constraint = Constraint(
    name="Loan_inv_returnAfterBorrow",
    context=Loan,
    expression="context Loan inv Loan_inv_returnAfterBorrow : self.returnDate <> null implies self.returnDate >= self.borrowDate",
    language="OCL"
)

# Domain Model
domain_model = DomainModel(
    name="LibraryLoan_v2",
    types={Book, Library, Author, BookItem, User, Loan, Genre, CopyStatus},
    associations={books, books_1, BookItem_Book, User_BookItem},
    constraints={
        Book_inv_positiveValues,
        Book_inv_hasAuthor,
        Book_inv_releaseAfterAuthorBirth,
        Book_inv_longBooksPrice,
        Book_inv_priceByPages,
        Book_inv_stockXorItems,
        Book_inv_unloanedItemsWithinStock,
        Book_inv_authorNamesNotEmpty,
        Book_inv_inventoryValue,
        Book_inv_uniqueTitle,
        Author_inv_1_1,
        Author_inv_bidirectional,
        Author_inv_bornInThePast,
        Author_inv_uniqueName,
        Library_inv_totalStock,
        Library_inv_contact,
        Library_inv_notAllOutOfStock,
        Library_inv_expensiveBooksLong,
        BookItem_inv_loanedInLibrary,
        BookItem_inv_bookIsBook,
        User_inv_passwordLength,
        User_inv_maxExpensiveItems,
        User_inv_noDuplicateBooks,
        User_inv_uniqueId,
        Loan_inv_dueAfterBorrow,
        Loan_inv_returnAfterBorrow
    },
    generalizations={},
    metadata=None
)


######################
# PROJECT DEFINITION #
######################

from besser.BUML.metamodel.project import Project
from besser.BUML.metamodel.structural.structural import Metadata

metadata = Metadata(description="Library Loan BUML Model with OCL constraints (v2)")
project = Project(
    name="LibraryLoan_v2",
    models=[domain_model],
    owner="BESSER User",
    metadata=metadata
)
