import java.util.List;
import java.util.ArrayList;

public class Guest extends Person{
    private List<Booking> staying;

    public Guest (int id, String name, String last_name, String phone_number, String email) {
        super(id, name, last_name, phone_number, email);
        this.staying = new ArrayList<>();
    }

    public Guest (int id, String name, String last_name, String phone_number, String email, List<Booking> staying) {
        super(id, name, last_name, phone_number, email);
        this.staying = staying;
    }

    public List<Booking> getStaying() {
        return this.staying;
    }

    public void addBooking(Booking booking) {
        this.staying.add(booking);
    }
}