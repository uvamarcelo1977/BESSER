####################
# STRUCTURAL MODEL #
####################

from besser.BUML.metamodel.structural import (
    Class, Property, Method, Parameter,
    BinaryAssociation, Generalization, DomainModel,
    Enumeration, EnumerationLiteral, Multiplicity,
    StringType, IntegerType, FloatType, BooleanType,
    TimeType, DateType, DateTimeType, TimeDeltaType,
    AnyType, Constraint, AssociationClass, Metadata, MethodImplementationType
)

# Enumerations
AppointmentStatus: Enumeration = Enumeration(
    name="AppointmentStatus",
    literals={
            EnumerationLiteral(name="CANCELLED"),
			EnumerationLiteral(name="COMPLETED"),
			EnumerationLiteral(name="NO_SHOW"),
			EnumerationLiteral(name="SCHEDULED")
    }
)

BloodType: Enumeration = Enumeration(
    name="BloodType",
    literals={
            EnumerationLiteral(name="AB_NEGATIVE"),
			EnumerationLiteral(name="AB_POSITIVE"),
			EnumerationLiteral(name="A_NEGATIVE"),
			EnumerationLiteral(name="A_POSITIVE"),
			EnumerationLiteral(name="B_NEGATIVE"),
			EnumerationLiteral(name="B_POSITIVE"),
			EnumerationLiteral(name="O_NEGATIVE"),
			EnumerationLiteral(name="O_POSITIVE")
    }
)

# Classes
Doctor = Class(name="Doctor")
Hospital = Class(name="Hospital")
MedicalAppointment = Class(name="MedicalAppointment")
MedicalRecord = Class(name="MedicalRecord")
Patient = Class(name="Patient")
Person = Class(name="Person", is_abstract=True)

# Doctor class attributes and methods
Doctor_consultationFee: Property = Property(name="consultationFee", type=FloatType)
Doctor_medicalLicense: Property = Property(name="medicalLicense", type=StringType)
Doctor_specialty: Property = Property(name="specialty", type=StringType)
Doctor_yearsOfExperience: Property = Property(name="yearsOfExperience", type=IntegerType)
Doctor.attributes={Doctor_consultationFee, Doctor_medicalLicense, Doctor_specialty, Doctor_yearsOfExperience}

# Hospital class attributes and methods
Hospital_address: Property = Property(name="address", type=StringType)
Hospital_capacity: Property = Property(name="capacity", type=IntegerType)
Hospital_name: Property = Property(name="name", type=StringType)
Hospital.attributes={Hospital_address, Hospital_capacity, Hospital_name}

# MedicalAppointment class attributes and methods
MedicalAppointment_appointmentDate: Property = Property(name="appointmentDate", type=DateType)
MedicalAppointment_appointmentId: Property = Property(name="appointmentId", type=StringType)
MedicalAppointment_cost: Property = Property(name="cost", type=FloatType)
MedicalAppointment_durationMinutes: Property = Property(name="durationMinutes", type=IntegerType)
MedicalAppointment_reason: Property = Property(name="reason", type=StringType)
MedicalAppointment_status: Property = Property(name="status", type=AppointmentStatus)
MedicalAppointment.attributes={MedicalAppointment_appointmentDate, MedicalAppointment_appointmentId,
                               MedicalAppointment_cost, MedicalAppointment_durationMinutes,
                               MedicalAppointment_reason, MedicalAppointment_status}

# MedicalRecord class attributes and methods
MedicalRecord_createdDate: Property = Property(name="createdDate", type=DateType)
MedicalRecord_diagnosis: Property = Property(name="diagnosis", type=StringType)
MedicalRecord_prescription: Property = Property(name="prescription", type=StringType)
MedicalRecord_recordId: Property = Property(name="recordId", type=StringType)
MedicalRecord.attributes={MedicalRecord_createdDate, MedicalRecord_diagnosis, MedicalRecord_prescription, MedicalRecord_recordId}

# Patient class attributes and methods
Patient_birthDate: Property = Property(name="birthDate", type=DateType)
Patient_bloodGroup: Property = Property(name="bloodGroup", type=BloodType)
Patient_isInsured: Property = Property(name="isInsured", type=BooleanType)
Patient_patientId: Property = Property(name="patientId", type=StringType)
Patient.attributes={Patient_birthDate, Patient_bloodGroup, Patient_isInsured, Patient_patientId}

# Person class attributes and methods
Person_email: Property = Property(name="email", type=StringType)
Person_fullName: Property = Property(name="fullName", type=StringType)
Person_id: Property = Property(name="id", type=StringType)
Person_phone: Property = Property(name="phone", type=StringType)
Person.attributes={Person_email, Person_fullName, Person_id, Person_phone}

