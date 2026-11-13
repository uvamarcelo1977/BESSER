import java.util.List;
import java.util.ArrayList;

public class Subject {
    private String subjectId;
    private String name;
    private int credits;
    private List<Student> students;
    private Professor teacher;
    private List<InfoExam> exams;

    public Subject (String subjectId, String name, int credits) {
        this.subjectId = subjectId;
        this.name = name;
        this.credits = credits;
        this.students = new ArrayList<>();
        this.exams = new ArrayList<>();
    }

    public Subject (String subjectId, String name, int credits, List<Student> students, List<InfoExam> exams) {
        this.subjectId = subjectId;
        this.name = name;
        this.credits = credits;
        this.students = students;
        this.exams = exams;
    }

    public String getSubjectId() {
        return this.subjectId;
    }

    public void setSubjectId(String subjectId) {
        this.subjectId = subjectId;
    }

    public String getName() {
        return this.name;
    }

    public void setName(String name) {
        this.name = name;
    }

    public int getCredits() {
        return this.credits;
    }

    public void setCredits(int credits) {
        this.credits = credits;
    }

    public List<Student> getStudents() {
        return this.students;
    }

    public void addStudent(Student student) {
        this.students.add(student);
    }

    public Professor getTeacher() {
        return this.teacher;
    }

    public void setTeacher(Professor teacher) {
        this.teacher = teacher;
    }

    public List<InfoExam> getExams() {
        return this.exams;
    }

    public void addInfoExam(InfoExam infoexam) {
        this.exams.add(infoexam);
    }
}