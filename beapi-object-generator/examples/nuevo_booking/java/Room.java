import java.util.List;
import java.util.ArrayList;

public class Room {
    private int number;
    private int max_people;
    private String description;
    private float price;
    private List<Booking> booking;

    public Room (int number, int max_people, String description, float price) {
        this.number = number;
        this.max_people = max_people;
        this.description = description;
        this.price = price;
        this.booking = new ArrayList<>();
    }

    public Room (int number, int max_people, String description, float price, List<Booking> booking) {
        this.number = number;
        this.max_people = max_people;
        this.description = description;
        this.price = price;
        this.booking = booking;
    }

    public int getNumber() {
        return this.number;
    }

    public void setNumber(int number) {
        this.number = number;
    }

    public int getMax_people() {
        return this.max_people;
    }

    public void setMax_people(int max_people) {
        this.max_people = max_people;
    }

    public String getDescription() {
        return this.description;
    }

    public void setDescription(String description) {
        this.description = description;
    }

    public float getPrice() {
        return this.price;
    }

    public void setPrice(float price) {
        this.price = price;
    }

    public List<Booking> getBooking() {
        return this.booking;
    }

    public void addBooking(Booking booking) {
        this.booking.add(booking);
    }
}