# Relationships
AppointmentRecord: BinaryAssociation = BinaryAssociation(
    name="AppointmentRecord",
    ends={
        Property(name="appointment", type=MedicalAppointment, multiplicity=Multiplicity(1, 1)),
        Property(name="record", type=MedicalRecord, multiplicity=Multiplicity(0, 1))
    }
)
DoctorAppointments: BinaryAssociation = BinaryAssociation(
    name="DoctorAppointments",
    ends={
        Property(name="attendingDoctor", type=Doctor, multiplicity=Multiplicity(1, 1)),
        Property(name="scheduledAppointments", type=MedicalAppointment, multiplicity=Multiplicity(0, 9999))
    }
)
PatientAppointments: BinaryAssociation = BinaryAssociation(
    name="PatientAppointments",
    ends={
        Property(name="appointments", type=MedicalAppointment, multiplicity=Multiplicity(0, 9999)),
        Property(name="patient", type=Patient, multiplicity=Multiplicity(1, 1))
    }
)
Patient_Doctor: BinaryAssociation = BinaryAssociation(
    name="Patient_Doctor",
    ends={
        Property(name="patients", type=Patient, multiplicity=Multiplicity(0, 9999)),
        Property(name="primaryDoctor", type=Doctor, multiplicity=Multiplicity(0, 1))
    }
)
HospitalDoctors: BinaryAssociation = BinaryAssociation(
    name="HospitalDoctors",
    ends={
        Property(name="hospital", type=Hospital, multiplicity=Multiplicity(1, 1)),
        Property(name="doctors", type=Doctor, multiplicity=Multiplicity(1, 9999))
    }
)
HospitalPatients: BinaryAssociation = BinaryAssociation(
    name="HospitalPatients",
    ends={
        Property(name="admittedAt", type=Hospital, multiplicity=Multiplicity(0, 1)),
        Property(name="inpatients", type=Patient, multiplicity=Multiplicity(0, 9999))
    }
)

# Generalizations
gen_Doctor_Person = Generalization(general=Person, specific=Doctor)
gen_Patient_Person = Generalization(general=Person, specific=Patient)


# OCL Constraints

# --- Person ---
Person_inv_uniqueId: Constraint = Constraint(
    name="Person_inv_uniqueId",
    context=Person,
    expression="context Person inv Person_inv_uniqueId : Person::allInstances()->isUnique(id)",
    language="OCL"
)
Person_inv_contact: Constraint = Constraint(
    name="Person_inv_contact",
    context=Person,
    expression="context Person inv Person_inv_contact : self.fullName.size() > 0 and "
               "(self.email <> '' or self.phone <> '')",
    language="OCL"
)
Person_inv_emailLowerCase: Constraint = Constraint(
    name="Person_inv_emailLowerCase",
    context=Person,
    expression="context Person inv Person_inv_emailLowerCase : self.email = self.email.toLower()",
    language="OCL"
)

# --- Doctor ---
Doctor_inv_2_1: Constraint = Constraint(
    name="Doctor_inv_2_1",
    context=Doctor,
    expression="context Doctor inv Doctor_inv_2_1 : self.scheduledAppointments ->size()>2",
    language="OCL"
)
Doctor_inv_licensePrefix: Constraint = Constraint(
    name="Doctor_inv_licensePrefix",
    context=Doctor,
    expression="context Doctor inv Doctor_inv_licensePrefix : self.medicalLicense.size() >= 3 and "
               "self.medicalLicense.substring(1, 3).toUpper() = 'MED'",
    language="OCL"
)
Doctor_inv_experienceRange: Constraint = Constraint(
    name="Doctor_inv_experienceRange",
    context=Doctor,
    expression="context Doctor inv Doctor_inv_experienceRange : self.yearsOfExperience >= 0 and "
               "not (self.yearsOfExperience > 60)",
    language="OCL"
)
Doctor_inv_patientsReferBack: Constraint = Constraint(
    name="Doctor_inv_patientsReferBack",
    context=Doctor,
    expression="context Doctor inv Doctor_inv_patientsReferBack : self.patients->forAll(p | p.primaryDoctor = self)",
    language="OCL"
)
Doctor_inv_averageDuration: Constraint = Constraint(
    name="Doctor_inv_averageDuration",
    context=Doctor,
    expression="context Doctor inv Doctor_inv_averageDuration : not self.scheduledAppointments->isEmpty() implies "
               "self.scheduledAppointments->collect(a | a.durationMinutes)->sum() / "
               "self.scheduledAppointments->size() <= 120",
    language="OCL"
)
Doctor_inv_billingCoversFees: Constraint = Constraint(
    name="Doctor_inv_billingCoversFees",
    context=Doctor,
    expression="context Doctor inv Doctor_inv_billingCoversFees : "
               "self.scheduledAppointments->collect(a | a.cost)->sum() >= "
               "self.consultationFee * self.scheduledAppointments->size()",
    language="OCL"
)

