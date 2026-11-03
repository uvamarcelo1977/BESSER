// This is a template example to list the name of the classes
import java.util.List;
import java.util.ArrayList;
import besser.trace.*;

@BClass(id = "e3de832b-9ece-5e2a-821f-43161ad2e121", name = "Subject", model = "Class_Diagram")
public class Subject {
    private int credits;
    private String subjectId;
    private String name;
    private List<InfoExam> infoexams;

    public Subject (int credits, String subjectId, String name) {
        this.credits = credits;
        this.subjectId = subjectId;
        this.name = name;
        this.infoexams = new ArrayList<>();
    }

    public Subject (int credits, String subjectId, String name, ArrayList<InfoExam> infoexams) {
        this.credits = credits;
        this.subjectId = subjectId;
        this.name = name;
        this.infoexams = infoexams;
    }

    @BAttribute(id = "115b4cfd-2b81-5a23-b788-bb23f667039b", name = "credits", type = "int")
    public int getCredits() {
        return this.credits;
    }

    public void setCredits(int credits) {
        this.credits = credits;
    }

    @BAttribute(id = "f319f2e7-725f-5925-857c-3f21ff8cfd98", name = "subjectId", type = "str")
    public String getSubjectid() {
        return this.subjectId;
    }

    public void setSubjectid(String subjectId) {
        this.subjectId = subjectId;
    }

    @BAttribute(id = "87fab655-9a2e-56e0-a51e-f02500821ac7", name = "name", type = "str")
    public String getName() {
        return this.name;
    }

    public void setName(String name) {
        this.name = name;
    }

    @BAssociationEnd(
        id = "7b9cdddd-473f-5093-b11e-f4db7e960230",
        name = "exams",
        type = InfoExam.class,
        lower = 0,
        upper = BTrace.MANY,
        association = "SubjectExams",
        associationId = "ad31bbd9-5669-51b4-92e6-803afda18624",
        opposite = "subject")
    public List<InfoExam> getInfoexams() {
        return this.infoexams;
    }

    public void addInfoExam(InfoExam infoexam) {
        this.infoexams.add(infoexam);
    }
}