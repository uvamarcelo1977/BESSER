import java.util.List;
import java.util.ArrayList;

public class Professor {
    private String department;
    private String fullName;
    private String professorId;
    private List<Subject> subjectsTaught;

    public Professor (String department, String fullName, String professorId) {
        this.department = department;
        this.fullName = fullName;
        this.professorId = professorId;
        this.subjectsTaught = new ArrayList<>();
    }

    public Professor (String department, String fullName, String professorId, List<Subject> subjectsTaught) {
        this.department = department;
        this.fullName = fullName;
        this.professorId = professorId;
        this.subjectsTaught = subjectsTaught;
    }

    public String getDepartment() {
        return this.department;
    }

    public void setDepartment(String department) {
        this.department = department;
    }

    public String getFullName() {
        return this.fullName;
    }

    public void setFullName(String fullName) {
        this.fullName = fullName;
    }

    public String getProfessorId() {
        return this.professorId;
    }

    public void setProfessorId(String professorId) {
        this.professorId = professorId;
    }

    public List<Subject> getSubjectsTaught() {
        return this.subjectsTaught;
    }

    public void addSubject(Subject subject) {
        this.subjectsTaught.add(subject);
    }
}