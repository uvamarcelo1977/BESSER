import java.time.LocalDate;
import java.util.List;
import java.util.ArrayList;
import besser.trace.*;

@BClass(id = "8e8061d7-a7f7-5429-93d2-0c199be963ee", name = "Book", model = "Library_with_OCL")
public class Book {
    private int pages;
    private int stock;
    private LocalDate release;
    private float price;
    private String title;
    private Genre genre;
    private List<Author> authors;
    private List<Library> library;

    public Book (int pages, int stock, LocalDate release, float price, String title, Genre genre) {
        this.pages = pages;
        this.stock = stock;
        this.release = release;
        this.price = price;
        this.title = title;
        this.genre = genre;
        this.authors = new ArrayList<>();
        this.library = new ArrayList<>();
    }

    public Book (int pages, int stock, LocalDate release, float price, String title, Genre genre, List<Author> authors, List<Library> library) {
        this.pages = pages;
        this.stock = stock;
        this.release = release;
        this.price = price;
        this.title = title;
        this.genre = genre;
        this.authors = authors;
        this.library = library;
    }

    @BAttribute(id = "c6e22ddc-5521-583f-a2c7-4fb011646dca", name = "pages", type = "int")
    public int getPages() {
        return this.pages;
    }

    public void setPages(int pages) {
        this.pages = pages;
    }

    @BAttribute(id = "54997292-021e-5ec3-9d27-253e4d4ba143", name = "stock", type = "int")
    public int getStock() {
        return this.stock;
    }

    public void setStock(int stock) {
        this.stock = stock;
    }

    @BAttribute(id = "83a38881-d1b0-58f2-a10f-84363ce7d6b6", name = "release", type = "date")
    public LocalDate getRelease() {
        return this.release;
    }

    public void setRelease(LocalDate release) {
        this.release = release;
    }

    @BAttribute(id = "8a0d2369-1414-5932-8512-4ef29a70db76", name = "price", type = "float")
    public float getPrice() {
        return this.price;
    }

    public void setPrice(float price) {
        this.price = price;
    }

    @BAttribute(id = "d149ff8a-3087-5d04-8c29-f3c930f0ea01", name = "title", type = "str")
    public String getTitle() {
        return this.title;
    }

    public void setTitle(String title) {
        this.title = title;
    }

    @BAttribute(id = "779ec665-1ec9-5bb8-ad61-1a06b8d0db1a", name = "genre", type = "Genre")
    public Genre getGenre() {
        return this.genre;
    }

    public void setGenre(Genre genre) {
        this.genre = genre;
    }

    @BAssociationEnd(
        id = "232707d6-6fd3-526c-9a8b-51c2e56e6e2e",
        name = "authors",
        type = Author.class,
        upper = BTrace.MANY,
        association = "books_1",
        associationId = "e432a0cb-2c73-5459-9307-c4379d4561f1",
        opposite = "books")
    public List<Author> getAuthors() {
        return this.authors;
    }

    public void addAuthor(Author author) {
        this.authors.add(author);
    }

    @BAssociationEnd(
        id = "3ad214ad-9f4e-551f-8a87-8ef5cdeefda2",
        name = "library",
        type = Library.class,
        upper = BTrace.MANY,
        association = "books",
        associationId = "0b70af27-039f-5edd-a193-1019e465f3d0",
        opposite = "books")
    public List<Library> getLibrary() {
        return this.library;
    }

    public void addLibrary(Library library) {
        this.library.add(library);
    }

    public void decrease_stock(int qty) {
        // TODO: implement decrease_stock
        throw new UnsupportedOperationException("decrease_stock is not implemented");
    }

    /** Checks the OCL invariants of Book. */
    public boolean repOk() {
        // book_has_title: context Book inv book_has_title: self.title.size() > 0
        try {
            if (!((this.getTitle().length() > 0))) {
                return false;
            }
        } catch (NullPointerException e) {
            // Navigating through null makes the OCL invariant undefined.
            return false;
        }
        // book_nonneg_price: context Book inv book_nonneg_price: self.price >= 0
        try {
            if (!((this.getPrice() >= 0))) {
                return false;
            }
        } catch (NullPointerException e) {
            // Navigating through null makes the OCL invariant undefined.
            return false;
        }
        // book_nonneg_stock: context Book inv book_nonneg_stock: self.stock >= 0
        try {
            if (!((this.getStock() >= 0))) {
                return false;
            }
        } catch (NullPointerException e) {
            // Navigating through null makes the OCL invariant undefined.
            return false;
        }
        // book_positive_pages: context Book inv book_positive_pages: self.pages > 0
        try {
            if (!((this.getPages() > 0))) {
                return false;
            }
        } catch (NullPointerException e) {
            // Navigating through null makes the OCL invariant undefined.
            return false;
        }
        return true;
    }
}