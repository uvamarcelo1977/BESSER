// This is a template example to list the name of the classes
import java.time.LocalDate;
import java.util.List;
import java.util.ArrayList;
import besser.trace.*;

@BClass(id = "81016b08-b660-5342-80f8-5c90f7397a80", name = "Author", model = "Library_with_OCL")
public class Author {
    private String name;
    private LocalDate birth;

    public Author (String name, LocalDate birth) {
        this.name = name;
        this.birth = birth;
    }



    @BAttribute(id = "2a863be4-18a5-5ee2-aca1-6a9b301f4988", name = "name", type = "str")
    public String getName() {
        return this.name;
    }

    public void setName(String name) {
        this.name = name;
    }

    @BAttribute(id = "9ba34131-ca01-57d5-b51c-a8247287d406", name = "birth", type = "date")
    public LocalDate getBirth() {
        return this.birth;
    }

    public void setBirth(LocalDate birth) {
        this.birth = birth;
    }
}