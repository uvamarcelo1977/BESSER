// This is a template example to list the name of the classes
import java.util.List;
import java.util.ArrayList;
import besser.trace.*;

@BClass(id = "7f597361-aeeb-5c76-966b-eeae6538b3a2", name = "Professor", model = "Class_Diagram")
public class Professor {
    private String fullName;
    private String professorId;
    private String department;
    private List<Subject> subjects;

    public Professor (String fullName, String professorId, String department) {
        this.fullName = fullName;
        this.professorId = professorId;
        this.department = department;
        this.subjects = new ArrayList<>();
    }

    public Professor (String fullName, String professorId, String department, ArrayList<Subject> subjects) {
        this.fullName = fullName;
        this.professorId = professorId;
        this.department = department;
        this.subjects = subjects;
    }

    @BAttribute(id = "65e6fbb3-f7a1-574a-9e55-d4423d86ba89", name = "fullName", type = "str")
    public String getFullname() {
        return this.fullName;
    }

    public void setFullname(String fullName) {
        this.fullName = fullName;
    }

    @BAttribute(id = "db7813fa-a8e4-53e8-a944-3a07dc19fc3f", name = "professorId", type = "str")
    public String getProfessorid() {
        return this.professorId;
    }

    public void setProfessorid(String professorId) {
        this.professorId = professorId;
    }

    @BAttribute(id = "51101533-b3f1-5c7c-8220-090119f873f1", name = "department", type = "str")
    public String getDepartment() {
        return this.department;
    }

    public void setDepartment(String department) {
        this.department = department;
    }

    @BAssociationEnd(
        id = "ea31ddad-e854-572e-adb3-9600ee9fb533",
        name = "subjectsTaught",
        type = Subject.class,
        lower = 0,
        upper = BTrace.MANY,
        association = "Teaching",
        associationId = "00d920f3-da03-5fc6-a930-b959cdd5d831",
        opposite = "teacher")
    public List<Subject> getSubjects() {
        return this.subjects;
    }

    public void addSubject(Subject subject) {
        this.subjects.add(subject);
    }
}