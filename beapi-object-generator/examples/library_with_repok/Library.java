import java.util.List;
import java.util.ArrayList;
import besser.trace.*;

@BClass(id = "7608dad3-0eb5-5dcd-b2b9-35eb46157627", name = "Library", model = "Library_with_OCL")
public class Library {
    private String web_page;
    private String telephone;
    private String address;
    private String name;
    private List<Book> books;

    public Library (String web_page, String telephone, String address, String name) {
        this.web_page = web_page;
        this.telephone = telephone;
        this.address = address;
        this.name = name;
        this.books = new ArrayList<>();
    }

    public Library (String web_page, String telephone, String address, String name, List<Book> books) {
        this.web_page = web_page;
        this.telephone = telephone;
        this.address = address;
        this.name = name;
        this.books = books;
    }

    @BAttribute(id = "d5a75ea7-6d7c-5e86-a1a7-014b56ffeccd", name = "web_page", type = "str")
    public String getWeb_page() {
        return this.web_page;
    }

    public void setWeb_page(String web_page) {
        this.web_page = web_page;
    }

    @BAttribute(id = "2c5394c9-952d-50e0-a9ad-302d219b858e", name = "telephone", type = "str")
    public String getTelephone() {
        return this.telephone;
    }

    public void setTelephone(String telephone) {
        this.telephone = telephone;
    }

    @BAttribute(id = "e9582813-5414-5a79-bbf4-489fbf2b2f53", name = "address", type = "str")
    public String getAddress() {
        return this.address;
    }

    public void setAddress(String address) {
        this.address = address;
    }

    @BAttribute(id = "906858f9-6141-544c-8984-47429dc7ea23", name = "name", type = "str")
    public String getName() {
        return this.name;
    }

    public void setName(String name) {
        this.name = name;
    }

    @BAssociationEnd(
        id = "0e3d77af-6448-52bd-b174-8ce98b038057",
        name = "books",
        type = Book.class,
        lower = 0,
        upper = BTrace.MANY,
        association = "books",
        associationId = "0b70af27-039f-5edd-a193-1019e465f3d0",
        opposite = "library")
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

    /** Checks the OCL invariants of Library. */
    public boolean repOk() {
        // library_has_books: context Library inv library_has_books: self.books->size() > 0
        try {
            if (!((this.getBooks().size() > 0))) {
                return false;
            }
        } catch (NullPointerException e) {
            // Navigating through null makes the OCL invariant undefined.
            return false;
        }
        // library_named: context Library inv library_named: self.name.size() > 0
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