// This is a template example to list the name of the classes
import java.time.LocalDate;
import java.util.List;
import java.util.ArrayList;
import besser.trace.*;

@BClass(
    id = "464f00c4-66a2-5337-aefd-0b61f4d75800",
    name = "MedicalRecord",
    model = "Class_Diagram")
public class MedicalRecord {
    private LocalDate createdDate;
    private String recordId;
    private String prescription;
    private String diagnosis;
    private MedicalAppointment medicalappointment;

    public MedicalRecord (LocalDate createdDate, String recordId, String prescription, String diagnosis) {
        this.createdDate = createdDate;
        this.recordId = recordId;
        this.prescription = prescription;
        this.diagnosis = diagnosis;
    }



    @BAttribute(id = "f69126cd-b504-5a5f-a7c8-31dc19d64e7c", name = "createdDate", type = "date")
    public LocalDate getCreateddate() {
        return this.createdDate;
    }

    public void setCreateddate(LocalDate createdDate) {
        this.createdDate = createdDate;
    }

    @BAttribute(id = "ca2936f7-8d9a-5c68-afba-f92bf83da073", name = "recordId", type = "str")
    public String getRecordid() {
        return this.recordId;
    }

    public void setRecordid(String recordId) {
        this.recordId = recordId;
    }

    @BAttribute(id = "7521abce-336e-5763-aba4-e13dbcc8eb77", name = "prescription", type = "str")
    public String getPrescription() {
        return this.prescription;
    }

    public void setPrescription(String prescription) {
        this.prescription = prescription;
    }

    @BAttribute(id = "0e60cbe5-c4b5-57f5-9e77-049655257a15", name = "diagnosis", type = "str")
    public String getDiagnosis() {
        return this.diagnosis;
    }

    public void setDiagnosis(String diagnosis) {
        this.diagnosis = diagnosis;
    }

    @BAssociationEnd(
        id = "a2c323c6-ea3a-5a24-a049-e9cf7a8d4779",
        name = "appointment",
        type = MedicalAppointment.class,
        association = "AppointmentRecord",
        associationId = "aa1a203e-c573-5159-a327-72c0616eb1b3",
        opposite = "record")
    public MedicalAppointment getMedicalappointment() {
        return this.medicalappointment;
    }

    public void setMedicalappointment(MedicalAppointment medicalappointment) {
        this.medicalappointment = medicalappointment;
    }
}