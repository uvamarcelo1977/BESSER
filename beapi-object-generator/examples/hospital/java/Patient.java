import java.time.LocalDate;
import java.util.List;
import java.util.ArrayList;

public class Patient extends Person{
    private BloodType bloodGroup;
    private LocalDate birthDate;
    private String patientId;
    private Doctor primaryDoctor;
    private List<MedicalAppointment> appointments;

    public Patient (BloodType bloodGroup, LocalDate birthDate, String patientId, String id, String email, String phone, String fullName) {
        super(id, email, phone, fullName);
        this.bloodGroup = bloodGroup;
        this.birthDate = birthDate;
        this.patientId = patientId;
        this.appointments = new ArrayList<>();
    }

    public Patient (BloodType bloodGroup, LocalDate birthDate, String patientId, String id, String email, String phone, String fullName, List<MedicalAppointment> appointments) {
        super(id, email, phone, fullName);
        this.bloodGroup = bloodGroup;
        this.birthDate = birthDate;
        this.patientId = patientId;
        this.appointments = appointments;
    }

    public BloodType getBloodGroup() {
        return this.bloodGroup;
    }

    public void setBloodGroup(BloodType bloodGroup) {
        this.bloodGroup = bloodGroup;
    }

    public LocalDate getBirthDate() {
        return this.birthDate;
    }

    public void setBirthDate(LocalDate birthDate) {
        this.birthDate = birthDate;
    }

    public String getPatientId() {
        return this.patientId;
    }

    public void setPatientId(String patientId) {
        this.patientId = patientId;
    }

    public Doctor getPrimaryDoctor() {
        return this.primaryDoctor;
    }

    public void setPrimaryDoctor(Doctor primaryDoctor) {
        this.primaryDoctor = primaryDoctor;
    }

    public List<MedicalAppointment> getAppointments() {
        return this.appointments;
    }

    public void addMedicalAppointment(MedicalAppointment medicalappointment) {
        this.appointments.add(medicalappointment);
    }
}