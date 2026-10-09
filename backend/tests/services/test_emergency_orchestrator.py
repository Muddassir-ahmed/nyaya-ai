import pytest

from app.models.emergency_contact import EmergencyContact
from app.schemas.emergency import EmergencyType
from app.services.emergency_orchestrator import EmergencyOrchestrator


@pytest.mark.asyncio
async def test_non_emergency_query_returns_non_emergency(
    db_session,
):
    orchestrator = EmergencyOrchestrator()

    response = await orchestrator.handle(
        db=db_session,
        query="What is the punishment for theft?",
    )

    assert response.is_emergency is False
    assert response.emergency_type is None
    assert response.contacts == []
    assert response.immediate_actions == []


@pytest.mark.asyncio
async def test_medical_emergency_returns_medical_type(
    db_session,
):
    contact = EmergencyContact(
        name="Test Medical",
        emergency_type="medical",
        phone_number="108",
        jurisdiction="India",
        primary_source_name="Test Source",
        primary_source_url="https://example.com",
        is_verified=True,
        is_active=True,
    )

    db_session.add(contact)
    await db_session.commit()

    orchestrator = EmergencyOrchestrator()

    response = await orchestrator.handle(
        db=db_session,
        query="Someone is unconscious and bleeding",
    )

    assert response.is_emergency is True
    assert response.emergency_type == EmergencyType.MEDICAL
    assert len(response.contacts) == 1
    assert response.contacts[0].phone_number == "108"
    assert response.contacts[0].is_verified is True


@pytest.mark.asyncio
async def test_fire_emergency_returns_fire_type(
    db_session,
):
    contact = EmergencyContact(
        name="Test Fire",
        emergency_type="fire",
        phone_number="101",
        jurisdiction="India",
        primary_source_name="Test Source",
        primary_source_url="https://example.com",
        is_verified=True,
        is_active=True,
    )

    db_session.add(contact)
    await db_session.commit()

    orchestrator = EmergencyOrchestrator()

    response = await orchestrator.handle(
        db=db_session,
        query="There is a fire in the building right now",
    )

    assert response.is_emergency is True
    assert response.emergency_type == EmergencyType.FIRE
    assert len(response.contacts) == 1
    assert response.contacts[0].phone_number == "101"


@pytest.mark.asyncio
async def test_cybercrime_emergency_returns_cybercrime_type(
    db_session,
):
    contact = EmergencyContact(
        name="Test Cybercrime",
        emergency_type="cybercrime",
        phone_number="1930",
        jurisdiction="India",
        primary_source_name="Test Source",
        primary_source_url="https://example.com",
        is_verified=True,
        is_active=True,
    )

    db_session.add(contact)
    await db_session.commit()

    orchestrator = EmergencyOrchestrator()

    response = await orchestrator.handle(
        db=db_session,
        query="Someone hacked my account and I am in immediate danger",
    )

    assert response.is_emergency is True
    assert response.emergency_type == EmergencyType.CYBERCRIME
    assert len(response.contacts) == 1
    assert response.contacts[0].phone_number == "1930"


@pytest.mark.asyncio
async def test_police_emergency_returns_police_type(
    db_session,
):
    contact = EmergencyContact(
        name="Test Police",
        emergency_type="police",
        phone_number="100",
        jurisdiction="India",
        primary_source_name="Test Source",
        primary_source_url="https://example.com",
        is_verified=True,
        is_active=True,
    )

    db_session.add(contact)
    await db_session.commit()

    orchestrator = EmergencyOrchestrator()

    response = await orchestrator.handle(
        db=db_session,
        query="Someone is attacking me right now",
    )

    assert response.is_emergency is True
    assert response.emergency_type == EmergencyType.POLICE
    assert len(response.contacts) == 1
    assert response.contacts[0].phone_number == "100"


@pytest.mark.asyncio
async def test_emergency_without_specialized_contact_uses_112(
    db_session,
):
    fallback = EmergencyContact(
        name="Test 112",
        emergency_type="other",
        phone_number="112",
        jurisdiction="India",
        primary_source_name="Test Source",
        primary_source_url="https://example.com",
        is_verified=True,
        is_active=True,
    )

    db_session.add(fallback)
    await db_session.commit()

    orchestrator = EmergencyOrchestrator()

    response = await orchestrator.handle(
        db=db_session,
        query="I am in immediate danger right now",
    )

    assert response.is_emergency is True
    assert response.emergency_type == EmergencyType.OTHER
    assert len(response.contacts) == 1
    assert response.contacts[0].phone_number == "112"


@pytest.mark.asyncio
async def test_emergency_response_contains_safety_warning(
    db_session,
):
    orchestrator = EmergencyOrchestrator()

    response = await orchestrator.handle(
        db=db_session,
        query="I am being attacked right now",
    )

    assert response.is_emergency is True
    assert response.safety_warning is not None
    assert "immediate danger" in response.safety_warning.lower()


@pytest.mark.asyncio
async def test_emergency_response_contains_verification_note(
    db_session,
):
    orchestrator = EmergencyOrchestrator()

    response = await orchestrator.handle(
        db=db_session,
        query="I am being attacked right now",
    )

    assert response.is_emergency is True
    assert response.verification_note is not None
    assert "verified" in response.verification_note.lower()

