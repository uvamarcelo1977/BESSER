import java.time.LocalDate;
import java.util.List;
import java.util.ArrayList;

public class Student {
    private String fullName;
    private String studentId;
    private String email;
    private LocalDate birthDate;
    private List<InfoExam> exams;
    private List<Subject> subjects;

    public Student (String fullName, String studentId, String email, LocalDate birthDate) {
        this.fullName = fullName;
        this.studentId = studentId;
        this.email = email;
        this.birthDate = birthDate;
        this.exams = new ArrayList<>();
        this.subjects = new ArrayList<>();
    }

    public Student (String fullName, String studentId, String email, LocalDate birthDate, List<InfoExam> exams, List<Subject> subjects) {
        this.fullName = fullName;
        this.studentId = studentId;
        this.email = email;
        this.birthDate = birthDate;
        this.exams = exams;
        this.subjects = subjects;
    }

    public String getFullName() {
        return this.fullName;
    }

    public void setFullName(String fullName) {
        this.fullName = fullName;
    }

    public String getStudentId() {
        return this.studentId;
    }

    public void setStudentId(String studentId) {
        this.studentId = studentId;
    }

    public String getEmail() {
        return this.email;
    }

    public void setEmail(String email) {
        this.email = email;
    }

    public LocalDate getBirthDate() {
        return this.birthDate;
    }

    public void setBirthDate(LocalDate birthDate) {
        this.birthDate = birthDate;
    }

    public List<InfoExam> getExams() {
        return this.exams;
    }

    public void addInfoExam(InfoExam infoexam) {
        this.exams.add(infoexam);
    }

    public List<Subject> getSubjects() {
        return this.subjects;
    }

    public void addSubject(Subject subject) {
        this.subjects.add(subject);
    }
}