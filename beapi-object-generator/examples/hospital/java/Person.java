import java.util.List;
import java.util.ArrayList;

public class Person {
    private String id;
    private String email;
    private String phone;
    private String fullName;

    public Person (String id, String email, String phone, String fullName) {
        this.id = id;
        this.email = email;
        this.phone = phone;
        this.fullName = fullName;
    }



    public String getId() {
        return this.id;
    }

    public void setId(String id) {
        this.id = id;
    }

    public String getEmail() {
        return this.email;
    }

    public void setEmail(String email) {
        this.email = email;
    }

    public String getPhone() {
        return this.phone;
    }

    public void setPhone(String phone) {
        this.phone = phone;
    }

    public String getFullName() {
        return this.fullName;
    }

    public void setFullName(String fullName) {
        this.fullName = fullName;
    }
}