# --- Patient ---
Patient_inv_5_1: Constraint = Constraint(
    name="Patient_inv_5_1",
    context=Patient,
    expression="context Patient inv Patient_inv_5_1 : (self.primaryDoctor<>null) implies (self.id<>self.primaryDoctor.id)",
    language="OCL"
)
Patient_inv_bornInThePast: Constraint = Constraint(
    name="Patient_inv_bornInThePast",
    context=Patient,
    expression="context Patient inv Patient_inv_bornInThePast : self.birthDate <= Date::today()",
    language="OCL"
)
Patient_inv_noDoubleBooking: Constraint = Constraint(
    name="Patient_inv_noDoubleBooking",
    context=Patient,
    expression="context Patient inv Patient_inv_noDoubleBooking : self.appointments->isUnique(appointmentDate)",
    language="OCL"
)
Patient_inv_insuredOrLowCost: Constraint = Constraint(
    name="Patient_inv_insuredOrLowCost",
    context=Patient,
    expression="context Patient inv Patient_inv_insuredOrLowCost : self.isInsured or "
               "self.appointments->collect(a | a.cost)->sum() <= 1000.0",
    language="OCL"
)
Patient_inv_primaryDoctorAttends: Constraint = Constraint(
    name="Patient_inv_primaryDoctorAttends",
    context=Patient,
    expression="context Patient inv Patient_inv_primaryDoctorAttends : self.primaryDoctor <> null implies "
               "self.appointments->exists(a | a.attendingDoctor = self.primaryDoctor)",
    language="OCL"
)
Patient_inv_fewDoctors: Constraint = Constraint(
    name="Patient_inv_fewDoctors",
    context=Patient,
    expression="context Patient inv Patient_inv_fewDoctors : self.appointments.attendingDoctor->asSet()->size() <= 5",
    language="OCL"
)

# --- MedicalAppointment ---
MedicalAppointment_inv_durationRange: Constraint = Constraint(
    name="MedicalAppointment_inv_durationRange",
    context=MedicalAppointment,
    expression="context MedicalAppointment inv MedicalAppointment_inv_durationRange : "
               "self.durationMinutes >= 10 and self.durationMinutes <= 240",
    language="OCL"
)
MedicalAppointment_inv_costCoversFee: Constraint = Constraint(
    name="MedicalAppointment_inv_costCoversFee",
    context=MedicalAppointment,
    expression="context MedicalAppointment inv MedicalAppointment_inv_costCoversFee : "
               "self.cost - self.attendingDoctor.consultationFee >= 0.0",
    language="OCL"
)
MedicalAppointment_inv_participantsArePeople: Constraint = Constraint(
    name="MedicalAppointment_inv_participantsArePeople",
    context=MedicalAppointment,
    expression="context MedicalAppointment inv MedicalAppointment_inv_participantsArePeople : "
               "self.attendingDoctor.oclIsKindOf(Person) and self.patient.oclIsTypeOf(Patient)",
    language="OCL"
)
MedicalAppointment_inv_reasonOrRecord: Constraint = Constraint(
    name="MedicalAppointment_inv_reasonOrRecord",
    context=MedicalAppointment,
    expression="context MedicalAppointment inv MedicalAppointment_inv_reasonOrRecord : "
               "self.reason <> '' or not self.record->isEmpty()",
    language="OCL"
)

# --- MedicalRecord ---
MedicalRecord_inv_1_1: Constraint = Constraint(
    name="MedicalRecord_inv_1_1",
    context=MedicalRecord,
    expression="context MedicalRecord inv MedicalRecord_inv_1_1 : self.createdDate > self.appointment.appointmentDate",
    language="OCL"
)
MedicalRecord_inv_prescriptionNeedsDiagnosis: Constraint = Constraint(
    name="MedicalRecord_inv_prescriptionNeedsDiagnosis",
    context=MedicalRecord,
    expression="context MedicalRecord inv MedicalRecord_inv_prescriptionNeedsDiagnosis : "
               "self.prescription <> '' implies self.diagnosis <> ''",
    language="OCL"
)
MedicalRecord_inv_recordIdFromAppointment: Constraint = Constraint(
    name="MedicalRecord_inv_recordIdFromAppointment",
    context=MedicalRecord,
    expression="context MedicalRecord inv MedicalRecord_inv_recordIdFromAppointment : "
               "self.recordId = 'R-'.concat(self.appointment.appointmentId)",
    language="OCL"
)
MedicalRecord_inv_doctorIsNotPatient: Constraint = Constraint(
    name="MedicalRecord_inv_doctorIsNotPatient",
    context=MedicalRecord,
    expression="context MedicalRecord inv MedicalRecord_inv_doctorIsNotPatient : "
               "self.appointment.attendingDoctor.oclAsType(Person) <> self.appointment.patient.oclAsType(Person)",
    language="OCL"
)

