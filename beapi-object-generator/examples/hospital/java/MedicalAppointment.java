import java.time.LocalDate;
import java.util.List;
import java.util.ArrayList;

public class MedicalAppointment {
    private AppointmentStatus status;
    private LocalDate appointmentDate;
    private String reason;
    private String appointmentId;
    private MedicalRecord record;
    private Patient patient;
    private Doctor attendingDoctor;

    public MedicalAppointment (AppointmentStatus status, LocalDate appointmentDate, String reason, String appointmentId) {
        this.status = status;
        this.appointmentDate = appointmentDate;
        this.reason = reason;
        this.appointmentId = appointmentId;
    }



    public AppointmentStatus getStatus() {
        return this.status;
    }

    public void setStatus(AppointmentStatus status) {
        this.status = status;
    }

    public LocalDate getAppointmentDate() {
        return this.appointmentDate;
    }

    public void setAppointmentDate(LocalDate appointmentDate) {
        this.appointmentDate = appointmentDate;
    }

    public String getReason() {
        return this.reason;
    }

    public void setReason(String reason) {
        this.reason = reason;
    }

    public String getAppointmentId() {
        return this.appointmentId;
    }

    public void setAppointmentId(String appointmentId) {
        this.appointmentId = appointmentId;
    }

    public MedicalRecord getRecord() {
        return this.record;
    }

    public void setRecord(MedicalRecord record) {
        this.record = record;
    }

    public Patient getPatient() {
        return this.patient;
    }

    public void setPatient(Patient patient) {
        this.patient = patient;
    }

    public Doctor getAttendingDoctor() {
        return this.attendingDoctor;
    }

    public void setAttendingDoctor(Doctor attendingDoctor) {
        this.attendingDoctor = attendingDoctor;
    }
}