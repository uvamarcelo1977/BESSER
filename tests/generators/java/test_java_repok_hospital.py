"""Tests for the OCL invariant -> Java ``repOk()`` translation.

Every invariant of the HospitalManagementSystem_v2 model is checked against the
Java expression generated for it inside ``repOk()``.
"""

import shutil
import subprocess

import pytest

from besser.generators.java_classes import JavaGenerator
from tests.BUML.metamodel.structural.hospital.hospitalManagementSystem_v2 import domain_model


@pytest.fixture(scope="module")
def output_dir(tmp_path_factory):
    path = tmp_path_factory.mktemp("hospital_v2")
    JavaGenerator(model=domain_model, output_dir=str(path)).generate()
    return path


@pytest.fixture(scope="module")
def java_code(output_dir):
    """Generated source of each class, by class name."""
    return {path.stem: path.read_text() for path in output_dir.glob("*.java")}


def test_every_invariant_is_translated(java_code):
    assert not any("Not translated" in code for code in java_code.values())


# --- Person ---

def test_person_unique_id(java_code):
    # Person::allInstances()->isUnique(id)
    assert "static final List<Person> allInstances = new ArrayList<>();" in java_code["Person"]
    assert ("Person.allInstances.stream().map(__unique -> __unique.getId()).distinct().count()"
            " == Person.allInstances.size()" in java_code["Person"])


def test_person_contact(java_code):
    # self.fullName.size() > 0 and (self.email <> '' or self.phone <> '')
    assert ('((this.getFullName().length() > 0) && '
            '(!Objects.equals(this.getEmail(), "") || !Objects.equals(this.getPhone(), "")))'
            in java_code["Person"])


def test_person_email_lower_case(java_code):
    # self.email = self.email.toLower()
    assert "Objects.equals(this.getEmail(), this.getEmail().toLowerCase())" in java_code["Person"]


# --- Doctor ---

def test_doctor_calls_person_repok(java_code):
    assert "@Override" in java_code["Doctor"]
    assert "if (!super.repOk()) {" in java_code["Doctor"]


def test_doctor_more_than_two_appointments(java_code):
    # self.scheduledAppointments ->size()>2
    assert "(this.getScheduledAppointments().size() > 2)" in java_code["Doctor"]


def test_doctor_license_prefix(java_code):
    # self.medicalLicense.size() >= 3 and self.medicalLicense.substring(1, 3).toUpper() = 'MED'
    assert ('((this.getMedicalLicense().length() >= 3) && '
            'Objects.equals(this.getMedicalLicense().substring(1 - 1, 3).toUpperCase(), "MED"))'
            in java_code["Doctor"])


def test_doctor_experience_range(java_code):
    # self.yearsOfExperience >= 0 and not (self.yearsOfExperience > 60)
    assert ("((this.getYearsOfExperience() >= 0) && !((this.getYearsOfExperience() > 60)))"
            in java_code["Doctor"])


def test_doctor_patients_refer_back(java_code):
    # self.patients->forAll(p | p.primaryDoctor = self)
    assert ("this.getPatients().stream().allMatch(p -> Objects.equals(p.getPrimaryDoctor(), this))"
            in java_code["Doctor"])


def test_doctor_average_duration(java_code):
    # not self.scheduledAppointments->isEmpty() implies
    #     self.scheduledAppointments->collect(a | a.durationMinutes)->sum() / self.scheduledAppointments->size() <= 120
    assert ("(!(!(this.getScheduledAppointments().isEmpty())) || "
            "((((double) this.getScheduledAppointments().stream().map(a -> a.getDurationMinutes())"
            ".collect(Collectors.toList()).stream().mapToInt(Integer::intValue).sum()"
            " / this.getScheduledAppointments().size()) <= 120)))" in java_code["Doctor"])


