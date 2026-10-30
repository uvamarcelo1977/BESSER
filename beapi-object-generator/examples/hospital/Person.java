// This is a template example to list the name of the classes
import java.util.List;
import java.util.ArrayList;
import besser.trace.*;

@BClass(
    id = "6ce73f23-64ec-5779-9479-6bd19356fff1",
    name = "Person",
    model = "Class_Diagram",
    isAbstract = true)
public class Person {
    private String email;
    private String fullName;
    private String phone;
    private String id;

    public Person (String email, String fullName, String phone, String id) {
        this.email = email;
        this.fullName = fullName;
        this.phone = phone;
        this.id = id;
    }



    @BAttribute(id = "53a02317-f688-519f-9acf-b09410bf3047", name = "email", type = "str")
    public String getEmail() {
        return this.email;
    }

    public void setEmail(String email) {
        this.email = email;
    }

    @BAttribute(id = "72624e3c-d6ad-502e-8310-7e87d0c4c7d7", name = "fullName", type = "str")
    public String getFullname() {
        return this.fullName;
    }

    public void setFullname(String fullName) {
        this.fullName = fullName;
    }

    @BAttribute(id = "7201ac25-fc4c-5385-b1aa-f1b675cba40c", name = "phone", type = "str")
    public String getPhone() {
        return this.phone;
    }

    public void setPhone(String phone) {
        this.phone = phone;
    }

    @BAttribute(id = "6c4f2067-b6ee-511e-b40f-b568e901aebc", name = "id", type = "str")
    public String getId() {
        return this.id;
    }

    public void setId(String id) {
        this.id = id;
    }
}