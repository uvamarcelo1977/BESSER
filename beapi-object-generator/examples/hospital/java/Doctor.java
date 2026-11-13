import java.util.List;
import java.util.ArrayList;

public class Doctor extends Person{
    private float consultationFee;
    private String medicalLicense;
    private String specialty;
    private List<Patient> patients;
    private List<MedicalAppointment> scheduledAppointments;

    public Doctor (float consultationFee, String medicalLicense, String specialty, String id, String email, String phone, String fullName) {
        super(id, email, phone, fullName);
        this.consultationFee = consultationFee;
        this.medicalLicense = medicalLicense;
        this.specialty = specialty;
        this.patients = new ArrayList<>();
        this.scheduledAppointments = new ArrayList<>();
    }

    public Doctor (float consultationFee, String medicalLicense, String specialty, String id, String email, String phone, String fullName, List<Patient> patients, List<MedicalAppointment> scheduledAppointments) {
        super(id, email, phone, fullName);
        this.consultationFee = consultationFee;
        this.medicalLicense = medicalLicense;
        this.specialty = specialty;
        this.patients = patients;
        this.scheduledAppointments = scheduledAppointments;
    }

    public float getConsultationFee() {
        return this.consultationFee;
    }

    public void setConsultationFee(float consultationFee) {
        this.consultationFee = consultationFee;
    }

    public String getMedicalLicense() {
        return this.medicalLicense;
    }

    public void setMedicalLicense(String medicalLicense) {
        this.medicalLicense = medicalLicense;
    }

    public String getSpecialty() {
        return this.specialty;
    }

    public void setSpecialty(String specialty) {
        this.specialty = specialty;
    }

    public List<Patient> getPatients() {
        return this.patients;
    }

    public void addPatient(Patient patient) {
        this.patients.add(patient);
    }

    public List<MedicalAppointment> getScheduledAppointments() {
        return this.scheduledAppointments;
    }

    public void addMedicalAppointment(MedicalAppointment medicalappointment) {
        this.scheduledAppointments.add(medicalappointment);
    }
}