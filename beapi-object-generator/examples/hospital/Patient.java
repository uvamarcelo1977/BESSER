// This is a template example to list the name of the classes
import java.time.LocalDate;
import java.util.List;
import java.util.ArrayList;
import besser.trace.*;

@BClass(
    id = "94cf697e-41b6-59ab-af73-66e1bd40ab88",
    name = "Patient",
    model = "Class_Diagram",
    parents = {Person.class})
public class Patient extends Person{
    private BloodType bloodGroup;
    private LocalDate birthDate;
    private String patientId;
    private List<MedicalAppointment> medicalappointments;

    public Patient (BloodType bloodGroup, LocalDate birthDate, String patientId, String email, String fullName, String phone, String id) {
        super(email, fullName, phone, id);
        this.bloodGroup = bloodGroup;
        this.birthDate = birthDate;
        this.patientId = patientId;
        this.medicalappointments = new ArrayList<>();
    }

    public Patient (BloodType bloodGroup, LocalDate birthDate, String patientId, String email, String fullName, String phone, String id, ArrayList<MedicalAppointment> medicalappointments) {
        super(email, fullName, phone, id);
        this.bloodGroup = bloodGroup;
        this.birthDate = birthDate;
        this.patientId = patientId;
        this.medicalappointments = medicalappointments;
    }

    @BAttribute(
        id = "dc52bdfa-1f64-5db6-b21e-0b561bdc0308",
        name = "bloodGroup",
        type = "BloodType")
    public BloodType getBloodgroup() {
        return this.bloodGroup;
    }

    public void setBloodgroup(BloodType bloodGroup) {
        this.bloodGroup = bloodGroup;
    }

    @BAttribute(id = "8d900e6c-8285-5460-9c6f-beccffde0c40", name = "birthDate", type = "date")
    public LocalDate getBirthdate() {
        return this.birthDate;
    }

    public void setBirthdate(LocalDate birthDate) {
        this.birthDate = birthDate;
    }

    @BAttribute(id = "f512b1f4-dc7d-5b0d-84c3-64ba71e77864", name = "patientId", type = "str")
    public String getPatientid() {
        return this.patientId;
    }

    public void setPatientid(String patientId) {
        this.patientId = patientId;
    }

    @BAssociationEnd(
        id = "3f4510f3-8abc-55c1-aef8-91ba428c35ce",
        name = "appointments",
        type = MedicalAppointment.class,
        lower = 0,
        upper = BTrace.MANY,
        association = "PatientAppointments",
        associationId = "a57850b0-7b64-52fc-b1da-2d3c17637af0",
        opposite = "patient")
    public List<MedicalAppointment> getMedicalappointments() {
        return this.medicalappointments;
    }

    public void addMedicalAppointment(MedicalAppointment medicalappointment) {
        this.medicalappointments.add(medicalappointment);
    }
}