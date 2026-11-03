import java.time.LocalDate;
import java.util.List;
import java.util.ArrayList;
import besser.trace.*;

@BClass(id = "81016b08-b660-5342-80f8-5c90f7397a80", name = "Author", model = "Library_with_OCL")
public class Author {
    private LocalDate birth;
    private String name;
    private List<Book> books;

    public Author (LocalDate birth, String name) {
        this.birth = birth;
        this.name = name;
        this.books = new ArrayList<>();
    }

    public Author (LocalDate birth, String name, List<Book> books) {
        this.birth = birth;
        this.name = name;
        this.books = books;
    }

    @BAttribute(id = "9ba34131-ca01-57d5-b51c-a8247287d406", name = "birth", type = "date")
    public LocalDate getBirth() {
        return this.birth;
    }

    public void setBirth(LocalDate birth) {
        this.birth = birth;
    }

    @BAttribute(id = "2a863be4-18a5-5ee2-aca1-6a9b301f4988", name = "name", type = "str")
    public String getName() {
        return this.name;
    }

    public void setName(String name) {
        this.name = name;
    }

    @BAssociationEnd(
        id = "143ad4cf-1d99-56f6-ba8f-9346986e003c",
        name = "books",
        type = Book.class,
        lower = 0,
        upper = BTrace.MANY,
        association = "books_1",
        associationId = "e432a0cb-2c73-5459-9307-c4379d4561f1",
        opposite = "authors")
    public List<Book> getBooks() {
        return this.books;
    }

    public void addBook(Book book) {
        this.books.add(book);
    }

    /** Checks the OCL invariants of Author. */
    public boolean repOk() {
        // author_named: context Author inv author_named: self.name.size() > 0
        try {
            if (!((this.getName().length() > 0))) {
                return false;
            }
        } catch (NullPointerException e) {
            // Navigating through null makes the OCL invariant undefined.
            return false;
        }
        return true;
    }
}