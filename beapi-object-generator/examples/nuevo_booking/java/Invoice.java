import java.time.LocalDate;
import java.util.List;
import java.util.ArrayList;

public class Invoice {
    private int id;
    private LocalDate issued_date;
    private float amount;
    private boolean paid;
    private Booking booking;

    public Invoice (int id, LocalDate issued_date, float amount, boolean paid) {
        this.id = id;
        this.issued_date = issued_date;
        this.amount = amount;
        this.paid = paid;
    }



    public int getId() {
        return this.id;
    }

    public void setId(int id) {
        this.id = id;
    }

    public LocalDate getIssued_date() {
        return this.issued_date;
    }

    public void setIssued_date(LocalDate issued_date) {
        this.issued_date = issued_date;
    }

    public float getAmount() {
        return this.amount;
    }

    public void setAmount(float amount) {
        this.amount = amount;
    }

    public boolean getPaid() {
        return this.paid;
    }

    public void setPaid(boolean paid) {
        this.paid = paid;
    }

    public Booking getBooking() {
        return this.booking;
    }

    public void setBooking(Booking booking) {
        this.booking = booking;
    }

    public boolean pay_invoice() {
        if (this.paid) {
            return false;
        }

        this.paid = true;
        if (this.booking != null) {
            this.booking.setBooking_status(BookingStatus.confirmed);
        }
        return true;
    }
}