def test_doctor_billing_covers_fees(java_code):
    # self.scheduledAppointments->collect(a | a.cost)->sum() >= self.consultationFee * self.scheduledAppointments->size()
    assert ("(this.getScheduledAppointments().stream().map(a -> a.getCost()).collect(Collectors.toList())"
            ".stream().mapToDouble(Float::doubleValue).sum() >= "
            "(this.getConsultationFee() * this.getScheduledAppointments().size()))" in java_code["Doctor"])


# --- Patient ---

def test_patient_not_own_doctor(java_code):
    # (self.primaryDoctor<>null) implies (self.id<>self.primaryDoctor.id)
    assert ("(!((this.getPrimaryDoctor() != null)) || "
            "(!Objects.equals(this.getId(), this.getPrimaryDoctor().getId())))" in java_code["Patient"])


def test_patient_born_in_the_past(java_code):
    # self.birthDate <= Date::today()
    assert "(this.getBirthDate().compareTo(LocalDate.now()) <= 0)" in java_code["Patient"]


def test_patient_no_double_booking(java_code):
    # self.appointments->isUnique(appointmentDate)
    assert ("this.getAppointments().stream().map(__unique -> __unique.getAppointmentDate()).distinct().count()"
            " == this.getAppointments().size()" in java_code["Patient"])


def test_patient_insured_or_low_cost(java_code):
    # self.isInsured or self.appointments->collect(a | a.cost)->sum() <= 1000.0
    assert ("(this.getIsInsured() || (this.getAppointments().stream().map(a -> a.getCost())"
            ".collect(Collectors.toList()).stream().mapToDouble(Float::doubleValue).sum() <= 1000.0f))"
            in java_code["Patient"])


def test_patient_primary_doctor_attends(java_code):
    # self.primaryDoctor <> null implies self.appointments->exists(a | a.attendingDoctor = self.primaryDoctor)
    assert ("(!((this.getPrimaryDoctor() != null)) || (this.getAppointments().stream()"
            ".anyMatch(a -> Objects.equals(a.getAttendingDoctor(), this.getPrimaryDoctor()))))"
            in java_code["Patient"])


def test_patient_few_doctors(java_code):
    # self.appointments.attendingDoctor->asSet()->size() <= 5
    assert ("this.getAppointments().stream().map(__ocl -> __ocl.getAttendingDoctor()).collect(Collectors.toList())"
            ".stream().distinct().collect(Collectors.toList()).size() <= 5" in java_code["Patient"])


# --- MedicalAppointment ---

def test_appointment_duration_range(java_code):
    # self.durationMinutes >= 10 and self.durationMinutes <= 240
    assert ("((this.getDurationMinutes() >= 10) && (this.getDurationMinutes() <= 240))"
            in java_code["MedicalAppointment"])


def test_appointment_cost_covers_fee(java_code):
    # self.cost - self.attendingDoctor.consultationFee >= 0.0
    assert ("((this.getCost() - this.getAttendingDoctor().getConsultationFee()) >= 0.0f)"
            in java_code["MedicalAppointment"])


def test_appointment_participants_are_people(java_code):
    # self.attendingDoctor.oclIsKindOf(Person) and self.patient.oclIsTypeOf(Patient)
    assert ("((this.getAttendingDoctor() instanceof Person) && "
            "(this.getPatient() != null && this.getPatient().getClass() == Patient.class))"
            in java_code["MedicalAppointment"])


def test_appointment_reason_or_record(java_code):
    # self.reason <> '' or not self.record->isEmpty()
    assert ('(!Objects.equals(this.getReason(), "") || !((this.getRecord() == null)))'
            in java_code["MedicalAppointment"])


# --- MedicalRecord ---

def test_record_created_after_appointment(java_code):
    # self.createdDate > self.appointment.appointmentDate
    assert ("(this.getCreatedDate().compareTo(this.getAppointment().getAppointmentDate()) > 0)"
            in java_code["MedicalRecord"])


