import java.time.LocalDate;
import java.util.List;
import java.util.ArrayList;

public class Booking {
    private int id;
    private LocalDate check_in;
    private LocalDate check_out;
    private BookingStatus booking_status;
    private StayStatus stay_status;
    private float price;
    private List<Guest> guests;
    private Invoice invoice;
    private Person booking_contact;
    private Employee managed_by;
    private List<Room> rooms;

    public Booking (int id, LocalDate check_in, LocalDate check_out, BookingStatus booking_status, StayStatus stay_status, float price) {
        this.id = id;
        this.check_in = check_in;
        this.check_out = check_out;
        this.booking_status = booking_status;
        this.stay_status = stay_status;
        this.price = price;
        this.guests = new ArrayList<>();
        this.rooms = new ArrayList<>();
    }

    public Booking (int id, LocalDate check_in, LocalDate check_out, BookingStatus booking_status, StayStatus stay_status, float price, List<Guest> guests, List<Room> rooms) {
        this.id = id;
        this.check_in = check_in;
        this.check_out = check_out;
        this.booking_status = booking_status;
        this.stay_status = stay_status;
        this.price = price;
        this.guests = guests;
        this.rooms = rooms;
    }

    public int getId() {
        return this.id;
    }

    public void setId(int id) {
        this.id = id;
    }

    public LocalDate getCheck_in() {
        return this.check_in;
    }

    public void setCheck_in(LocalDate check_in) {
        this.check_in = check_in;
    }

    public LocalDate getCheck_out() {
        return this.check_out;
    }

    public void setCheck_out(LocalDate check_out) {
        this.check_out = check_out;
    }

    public BookingStatus getBooking_status() {
        return this.booking_status;
    }

    public void setBooking_status(BookingStatus booking_status) {
        this.booking_status = booking_status;
    }

    public StayStatus getStay_status() {
        return this.stay_status;
    }

    public void setStay_status(StayStatus stay_status) {
        this.stay_status = stay_status;
    }

    public float getPrice() {
        return this.price;
    }

    public void setPrice(float price) {
        this.price = price;
    }

    public List<Guest> getGuests() {
        return this.guests;
    }

    public void addGuest(Guest guest) {
        this.guests.add(guest);
    }

    public Invoice getInvoice() {
        return this.invoice;
    }

    public void setInvoice(Invoice invoice) {
        this.invoice = invoice;
    }

    public Person getBooking_contact() {
        return this.booking_contact;
    }

    public void setBooking_contact(Person booking_contact) {
        this.booking_contact = booking_contact;
    }

    public Employee getManaged_by() {
        return this.managed_by;
    }

    public void setManaged_by(Employee managed_by) {
        this.managed_by = managed_by;
    }

    public List<Room> getRooms() {
        return this.rooms;
    }

    public void addRoom(Room room) {
        this.rooms.add(room);
    }

    public boolean generate_invoice() {
        if (this.invoice != null) {
            return false;
        }

        this.invoice = new Invoice(0, LocalDate.now(), calculate_price(), false);
        this.invoice.setBooking(this);
        return true;
    }

    public boolean register_arrival() {
        if (this.booking_status != BookingStatus.confirmed
                || this.stay_status != StayStatus.not_arrived) {
            return false;
        }

        this.stay_status = StayStatus.checked_in;
        return true;
    }

    public boolean register_departure() {
        if (this.stay_status != StayStatus.checked_in) {
            return false;
        }

        this.stay_status = StayStatus.checked_out;
        return true;
    }

    public boolean cancel() {
        if (this.booking_status == BookingStatus.canceled
                || this.stay_status != StayStatus.not_arrived) {
            return false;
        }

        this.booking_status = BookingStatus.canceled;
        return true;
    }

    public float calculate_price() {
        long nights = java.time.temporal.ChronoUnit.DAYS.between(this.check_in, this.check_out);
        float total = 0.0f;
        for (Room room : this.rooms) {
            total += room.getPrice() * nights;
        }
        this.price = total;
        return this.price;
    }
}