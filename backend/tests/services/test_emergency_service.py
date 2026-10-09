import pytest

from app.models.emergency_contact import EmergencyContact
from app.schemas.emergency import EmergencyType
from app.services.emergency_service import EmergencyService


async def create_contact(
    db_session,
    *,
    name: str,
    emergency_type: str = "police",
    phone_number: str = "TEST_NUMBER",
    jurisdiction: str = "India",
    is_verified: bool = True,
    is_active: bool = True,
    primary_source_name: str = "Test Source",
    primary_source_url: str = "https://example.com",
    secondary_source_name: str | None = None,
    secondary_source_url: str | None = None,
):
    contact = EmergencyContact(
        name=name,
        emergency_type=emergency_type,
        phone_number=phone_number,
        jurisdiction=jurisdiction,
        primary_source_name=primary_source_name,
        primary_source_url=primary_source_url,
        secondary_source_name=secondary_source_name,
        secondary_source_url=secondary_source_url,
        is_verified=is_verified,
        is_active=is_active,
    )

    db_session.add(contact)
    await db_session.commit()

    return contact


@pytest.mark.asyncio
async def test_unverified_contact_is_not_returned(db_session, verified_112):
    await create_contact(
        db_session,
        name="Unverified Police",
        is_verified=False,
    )

    contacts = await EmergencyService.get_verified_contacts(
        db=db_session,
        emergency_type=EmergencyType.POLICE,
        jurisdiction="India",
    )

    assert len(contacts) == 1
    assert contacts[0].phone_number == "112"
    assert contacts[0].is_verified is True


@pytest.mark.asyncio
async def test_inactive_contact_is_not_returned(db_session, verified_112):
    await create_contact(
        db_session,
        name="Inactive Police",
        is_active=False,
    )

    contacts = await EmergencyService.get_verified_contacts(
        db=db_session,
        emergency_type=EmergencyType.POLICE,
        jurisdiction="India",
    )

    assert len(contacts) == 1
    assert contacts[0].phone_number == "112"
    assert contacts[0].is_verified is True


@pytest.mark.asyncio
async def test_wrong_emergency_type_is_not_returned(db_session, verified_112):
    await create_contact(
        db_session,
        name="Fire Service",
        emergency_type="fire",
    )

    contacts = await EmergencyService.get_verified_contacts(
        db=db_session,
        emergency_type=EmergencyType.POLICE,
        jurisdiction="India",
    )

    assert len(contacts) == 1
    assert contacts[0].phone_number == "112"
    assert contacts[0].is_verified is True


@pytest.mark.asyncio
async def test_wrong_jurisdiction_is_not_returned(db_session, verified_112):
    await create_contact(
        db_session,
        name="Assam Police",
        jurisdiction="Assam",
    )

    contacts = await EmergencyService.get_verified_contacts(
        db=db_session,
        emergency_type=EmergencyType.POLICE,
        jurisdiction="India",
    )

    assert len(contacts) == 1
    assert contacts[0].phone_number == "112"
    assert contacts[0].is_verified is True


@pytest.mark.asyncio
async def test_verified_active_matching_contact_is_returned(db_session):
    await create_contact(
        db_session,
        name="Verified Police",
        phone_number="100",
        is_verified=True,
        is_active=True,
    )

    contacts = await EmergencyService.get_verified_contacts(
        db=db_session,
        emergency_type=EmergencyType.POLICE,
        jurisdiction="India",
    )

    assert len(contacts) == 1
    assert contacts[0].name == "Verified Police"
    assert contacts[0].phone_number == "100"
    assert contacts[0].is_verified is True
    assert contacts[0].is_active is True


@pytest.mark.asyncio
async def test_state_specific_contact_is_preferred_over_112(db_session):
    await create_contact(
        db_session,
        name="Assam Medical",
        emergency_type="medical",
        phone_number="108",
        jurisdiction="Assam",
    )

    contacts = await EmergencyService.get_verified_contacts(
        db=db_session,
        emergency_type=EmergencyType.MEDICAL,
        jurisdiction="Assam",
    )

    assert len(contacts) == 1
    assert contacts[0].name == "Assam Medical"
    assert contacts[0].phone_number == "108"


@pytest.mark.asyncio
async def test_state_specific_contact_preferred_over_india_contact(
    db_session,
    verified_112,
):
    await create_contact(
        db_session,
        name="India Patient Transport",
        emergency_type=EmergencyType.MEDICAL.value,
        phone_number="102",
        jurisdiction="India",
        is_verified=True,
        is_active=True,
    )

    await create_contact(
        db_session,
        name="Assam Emergency Ambulance",
        emergency_type=EmergencyType.MEDICAL.value,
        phone_number="108",
        jurisdiction="Assam",
        is_verified=True,
        is_active=True,
    )

    contacts = await EmergencyService.get_verified_contacts(
        db=db_session,
        emergency_type=EmergencyType.MEDICAL,
        jurisdiction="Assam",
    )

    assert len(contacts) == 1
    assert contacts[0].phone_number == "108"
    assert contacts[0].jurisdiction == "Assam"


@pytest.mark.asyncio
async def test_missing_state_specific_contact_uses_india_contact(
    db_session,
):
    await create_contact(
        db_session,
        name="India Patient Transport",
        emergency_type=EmergencyType.MEDICAL.value,
        phone_number="102",
        jurisdiction="India",
        is_verified=True,
        is_active=True,
    )

    contacts = await EmergencyService.get_verified_contacts(
        db=db_session,
        emergency_type=EmergencyType.MEDICAL,
        jurisdiction="Karnataka",
    )

    assert len(contacts) == 1
    assert contacts[0].phone_number == "102"
    assert contacts[0].jurisdiction == "India"
    assert contacts[0].emergency_type == EmergencyType.MEDICAL.value


@pytest.mark.asyncio
async def test_missing_state_and_india_contact_falls_back_to_112(
    db_session,
    verified_112,
):
    contacts = await EmergencyService.get_verified_contacts(
        db=db_session,
        emergency_type=EmergencyType.DISASTER,
        jurisdiction="Karnataka",
    )

    assert len(contacts) == 1
    assert contacts[0].phone_number == "112"
    assert contacts[0].jurisdiction == "India"


@pytest.mark.asyncio
async def test_missing_emergency_type_contact_falls_back_to_112(db_session, verified_112):
    contacts = await EmergencyService.get_verified_contacts(
        db=db_session,
        emergency_type=EmergencyType.FIRE,
        jurisdiction="Assam",
    )

    assert len(contacts) == 1
    assert contacts[0].phone_number == "112"


@pytest.mark.asyncio
async def test_unverified_112_is_not_used_as_fallback(db_session):
    await create_contact(
        db_session,
        name="Unverified 112",
        emergency_type="other",
        phone_number="112",
        jurisdiction="India",
        is_verified=False,
    )

    contacts = await EmergencyService.get_verified_contacts(
        db=db_session,
        emergency_type=EmergencyType.FIRE,
        jurisdiction="Karnataka",
    )

    assert contacts == []


@pytest.mark.asyncio
async def test_inactive_112_is_not_used_as_fallback(db_session):
    await create_contact(
        db_session,
        name="Inactive 112",
        emergency_type="other",
        phone_number="112",
        jurisdiction="India",
        is_active=False,
    )

    contacts = await EmergencyService.get_verified_contacts(
        db=db_session,
        emergency_type=EmergencyType.FIRE,
        jurisdiction="Karnataka",
    )

    assert contacts == []