def test_record_prescription_needs_diagnosis(java_code):
    # self.prescription <> '' implies self.diagnosis <> ''
    assert ('(!(!Objects.equals(this.getPrescription(), "")) || (!Objects.equals(this.getDiagnosis(), "")))'
            in java_code["MedicalRecord"])


def test_record_id_from_appointment(java_code):
    # self.recordId = 'R-'.concat(self.appointment.appointmentId)
    assert ('Objects.equals(this.getRecordId(), "R-".concat(this.getAppointment().getAppointmentId()))'
            in java_code["MedicalRecord"])


def test_record_doctor_is_not_patient(java_code):
    # self.appointment.attendingDoctor.oclAsType(Person) <> self.appointment.patient.oclAsType(Person)
    assert ("!Objects.equals(((Person) this.getAppointment().getAttendingDoctor()), "
            "((Person) this.getAppointment().getPatient()))" in java_code["MedicalRecord"])


# --- Hospital ---

def test_hospital_capacity(java_code):
    # self.capacity > 0 and self.inpatients->size() <= self.capacity
    assert "((this.getCapacity() > 0) && (this.getInpatients().size() <= this.getCapacity()))" in java_code["Hospital"]


def test_hospital_all_doctors_licensed(java_code):
    # self.doctors->reject(d | d.medicalLicense <> '')->isEmpty()
    assert ('this.getDoctors().stream().filter(d -> !(!Objects.equals(d.getMedicalLicense(), "")))'
            ".collect(Collectors.toList()).isEmpty()" in java_code["Hospital"])


def test_hospital_inpatients_have_local_doctor(java_code):
    # self.inpatients->forAll(p | p.primaryDoctor <> null implies self.doctors->includes(p.primaryDoctor))
    assert ("this.getInpatients().stream().allMatch(p -> (!((p.getPrimaryDoctor() != null)) || "
            "(this.getDoctors().contains(p.getPrimaryDoctor()))))" in java_code["Hospital"])


def test_hospital_senior_doctor(java_code):
    # self.doctors->exists(d | d.yearsOfExperience >= 10)
    assert "this.getDoctors().stream().anyMatch(d -> (d.getYearsOfExperience() >= 10))" in java_code["Hospital"]


def test_hospital_doctors_patients_admitted(java_code):
    # self.doctors->forAll(d | d.patients->forAll(p | self.inpatients->includes(p)))
    assert ("this.getDoctors().stream().allMatch(d -> "
            "d.getPatients().stream().allMatch(p -> this.getInpatients().contains(p)))" in java_code["Hospital"])


def test_hospital_distinct_doctor_patients(java_code):
    # self.doctors->collect(d | d.patients)->asSet()->size() <= self.inpatients->size()
    assert ("this.getDoctors().stream().flatMap(d -> d.getPatients().stream()).collect(Collectors.toList())"
            ".stream().distinct().collect(Collectors.toList()).size() <= this.getInpatients().size()"
            in java_code["Hospital"])


def test_hospital_fee_by_specialty(java_code):
    # self.doctors->select(d | d.specialty = 'Surgery')->forAll(d |
    #     if d.yearsOfExperience > 20 then d.consultationFee >= 200.0 else d.consultationFee >= 100.0 endif)
    assert ('this.getDoctors().stream().filter(d -> Objects.equals(d.getSpecialty(), "Surgery"))'
            ".collect(Collectors.toList()).stream().allMatch(d -> ((d.getYearsOfExperience() > 20) ? "
            "(d.getConsultationFee() >= 200.0f) : (d.getConsultationFee() >= 100.0f)))" in java_code["Hospital"])


# --- Generated code ---

@pytest.mark.skipif(shutil.which("javac") is None, reason="no JDK available")
def test_generated_code_compiles(output_dir):
    sources = [str(path) for path in output_dir.rglob("*.java")]
    result = subprocess.run(["javac", "-d", str(output_dir / "classes"), *sources], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
