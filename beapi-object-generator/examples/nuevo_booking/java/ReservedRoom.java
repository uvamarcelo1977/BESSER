import java.util.List;
import java.util.ArrayList;

public class ReservedRoom {
    private float agreed_price;
    private float additional_charges;

    public ReservedRoom (float agreed_price, float additional_charges) {
        this.agreed_price = agreed_price;
        this.additional_charges = additional_charges;
    }



    public float getAgreed_price() {
        return this.agreed_price;
    }

    public void setAgreed_price(float agreed_price) {
        this.agreed_price = agreed_price;
    }

    public float getAdditional_charges() {
        return this.additional_charges;
    }

    public void setAdditional_charges(float additional_charges) {
        this.additional_charges = additional_charges;
    }
}