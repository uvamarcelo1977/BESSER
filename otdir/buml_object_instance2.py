from besser.BUML.metamodel.object import ObjectModel
import datetime

author_0_obj = Author("Author_0").attributes(**{'name': "Str", 'email': "Str"}).build()
author_1_obj = Author("Author_1").attributes(**{'name': "Str", 'email': "Str"}).build()
author_2_obj = Author("Author_2").attributes(**{'name': "Str", 'email': "Str"}).build()
author_3_obj = Author("Author_3").attributes(**{'name': "Str", 'email': "Str"}).build()
author_4_obj = Author("Author_4").attributes(**{'name': "Str", 'email': "Str"}).build()
book_0_obj = Book("Book_0").attributes(**{'pages': 14, 'release': datetime.date(1996, 7, 19), 'title': "Str"}).build()
book_1_obj = Book("Book_1").attributes(**{'pages': 13, 'release': datetime.date(1996, 7, 19), 'title': "Str"}).build()
book_2_obj = Book("Book_2").attributes(**{'pages': 14, 'release': datetime.date(1996, 7, 19), 'title': "Str"}).build()
book_3_obj = Book("Book_3").attributes(**{'pages': 13, 'release': datetime.date(1996, 7, 19), 'title': "Str"}).build()
book_4_obj = Book("Book_4").attributes(**{'pages': 14, 'release': datetime.date(1996, 7, 19), 'title': "Str"}).build()
library_0_obj = Library("Library_0").attributes(**{'address': "Str", 'name': "Str"}).build()
library_1_obj = Library("Library_1").attributes(**{'address': "Str", 'name': "Str"}).build()
library_2_obj = Library("Library_2").attributes(**{'address': "Str", 'name': "Str"}).build()
library_3_obj = Library("Library_3").attributes(**{'address': "Str", 'name': "Str"}).build()
library_4_obj = Library("Library_4").attributes(**{'address': "Str", 'name': "Str"}).build()

# Set relations between objects
setattr(author_0_obj, 'publishes', book_4_obj)
setattr(author_1_obj, 'publishes', book_3_obj)
setattr(author_2_obj, 'publishes', {book_2_obj, book_4_obj})
setattr(author_3_obj, 'publishes', {book_0_obj, book_1_obj, book_3_obj})
setattr(author_4_obj, 'publishes', {book_0_obj, book_1_obj, book_2_obj})
setattr(book_0_obj, 'locatedIn', library_4_obj)
setattr(book_1_obj, 'locatedIn', library_4_obj)
setattr(book_2_obj, 'locatedIn', library_4_obj)
setattr(book_3_obj, 'locatedIn', library_4_obj)
setattr(book_4_obj, 'locatedIn', library_3_obj)

# Object Model instance
object_model: ObjectModel = ObjectModel(
    name="Object_Diagram",
    objects={author_0_obj, author_1_obj, author_2_obj, author_3_obj, author_4_obj, book_0_obj, book_1_obj, book_2_obj, book_3_obj, book_4_obj, library_0_obj, library_1_obj, library_2_obj, library_3_obj, library_4_obj}
)