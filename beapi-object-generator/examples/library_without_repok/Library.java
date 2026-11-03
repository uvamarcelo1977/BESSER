// This is a template example to list the name of the classes
import java.util.List;
import java.util.ArrayList;
import besser.trace.*;

@BClass(id = "7608dad3-0eb5-5dcd-b2b9-35eb46157627", name = "Library", model = "Library_with_OCL")
public class Library {
    private String telephone;
    private String name;
    private String address;
    private String web_page;

    public Library (String telephone, String name, String address, String web_page) {
        this.telephone = telephone;
        this.name = name;
        this.address = address;
        this.web_page = web_page;
    }



    @BAttribute(id = "2c5394c9-952d-50e0-a9ad-302d219b858e", name = "telephone", type = "str")
    public String getTelephone() {
        return this.telephone;
    }

    public void setTelephone(String telephone) {
        this.telephone = telephone;
    }

    @BAttribute(id = "906858f9-6141-544c-8984-47429dc7ea23", name = "name", type = "str")
    public String getName() {
        return this.name;
    }

    public void setName(String name) {
        this.name = name;
    }

    @BAttribute(id = "e9582813-5414-5a79-bbf4-489fbf2b2f53", name = "address", type = "str")
    public String getAddress() {
        return this.address;
    }

    public void setAddress(String address) {
        this.address = address;
    }

    @BAttribute(id = "d5a75ea7-6d7c-5e86-a1a7-014b56ffeccd", name = "web_page", type = "str")
    public String getWeb_page() {
        return this.web_page;
    }

    public void setWeb_page(String web_page) {
        this.web_page = web_page;
    }
}