@pytest.mark.asyncio
async def test_detected_assam_jurisdiction_uses_assam_medical_contact(
    db_session,
):
    assam_contact = EmergencyContact(
        name="Assam Emergency Ambulance",
        emergency_type="medical",
        phone_number="108",
        jurisdiction="Assam",
        primary_source_name="Test Assam Source",
        primary_source_url="https://example.com/assam",
        is_verified=True,
        is_active=True,
    )

    india_contact = EmergencyContact(
        name="India Patient Transport",
        emergency_type="medical",
        phone_number="102",
        jurisdiction="India",
        primary_source_name="Test India Source",
        primary_source_url="https://example.com/india",
        is_verified=True,
        is_active=True,
    )

    db_session.add_all([assam_contact, india_contact])
    await db_session.commit()

    orchestrator = EmergencyOrchestrator()

    response = await orchestrator.handle(
        db=db_session,
        query="I am in Assam and someone is unconscious",
    )

    assert response.is_emergency is True
    assert response.emergency_type == EmergencyType.MEDICAL
    assert len(response.contacts) == 1

    assert response.contacts[0].phone_number == "108"
    assert response.contacts[0].jurisdiction == "Assam"

@pytest.mark.asyncio
async def test_detected_karnataka_jurisdiction_uses_india_fallback(
    db_session,
):
    india_contact = EmergencyContact(
        name="India Patient Transport",
        emergency_type="medical",
        phone_number="102",
        jurisdiction="India",
        primary_source_name="Test India Source",
        primary_source_url="https://example.com/india",
        is_verified=True,
        is_active=True,
    )

    fallback_112 = EmergencyContact(
        name="India Universal Emergency",
        emergency_type="other",
        phone_number="112",
        jurisdiction="India",
        primary_source_name="Test 112 Source",
        primary_source_url="https://example.com/112",
        is_verified=True,
        is_active=True,
    )

    db_session.add_all([india_contact, fallback_112])
    await db_session.commit()

    orchestrator = EmergencyOrchestrator()

    response = await orchestrator.handle(
        db=db_session,
        query="I am in Karnataka and someone is unconscious",
    )

    assert response.is_emergency is True
    assert response.emergency_type == EmergencyType.MEDICAL
    assert len(response.contacts) == 1

    assert response.contacts[0].phone_number == "102"
    assert response.contacts[0].jurisdiction == "India"

@pytest.mark.asyncio
async def test_explicit_jurisdiction_overrides_detected_jurisdiction(
    db_session,
):
    assam_contact = EmergencyContact(
        name="Assam Emergency Ambulance",
        emergency_type="medical",
        phone_number="108",
        jurisdiction="Assam",
        primary_source_name="Test Assam Source",
        primary_source_url="https://example.com/assam",
        is_verified=True,
        is_active=True,
    )

    india_contact = EmergencyContact(
        name="India Patient Transport",
        emergency_type="medical",
        phone_number="102",
        jurisdiction="India",
        primary_source_name="Test India Source",
        primary_source_url="https://example.com/india",
        is_verified=True,
        is_active=True,
    )

    db_session.add_all([assam_contact, india_contact])
    await db_session.commit()

    orchestrator = EmergencyOrchestrator()

    response = await orchestrator.handle(
        db=db_session,
        query="I am in Assam and someone is unconscious",
        jurisdiction="Karnataka",
    )

    assert response.is_emergency is True
    assert response.emergency_type == EmergencyType.MEDICAL

    assert len(response.contacts) == 1
    assert response.contacts[0].phone_number == "102"
    assert response.contacts[0].jurisdiction == "India"

@pytest.mark.asyncio
async def test_fire_keyword_does_not_match_firewall(
    db_session,
):
    orchestrator = EmergencyOrchestrator()

    response = await orchestrator.handle(
        db=db_session,
        query="This is an emergency and my firewall is down",
    )

    assert response.is_emergency is True
    assert response.emergency_type == EmergencyType.OTHER

@pytest.mark.asyncio
async def test_hack_keyword_does_not_match_hackathon(
    db_session,
):
    orchestrator = EmergencyOrchestrator()

    response = await orchestrator.handle(
        db=db_session,
        query="There is an emergency at a hackathon venue",
    )

    assert response.is_emergency is True
    assert response.emergency_type == EmergencyType.OTHER

@pytest.mark.asyncio
async def test_child_keyword_does_not_match_childhood(
    db_session,
):
    orchestrator = EmergencyOrchestrator()

    response = await orchestrator.handle(
        db=db_session,
        query="This is an emergency involving a childhood document",
    )

    assert response.is_emergency is True
    assert response.emergency_type == EmergencyType.OTHER


def test_fire_actions_exclude_interpersonal_danger_guidance():
    actions = EmergencyOrchestrator._build_immediate_actions(
        EmergencyType.FIRE
    )

    assert not any(
        "confront" in action.lower()
        or "person causing the danger" in action.lower()
        for action in actions
    )
    assert any(
        "leave the affected building" in action.lower()
        for action in actions
    )
    assert any(
        "do not re-enter" in action.lower()
        for action in actions
    )


def test_police_actions_keep_confrontation_warning():
    actions = EmergencyOrchestrator._build_immediate_actions(
        EmergencyType.POLICE
    )

    assert any(
        "avoid confrontation" in action.lower()
        for action in actions
    )


def test_immediate_death_threat_uses_police_emergency_type():
    emergency_type = EmergencyOrchestrator._detect_emergency_type(
        "Someone is threatening to kill me right now "
        "and is standing outside my home."
    )

    assert emergency_type == EmergencyType.POLICE
