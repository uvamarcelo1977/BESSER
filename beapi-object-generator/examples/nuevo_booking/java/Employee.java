import java.util.List;
import java.util.ArrayList;

public class Employee extends Person{
    private List<Booking> manages;

    public Employee (int id, String name, String last_name, String phone_number, String email) {
        super(id, name, last_name, phone_number, email);
        this.manages = new ArrayList<>();
    }

    public Employee (int id, String name, String last_name, String phone_number, String email, List<Booking> manages) {
        super(id, name, last_name, phone_number, email);
        this.manages = manages;
    }

    public List<Booking> getManages() {
        return this.manages;
    }

    public void addBooking(Booking booking) {
        this.manages.add(booking);
    }
}