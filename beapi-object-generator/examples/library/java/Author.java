import java.time.LocalDate;
import java.util.List;
import java.util.ArrayList;

public class Author {
    private String name;
    private LocalDate birth;
    private List<Book> books;

    public Author (String name, LocalDate birth) {
        this.name = name;
        this.birth = birth;
        this.books = new ArrayList<>();
    }

    public Author (String name, LocalDate birth, List<Book> books) {
        this.name = name;
        this.birth = birth;
        this.books = books;
    }

    public String getName() {
        return this.name;
    }

    public void setName(String name) {
        this.name = name;
    }

    public LocalDate getBirth() {
        return this.birth;
    }

    public void setBirth(LocalDate birth) {
        this.birth = birth;
    }

    public List<Book> getBooks() {
        return this.books;
    }

    public void addBook(Book book) {
        this.books.add(book);
    }
}