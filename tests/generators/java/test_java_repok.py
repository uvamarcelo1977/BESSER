"""Tests for the OCL invariant -> Java ``repOk()`` translation.

Every invariant of the LibraryLoan_v2 model is checked against the Java
expression generated for it inside ``repOk()``.
"""

import shutil
import subprocess

import pytest

from besser.generators.java_classes import JavaGenerator
from tests.BUML.metamodel.structural.libraryloan.libraryloan_v2 import domain_model


@pytest.fixture(scope="module")
def output_dir(tmp_path_factory):
    path = tmp_path_factory.mktemp("libraryloan_v2")
    JavaGenerator(model=domain_model, output_dir=str(path)).generate()
    return path


@pytest.fixture(scope="module")
def java_code(output_dir):
    """Generated source of each class, by class name."""
    return {path.stem: path.read_text() for path in output_dir.glob("*.java")}


# --- Book ---

def test_book_positive_values(java_code):
    # self.pages > 0 and self.stock >= 0 and self.price > 0.0
    assert "(((this.getPages() > 0) && (this.getStock() >= 0)) && (this.getPrice() > 0.0f))" in java_code["Book"]


def test_book_has_author(java_code):
    # not self.authors->isEmpty()
    assert "!(this.getAuthors().isEmpty())" in java_code["Book"]


def test_book_release_after_author_birth(java_code):
    # self.authors->forAll(a | a.birth < self.release)
    assert ("this.getAuthors().stream().allMatch(a -> (a.getBirth().compareTo(this.getRelease()) < 0))"
            in java_code["Book"])


def test_book_long_books_price(java_code):
    # self.pages > 1000 implies self.price >= 20.0
    assert "(!((this.getPages() > 1000)) || ((this.getPrice() >= 20.0f)))" in java_code["Book"]


def test_book_price_by_pages(java_code):
    # if self.pages > 500 then self.price >= 15.0 else self.price >= 1.0 endif
    assert ("((this.getPages() > 500) ? (this.getPrice() >= 15.0f) : (this.getPrice() >= 1.0f))"
            in java_code["Book"])


def test_book_stock_xor_items(java_code):
    # (self.stock = 0) xor self.booksitems->exists(i | i.id <> '')
    assert ('((this.getStock() == 0) ^ this.getBooksitems().stream().anyMatch(i -> !Objects.equals(i.getId(), "")))'
            in java_code["Book"])


def test_book_unloaned_items_within_stock(java_code):
    # self.booksitems->select(i | i.users->isEmpty())->size() <= self.stock
    assert ("this.getBooksitems().stream().filter(i -> i.getUsers().isEmpty())"
            ".collect(Collectors.toList()).size() <= this.getStock()" in java_code["Book"])


def test_book_author_names_not_empty(java_code):
    # self.authors->collect(a | a.name)->excludes('')
    assert ('!(this.getAuthors().stream().map(a -> a.getName()).collect(Collectors.toList()).contains(""))'
            in java_code["Book"])


def test_book_inventory_value(java_code):
    # self.price * self.stock <= 1000000.0
    assert "((this.getPrice() * this.getStock()) <= 1000000.0f)" in java_code["Book"]


def test_book_unique_title(java_code):
    # Book::allInstances()->forAll(b1, b2 | b1 <> b2 implies b1.title <> b2.title)
    assert "static final List<Book> allInstances = new ArrayList<>();" in java_code["Book"]
    assert ("Book.allInstances.stream().allMatch(b1 -> Book.allInstances.stream().allMatch(b2 -> "
            "(!(!Objects.equals(b1, b2)) || (!Objects.equals(b1.getTitle(), b2.getTitle())))))"
            in java_code["Book"])


# --- Author ---

def test_author_more_than_one_book(java_code):
    # self.books->size() > 1
    assert "(this.getBooks().size() > 1)" in java_code["Author"]


def test_author_bidirectional(java_code):
    # self.books->forAll(b | b.authors->includes(self))
    assert "this.getBooks().stream().allMatch(b -> b.getAuthors().contains(this))" in java_code["Author"]


def test_author_born_in_the_past(java_code):
    # self.birth < Date::today()
    assert "(this.getBirth().compareTo(LocalDate.now()) < 0)" in java_code["Author"]


