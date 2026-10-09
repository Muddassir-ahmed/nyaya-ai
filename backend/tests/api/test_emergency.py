import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.models.emergency_contact import EmergencyContact


@pytest.mark.asyncio
async def test_emergency_api_detects_police_emergency(
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

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.post(
            "/emergency/analyze",
            json={
                "query": "Someone is attacking me right now",
            },
        )

    assert response.status_code == 200

    data = response.json()

    assert data["is_emergency"] is True
    assert data["emergency_type"] == "police"
    assert len(data["contacts"]) == 1
    assert data["contacts"][0]["phone_number"] == "100"


@pytest.mark.asyncio
async def test_emergency_api_rejects_normal_legal_question(
    db_session,
):
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.post(
            "/emergency/analyze",
            json={
                "query": "What is the punishment for theft?",
            },
        )

    assert response.status_code == 200

    data = response.json()

    assert data["is_emergency"] is False
    assert data["emergency_type"] is None
    assert data["contacts"] == []
    assert data["immediate_actions"] == []


@pytest.mark.asyncio
async def test_emergency_api_returns_verified_medical_contact(
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

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.post(
            "/emergency/analyze",
            json={
                "query": "Someone is unconscious and bleeding",
            },
        )

    assert response.status_code == 200

    data = response.json()

    assert data["is_emergency"] is True
    assert data["emergency_type"] == "medical"
    assert len(data["contacts"]) == 1
    assert data["contacts"][0]["phone_number"] == "108"
    assert data["contacts"][0]["is_verified"] is True


@pytest.mark.asyncio
async def test_emergency_api_returns_112_fallback(
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

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.post(
            "/emergency/analyze",
            json={
                "query": "I am in immediate danger right now",
            },
        )

    assert response.status_code == 200

    data = response.json()

    assert data["is_emergency"] is True
    assert data["emergency_type"] == "other"
    assert len(data["contacts"]) == 1
    assert data["contacts"][0]["phone_number"] == "112"


@pytest.mark.asyncio
async def test_emergency_api_contains_safety_information(
    db_session,
):
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.post(
            "/emergency/analyze",
            json={
                "query": "I am being attacked right now",
            },
        )

    assert response.status_code == 200

    data = response.json()

    assert data["is_emergency"] is True
    assert data["safety_warning"] is not None
    assert data["verification_note"] is not None
    assert "verified" in data["verification_note"].lower()


@pytest.mark.asyncio
async def test_emergency_api_explicit_jurisdiction_overrides_detected_jurisdiction(
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

    db_session.add_all(
        [
            assam_contact,
            india_contact,
        ]
    )
    await db_session.commit()

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.post(
            "/emergency/analyze",
            json={
                "query": "I am in Karnataka and someone is unconscious",
                "jurisdiction": "Assam",
            },
        )

    assert response.status_code == 200

    data = response.json()

    assert data["is_emergency"] is True
    assert data["emergency_type"] == "medical"

    assert len(data["contacts"]) == 1
    assert data["contacts"][0]["phone_number"] == "108"
    assert data["contacts"][0]["jurisdiction"] == "Assam"


@pytest.mark.asyncio
async def test_emergency_api_uses_detected_jurisdiction_when_not_explicit(
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

    db_session.add_all(
        [
            assam_contact,
            india_contact,
        ]
    )
    await db_session.commit()

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.post(
            "/emergency/analyze",
            json={
                "query": "I am in Assam and someone is unconscious",
            },
        )

    assert response.status_code == 200

    data = response.json()

    assert data["is_emergency"] is True
    assert data["emergency_type"] == "medical"

    assert len(data["contacts"]) == 1
    assert data["contacts"][0]["phone_number"] == "108"
    assert data["contacts"][0]["jurisdiction"] == "Assam"


@pytest.mark.asyncio
async def test_emergency_api_rejects_empty_query(
    db_session,
):
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.post(
            "/emergency/analyze",
            json={
                "query": "",
            },
        )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_emergency_api_rejects_missing_query(
    db_session,
):
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.post(
            "/emergency/analyze",
            json={},
        )

    assert response.status_code == 422