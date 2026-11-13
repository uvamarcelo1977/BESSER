import java.util.List;
import java.util.ArrayList;

public class Person {
    private int id;
    private String name;
    private String last_name;
    private String phone_number;
    private String email;
    private List<Booking> bookings;

    public Person (int id, String name, String last_name, String phone_number, String email) {
        this.id = id;
        this.name = name;
        this.last_name = last_name;
        this.phone_number = phone_number;
        this.email = email;
        this.bookings = new ArrayList<>();
    }

    public Person (int id, String name, String last_name, String phone_number, String email, List<Booking> bookings) {
        this.id = id;
        this.name = name;
        this.last_name = last_name;
        this.phone_number = phone_number;
        this.email = email;
        this.bookings = bookings;
    }

    public int getId() {
        return this.id;
    }

    public void setId(int id) {
        this.id = id;
    }

    public String getName() {
        return this.name;
    }

    public void setName(String name) {
        this.name = name;
    }

    public String getLast_name() {
        return this.last_name;
    }

    public void setLast_name(String last_name) {
        this.last_name = last_name;
    }

    public String getPhone_number() {
        return this.phone_number;
    }

    public void setPhone_number(String phone_number) {
        this.phone_number = phone_number;
    }

    public String getEmail() {
        return this.email;
    }

    public void setEmail(String email) {
        this.email = email;
    }

    public List<Booking> getBookings() {
        return this.bookings;
    }

    public void addBooking(Booking booking) {
        this.bookings.add(booking);
    }
}