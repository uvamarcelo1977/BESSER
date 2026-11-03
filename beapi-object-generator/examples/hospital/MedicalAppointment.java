// This is a template example to list the name of the classes
import java.time.LocalDate;
import java.util.List;
import java.util.ArrayList;
import besser.trace.*;

@BClass(
    id = "30e4a527-31f2-51b0-8246-7eaa0950b34f",
    name = "MedicalAppointment",
    model = "Class_Diagram")
public class MedicalAppointment {
    private LocalDate appointmentDate;
    private String reason;
    private AppointmentStatus status;
    private String appointmentId;

    public MedicalAppointment (LocalDate appointmentDate, String reason, AppointmentStatus status, String appointmentId) {
        this.appointmentDate = appointmentDate;
        this.reason = reason;
        this.status = status;
        this.appointmentId = appointmentId;
    }



    @BAttribute(
        id = "ec5f2aea-cc8f-5b43-b0dc-4e2cc4eafdb1",
        name = "appointmentDate",
        type = "date")
    public LocalDate getAppointmentdate() {
        return this.appointmentDate;
    }

    public void setAppointmentdate(LocalDate appointmentDate) {
        this.appointmentDate = appointmentDate;
    }

    @BAttribute(id = "3443599a-1031-53eb-97e5-39b3a5574f33", name = "reason", type = "str")
    public String getReason() {
        return this.reason;
    }

    public void setReason(String reason) {
        this.reason = reason;
    }

    @BAttribute(
        id = "d42ff150-0f2e-57fb-8e05-af7988078d4c",
        name = "status",
        type = "AppointmentStatus")
    public AppointmentStatus getStatus() {
        return this.status;
    }

    public void setStatus(AppointmentStatus status) {
        this.status = status;
    }

    @BAttribute(id = "f4cd7b40-0c51-5f50-8c3d-23108487c131", name = "appointmentId", type = "str")
    public String getAppointmentid() {
        return this.appointmentId;
    }

    public void setAppointmentid(String appointmentId) {
        this.appointmentId = appointmentId;
    }
}