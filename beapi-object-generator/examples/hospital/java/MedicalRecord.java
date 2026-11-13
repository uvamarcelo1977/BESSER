import java.time.LocalDate;
import java.util.List;
import java.util.ArrayList;

public class MedicalRecord {
    private String diagnosis;
    private String recordId;
    private LocalDate createdDate;
    private String prescription;
    private MedicalAppointment appointment;

    public MedicalRecord (String diagnosis, String recordId, LocalDate createdDate, String prescription) {
        this.diagnosis = diagnosis;
        this.recordId = recordId;
        this.createdDate = createdDate;
        this.prescription = prescription;
    }



    public String getDiagnosis() {
        return this.diagnosis;
    }

    public void setDiagnosis(String diagnosis) {
        this.diagnosis = diagnosis;
    }

    public String getRecordId() {
        return this.recordId;
    }

    public void setRecordId(String recordId) {
        this.recordId = recordId;
    }

    public LocalDate getCreatedDate() {
        return this.createdDate;
    }

    public void setCreatedDate(LocalDate createdDate) {
        this.createdDate = createdDate;
    }

    public String getPrescription() {
        return this.prescription;
    }

    public void setPrescription(String prescription) {
        this.prescription = prescription;
    }

    public MedicalAppointment getAppointment() {
        return this.appointment;
    }

    public void setAppointment(MedicalAppointment appointment) {
        this.appointment = appointment;
    }
}