// This is a template example to list the name of the classes
import java.time.LocalDate;
import java.util.List;
import java.util.ArrayList;
import besser.trace.*;

@BClass(id = "b3b3f83f-223c-554c-bcc9-0e3c591b26be", name = "InfoExam", model = "Class_Diagram")
public class InfoExam {
    private LocalDate examDate;
    private int grade;
    private String examId;

    public InfoExam (LocalDate examDate, int grade, String examId) {
        this.examDate = examDate;
        this.grade = grade;
        this.examId = examId;
    }



    @BAttribute(id = "3f6d32ee-cf94-59d7-9a26-906796dcc5fe", name = "examDate", type = "date")
    public LocalDate getExamdate() {
        return this.examDate;
    }

    public void setExamdate(LocalDate examDate) {
        this.examDate = examDate;
    }

    @BAttribute(id = "c673f8f4-73b7-5d92-9120-b768eceb7ddb", name = "grade", type = "int")
    public int getGrade() {
        return this.grade;
    }

    public void setGrade(int grade) {
        this.grade = grade;
    }

    @BAttribute(id = "bb63cc61-083a-56a9-8cab-1f3cccffb1ee", name = "examId", type = "str")
    public String getExamid() {
        return this.examId;
    }

    public void setExamid(String examId) {
        this.examId = examId;
    }
}