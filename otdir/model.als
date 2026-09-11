open util/boolean
open util/integer
open util/ordering[Date]

-- Basic signatures
sig Str {}
sig Date {}


-- Helper functions

fun image [s: univ -> univ]: set univ { { f: univ | some i: univ | i -> f in s } }

fun toSeq [a: set univ, rel: univ -> univ]: univ -> univ { a <: rel }
fun collect [s: univ -> univ, r: univ -> univ]: univ -> univ { s.r }

one sig date0 extends Date {}
one sig date1 extends Date {}
one sig date2 extends Date {}
one sig date3 extends Date {}
one sig date4 extends Date {}
fact Order {
    date0 = first
    date0.next = date1
    date1.next = date2
    date2.next = date3
    date3.next = date4
    date4 = last
}



-- Classes
sig Author {
  Author_name: Str,
  Author_email: Str,
  Author_publishes: set Book
}

sig Book {
  Book_pages: Int,
  Book_release: Date,
  Book_title: Str,
  Book_writtenBy: set Author,
  Book_locatedIn: one Library
}

sig Library {
  Library_address: Str,
  Library_name: Str,
  Library_has: set Book
}






fact{all b: Book | #(b.Book_writtenBy)>=1 }
fact{Author_publishes= ~Book_writtenBy}


fact{Book_locatedIn= ~Library_has}

pred instance_model {
  some Author
  some Str
  some Book
  some Date
  some Library
}

run instance_model for 5 Author, 5 Str, 5 Book, 5 Date, 5 Library, 5 Int