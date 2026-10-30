// This is a template example to list the name of the classes
import java.time.LocalDate;
import java.util.List;
import java.util.ArrayList;
import besser.trace.*;

@BClass(id = "8e18e79f-9757-53ab-8ac3-47b24e891abf", name = "Student", model = "Class_Diagram")
public class Student {
    private String email;
    private String studentId;
    private String fullName;
    private LocalDate birthDate;
    private List<Subject> subjects;
    private List<InfoExam> infoexams;

    public Student (String email, String studentId, String fullName, LocalDate birthDate) {
        this.email = email;
        this.studentId = studentId;
        this.fullName = fullName;
        this.birthDate = birthDate;
        this.subjects = new ArrayList<>();
        this.infoexams = new ArrayList<>();
    }

    public Student (String email, String studentId, String fullName, LocalDate birthDate, ArrayList<Subject> subjects, ArrayList<InfoExam> infoexams) {
        this.email = email;
        this.studentId = studentId;
        this.fullName = fullName;
        this.birthDate = birthDate;
        this.subjects = subjects;
        this.infoexams = infoexams;
    }

    @BAttribute(id = "54f1cdaa-3df1-5b30-940c-804a157a8b71", name = "email", type = "str")
    public String getEmail() {
        return this.email;
    }

    public void setEmail(String email) {
        this.email = email;
    }

    @BAttribute(id = "442ea03d-93ba-5245-91ac-f55ca0f40d9b", name = "studentId", type = "str")
    public String getStudentid() {
        return this.studentId;
    }

    public void setStudentid(String studentId) {
        this.studentId = studentId;
    }

    @BAttribute(id = "a3e18b74-619a-5fb5-bb4f-8d2b6c890801", name = "fullName", type = "str")
    public String getFullname() {
        return this.fullName;
    }

    public void setFullname(String fullName) {
        this.fullName = fullName;
    }

    @BAttribute(id = "7ef043f4-5f9c-5557-a0b8-b6bfbf639e53", name = "birthDate", type = "date")
    public LocalDate getBirthdate() {
        return this.birthDate;
    }

    public void setBirthdate(LocalDate birthDate) {
        this.birthDate = birthDate;
    }

    @BAssociationEnd(
        id = "ab13c7aa-bf81-5d17-8ff1-09754e9761e8",
        name = "subjects",
        type = Subject.class,
        upper = BTrace.MANY,
        association = "Enrollment",
        associationId = "29020ae0-41d6-5652-a4b4-0c66a8a235e5",
        opposite = "students")
    public List<Subject> getSubjects() {
        return this.subjects;
    }

    public void addSubject(Subject subject) {
        this.subjects.add(subject);
    }

    @BAssociationEnd(
        id = "a93b7704-5ca3-50c1-93e1-16faf244b57b",
        name = "exams",
        type = InfoExam.class,
        lower = 0,
        upper = BTrace.MANY,
        association = "StudentExams",
        associationId = "69b49287-c42c-5b85-a889-33959ac66b6a",
        opposite = "student")
    public List<InfoExam> getInfoexams() {
        return this.infoexams;
    }

    public void addInfoExam(InfoExam infoexam) {
        this.infoexams.add(infoexam);
    }
}