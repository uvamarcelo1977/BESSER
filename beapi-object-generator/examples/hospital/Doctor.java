// This is a template example to list the name of the classes
import java.util.List;
import java.util.ArrayList;
import besser.trace.*;

@BClass(
    id = "81b824e9-70ba-5580-8a62-d6185f849052",
    name = "Doctor",
    model = "Class_Diagram",
    parents = {Person.class})
public class Doctor extends Person{
    private float consultationFee;
    private String medicalLicense;
    private String specialty;
    private List<MedicalAppointment> medicalappointments;
    private List<Patient> patients;

    public Doctor (float consultationFee, String medicalLicense, String specialty, String email, String fullName, String phone, String id) {
        super(email, fullName, phone, id);
        this.consultationFee = consultationFee;
        this.medicalLicense = medicalLicense;
        this.specialty = specialty;
        this.medicalappointments = new ArrayList<>();
        this.patients = new ArrayList<>();
    }

    public Doctor (float consultationFee, String medicalLicense, String specialty, String email, String fullName, String phone, String id, ArrayList<MedicalAppointment> medicalappointments, ArrayList<Patient> patients) {
        super(email, fullName, phone, id);
        this.consultationFee = consultationFee;
        this.medicalLicense = medicalLicense;
        this.specialty = specialty;
        this.medicalappointments = medicalappointments;
        this.patients = patients;
    }

    @BAttribute(
        id = "9efb8c00-85e8-5617-8c3e-3a293735babe",
        name = "consultationFee",
        type = "float")
    public float getConsultationfee() {
        return this.consultationFee;
    }

    public void setConsultationfee(float consultationFee) {
        this.consultationFee = consultationFee;
    }

    @BAttribute(id = "7ec47ae6-915c-5310-893b-4b42f79b5b0a", name = "medicalLicense", type = "str")
    public String getMedicallicense() {
        return this.medicalLicense;
    }

    public void setMedicallicense(String medicalLicense) {
        this.medicalLicense = medicalLicense;
    }

    @BAttribute(id = "553b4591-909c-5016-bc8d-0a3b2087d75f", name = "specialty", type = "str")
    public String getSpecialty() {
        return this.specialty;
    }

    public void setSpecialty(String specialty) {
        this.specialty = specialty;
    }

    @BAssociationEnd(
        id = "d42faabc-a107-5c3c-898a-97e20baffe3a",
        name = "scheduledAppointments",
        type = MedicalAppointment.class,
        lower = 0,
        upper = BTrace.MANY,
        association = "DoctorAppointments",
        associationId = "8feb02a8-1d8e-5109-a98a-c6c0c217d0b2",
        opposite = "attendingDoctor")
    public List<MedicalAppointment> getMedicalappointments() {
        return this.medicalappointments;
    }

    public void addMedicalAppointment(MedicalAppointment medicalappointment) {
        this.medicalappointments.add(medicalappointment);
    }

    @BAssociationEnd(
        id = "9a0f5da2-e79a-54ad-a8cf-2bdde2fe99bb",
        name = "patients",
        type = Patient.class,
        lower = 0,
        upper = BTrace.MANY,
        association = "Patient_Doctor",
        associationId = "6c6e2b3d-bbdc-500f-a9a4-14d08e1c16af",
        opposite = "primaryDoctor")
    public List<Patient> getPatients() {
        return this.patients;
    }

    public void addPatient(Patient patient) {
        this.patients.add(patient);
    }
}