def test_author_unique_name(java_code):
    # Author::allInstances()->select(a | a.name = self.name)->size() = 1
    assert ("Author.allInstances.stream().filter(a -> Objects.equals(a.getName(), this.getName()))"
            ".collect(Collectors.toList()).size() == 1" in java_code["Author"])


# --- Library ---

def test_library_total_stock(java_code):
    # self.books->collect(b | b.stock)->sum() > 0
    assert ("this.getBooks().stream().map(b -> b.getStock()).collect(Collectors.toList())"
            ".stream().mapToInt(Integer::intValue).sum() > 0" in java_code["Library"])


def test_library_contact(java_code):
    # self.web_page <> '' or self.telephone <> ''
    assert ('(!Objects.equals(this.getWeb_page(), "") || !Objects.equals(this.getTelephone(), ""))'
            in java_code["Library"])


def test_library_not_all_out_of_stock(java_code):
    # self.books->reject(b | b.stock > 0)->size() < self.books->size()
    assert ("this.getBooks().stream().filter(b -> !((b.getStock() > 0))).collect(Collectors.toList()).size()"
            " < this.getBooks().size()" in java_code["Library"])


def test_library_expensive_books_long(java_code):
    # self.books->select(b | b.price > 100.0)->forAll(b | b.pages >= 100)
    assert ("this.getBooks().stream().filter(b -> (b.getPrice() > 100.0f)).collect(Collectors.toList())"
            ".stream().allMatch(b -> (b.getPages() >= 100))" in java_code["Library"])


# --- BookItem ---

def test_book_item_loaned_in_library(java_code):
    # self.users->size() > 0 implies self.book.library->size() >= 1
    assert ("(!((this.getUsers().size() > 0)) || ((this.getBook().getLibrary().size() >= 1)))"
            in java_code["BookItem"])


def test_book_item_book_is_book(java_code):
    # self.book.oclIsTypeOf(Book) and self.publisher <> ''
    assert ('((this.getBook() != null && this.getBook().getClass() == Book.class)'
            ' && !Objects.equals(this.getPublisher(), ""))' in java_code["BookItem"])


# --- User ---

def test_user_password_length(java_code):
    # self.password.size() >= 8 and self.password <> self.name
    assert ("((this.getPassword().length() >= 8) && !Objects.equals(this.getPassword(), this.getName()))"
            in java_code["User"])


def test_user_max_expensive_items(java_code):
    # self.items->select(i | i.book.price > 50.0)->size() <= 3
    assert ("this.getItems().stream().filter(i -> (i.getBook().getPrice() > 50.0f))"
            ".collect(Collectors.toList()).size() <= 3" in java_code["User"])


def test_user_no_duplicate_books(java_code):
    # self.items->collect(i | i.book)->asSet()->size() = self.items->size()
    assert ("this.getItems().stream().map(i -> i.getBook()).collect(Collectors.toList())"
            ".stream().distinct().collect(Collectors.toList()).size() == this.getItems().size()"
            in java_code["User"])


def test_user_unique_id(java_code):
    # User::allInstances()->forAll(u | u <> self implies u.id <> self.id)
    assert ("User.allInstances.stream().allMatch(u -> "
            "(!(!Objects.equals(u, this)) || (!Objects.equals(u.getId(), this.getId()))))" in java_code["User"])


# --- Loan ---

def test_loan_due_after_borrow(java_code):
    # self.dueDate > self.borrowDate
    assert "(this.getDueDate().compareTo(this.getBorrowDate()) > 0)" in java_code["Loan"]


def test_loan_return_after_borrow(java_code):
    # self.returnDate <> null implies self.returnDate >= self.borrowDate
    assert ("(!((this.getReturnDate() != null)) || ((this.getReturnDate().compareTo(this.getBorrowDate()) >= 0)))"
            in java_code["Loan"])


# --- Generated code ---

@pytest.mark.skipif(shutil.which("javac") is None, reason="no JDK available")
def test_generated_code_compiles(output_dir):
    sources = [str(path) for path in output_dir.rglob("*.java")]
    result = subprocess.run(["javac", "-d", str(output_dir / "classes"), *sources], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
