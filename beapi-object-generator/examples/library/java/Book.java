import java.time.LocalDate;
import java.util.List;
import java.util.ArrayList;

public class Book {
    private float price;
    private int stock;
    private LocalDate release;
    private String title;
    private Genre genre;
    private int pages;
    private List<Library> library;
    private List<Author> authors;

    public Book (float price, int stock, LocalDate release, String title, Genre genre, int pages) {
        this.price = price;
        this.stock = stock;
        this.release = release;
        this.title = title;
        this.genre = genre;
        this.pages = pages;
        this.library = new ArrayList<>();
        this.authors = new ArrayList<>();
    }

    public Book (float price, int stock, LocalDate release, String title, Genre genre, int pages, List<Library> library, List<Author> authors) {
        this.price = price;
        this.stock = stock;
        this.release = release;
        this.title = title;
        this.genre = genre;
        this.pages = pages;
        this.library = library;
        this.authors = authors;
    }

    public float getPrice() {
        return this.price;
    }

    public void setPrice(float price) {
        this.price = price;
    }

    public int getStock() {
        return this.stock;
    }

    public void setStock(int stock) {
        this.stock = stock;
    }

    public LocalDate getRelease() {
        return this.release;
    }

    public void setRelease(LocalDate release) {
        this.release = release;
    }

    public String getTitle() {
        return this.title;
    }

    public void setTitle(String title) {
        this.title = title;
    }

    public Genre getGenre() {
        return this.genre;
    }

    public void setGenre(Genre genre) {
        this.genre = genre;
    }

    public int getPages() {
        return this.pages;
    }

    public void setPages(int pages) {
        this.pages = pages;
    }

    public List<Library> getLibrary() {
        return this.library;
    }

    public void addLibrary(Library library) {
        this.library.add(library);
    }

    public List<Author> getAuthors() {
        return this.authors;
    }

    public void addAuthor(Author author) {
        this.authors.add(author);
    }

    public void decrease_stock(int qty) {
        // TODO: implement decrease_stock
        throw new UnsupportedOperationException("decrease_stock is not implemented");
    }
}