import besser.trace.*;

@BEnumeration(
    id = "4585137c-16d8-5621-95f3-c0982103f802",
    name = "AppointmentStatus",
    model = "Class_Diagram")
public enum AppointmentStatus {
    @BLiteral(id = "08f2c5f7-0f03-5ad8-a948-748f669975ac", name = "CANCELLED")
    CANCELLED,
    @BLiteral(id = "73fd9a29-efb4-510f-a071-ad94236fed3d", name = "COMPLETED")
    COMPLETED,
    @BLiteral(id = "facbb2f5-0ec2-5c21-a54f-cb800489cb3f", name = "NO_SHOW")
    NO_SHOW,
    @BLiteral(id = "c8358c51-f7c7-5ef8-a111-4b222af3380a", name = "SCHEDULED")
    SCHEDULED
}