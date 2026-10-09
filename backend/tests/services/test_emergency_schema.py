from app.schemas.emergency import (
    EmergencyContact,
    EmergencyResponse,
    EmergencyType,
)


def test_emergency_contact_schema():
    contact = EmergencyContact(
    name="Police Emergency",
    emergency_type=EmergencyType.POLICE,
    phone_number="TEST_NUMBER",
    jurisdiction="India",
    primary_source_name="Test Source",
    primary_source_url="https://example.com",
    is_verified=True,
)

    assert contact.name == "Police Emergency"
    assert contact.emergency_type == EmergencyType.POLICE
    assert contact.is_verified is True


def test_emergency_response_schema():
    response = EmergencyResponse(
        is_emergency=True,
        emergency_type=EmergencyType.MEDICAL,
        immediate_actions=[
            "Move to a safe location.",
            "Seek immediate medical assistance.",
        ],
        safety_warning="This is emergency information.",
        verification_note="Contact information must come from a verified source.",
    )

    assert response.is_emergency is True
    assert response.emergency_type == EmergencyType.MEDICAL
    assert len(response.immediate_actions) == 2


def test_emergency_type_values():
    assert EmergencyType.POLICE.value == "police"
    assert EmergencyType.FIRE.value == "fire"
    assert EmergencyType.MEDICAL.value == "medical"