# --- Hospital ---
Hospital_inv_capacity: Constraint = Constraint(
    name="Hospital_inv_capacity",
    context=Hospital,
    expression="context Hospital inv Hospital_inv_capacity : self.capacity > 0 and self.inpatients->size() <= self.capacity",
    language="OCL"
)
Hospital_inv_allDoctorsLicensed: Constraint = Constraint(
    name="Hospital_inv_allDoctorsLicensed",
    context=Hospital,
    expression="context Hospital inv Hospital_inv_allDoctorsLicensed : "
               "self.doctors->reject(d | d.medicalLicense <> '')->isEmpty()",
    language="OCL"
)
Hospital_inv_inpatientsHaveLocalDoctor: Constraint = Constraint(
    name="Hospital_inv_inpatientsHaveLocalDoctor",
    context=Hospital,
    expression="context Hospital inv Hospital_inv_inpatientsHaveLocalDoctor : "
               "self.inpatients->forAll(p | p.primaryDoctor <> null implies self.doctors->includes(p.primaryDoctor))",
    language="OCL"
)
Hospital_inv_seniorDoctor: Constraint = Constraint(
    name="Hospital_inv_seniorDoctor",
    context=Hospital,
    expression="context Hospital inv Hospital_inv_seniorDoctor : self.doctors->exists(d | d.yearsOfExperience >= 10)",
    language="OCL"
)
Hospital_inv_doctorsPatientsAdmitted: Constraint = Constraint(
    name="Hospital_inv_doctorsPatientsAdmitted",
    context=Hospital,
    expression="context Hospital inv Hospital_inv_doctorsPatientsAdmitted : "
               "self.doctors->forAll(d | d.patients->forAll(p | self.inpatients->includes(p)))",
    language="OCL"
)
Hospital_inv_distinctDoctorPatients: Constraint = Constraint(
    name="Hospital_inv_distinctDoctorPatients",
    context=Hospital,
    expression="context Hospital inv Hospital_inv_distinctDoctorPatients : "
               "self.doctors->collect(d | d.patients)->asSet()->size() <= self.inpatients->size()",
    language="OCL"
)
Hospital_inv_feeBySpecialty: Constraint = Constraint(
    name="Hospital_inv_feeBySpecialty",
    context=Hospital,
    expression="context Hospital inv Hospital_inv_feeBySpecialty : "
               "self.doctors->select(d | d.specialty = 'Surgery')->forAll(d | "
               "if d.yearsOfExperience > 20 then d.consultationFee >= 200.0 else d.consultationFee >= 100.0 endif)",
    language="OCL"
)

# Domain Model
domain_model = DomainModel(
    name="Class_Diagram",
    types={Doctor, Hospital, MedicalAppointment, MedicalRecord, Patient, Person, AppointmentStatus, BloodType},
    associations={AppointmentRecord, DoctorAppointments, PatientAppointments, Patient_Doctor,
                  HospitalDoctors, HospitalPatients},
    constraints={
        Person_inv_uniqueId, Person_inv_contact, Person_inv_emailLowerCase,
        Doctor_inv_2_1, Doctor_inv_licensePrefix, Doctor_inv_experienceRange, Doctor_inv_patientsReferBack,
        Doctor_inv_averageDuration, Doctor_inv_billingCoversFees,
        Patient_inv_5_1, Patient_inv_bornInThePast, Patient_inv_noDoubleBooking, Patient_inv_insuredOrLowCost,
        Patient_inv_primaryDoctorAttends, Patient_inv_fewDoctors,
        MedicalAppointment_inv_durationRange, MedicalAppointment_inv_costCoversFee,
        MedicalAppointment_inv_participantsArePeople, MedicalAppointment_inv_reasonOrRecord,
        MedicalRecord_inv_1_1, MedicalRecord_inv_prescriptionNeedsDiagnosis,
        MedicalRecord_inv_recordIdFromAppointment, MedicalRecord_inv_doctorIsNotPatient,
        Hospital_inv_capacity, Hospital_inv_allDoctorsLicensed, Hospital_inv_inpatientsHaveLocalDoctor,
        Hospital_inv_seniorDoctor, Hospital_inv_doctorsPatientsAdmitted, Hospital_inv_distinctDoctorPatients,
        Hospital_inv_feeBySpecialty,
    },
    generalizations={gen_Doctor_Person, gen_Patient_Person},
    metadata=None
)


######################
# PROJECT DEFINITION #
######################

from besser.BUML.metamodel.project import Project
from besser.BUML.metamodel.structural.structural import Metadata

metadata = Metadata(description="Hospital Management System BUML Model (v2, with OCL invariants)")
project = Project(
    name="HospitalManagementSystem_v2",
    models=[domain_model],
    owner="BESSER User",
    metadata=metadata
)
