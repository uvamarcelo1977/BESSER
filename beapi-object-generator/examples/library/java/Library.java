import java.util.List;
import java.util.ArrayList;

public class Library {
    private String name;
    private String address;
    private String web_page;
    private String telephone;
    private List<Book> books;

    public Library (String name, String address, String web_page, String telephone) {
        this.name = name;
        this.address = address;
        this.web_page = web_page;
        this.telephone = telephone;
        this.books = new ArrayList<>();
    }

    public Library (String name, String address, String web_page, String telephone, List<Book> books) {
        this.name = name;
        this.address = address;
        this.web_page = web_page;
        this.telephone = telephone;
        this.books = books;
    }

    public String getName() {
        return this.name;
    }

    public void setName(String name) {
        this.name = name;
    }

    public String getAddress() {
        return this.address;
    }

    public void setAddress(String address) {
        this.address = address;
    }

    public String getWeb_page() {
        return this.web_page;
    }

    public void setWeb_page(String web_page) {
        this.web_page = web_page;
    }

    public String getTelephone() {
        return this.telephone;
    }

    public void setTelephone(String telephone) {
        this.telephone = telephone;
    }

    public List<Book> getBooks() {
        return this.books;
    }

    public void addBook(Book book) {
        this.books.add(book);
    }

    public String cheapest_book_by(Author author) {
        // TODO: implement cheapest_book_by
        throw new UnsupportedOperationException("cheapest_book_by is not implemented");
    }
}