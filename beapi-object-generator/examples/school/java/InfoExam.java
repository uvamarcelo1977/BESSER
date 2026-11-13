import java.time.LocalDate;
import java.util.List;
import java.util.ArrayList;

public class InfoExam {
    private String examId;
    private LocalDate examDate;
    private int grade;
    private Student student;
    private Subject subject;

    public InfoExam (String examId, LocalDate examDate, int grade) {
        this.examId = examId;
        this.examDate = examDate;
        this.grade = grade;
    }



    public String getExamId() {
        return this.examId;
    }

    public void setExamId(String examId) {
        this.examId = examId;
    }

    public LocalDate getExamDate() {
        return this.examDate;
    }

    public void setExamDate(LocalDate examDate) {
        this.examDate = examDate;
    }

    public int getGrade() {
        return this.grade;
    }

    public void setGrade(int grade) {
        this.grade = grade;
    }

    public Student getStudent() {
        return this.student;
    }

    public void setStudent(Student student) {
        this.student = student;
    }

    public Subject getSubject() {
        return this.subject;
    }

    public void setSubject(Subject subject) {
        this.subject = subject;
    }
}