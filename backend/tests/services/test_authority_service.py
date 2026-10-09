import pytest

from app.models.authority import Authority
from app.models.jurisdiction import Jurisdiction
from app.services.authority_service import AuthorityService


async def create_jurisdiction(
    db_session,
    *,
    name: str,
    code: str,
    jurisdiction_type: str,
    parent: Jurisdiction | None = None,
) -> Jurisdiction:
    jurisdiction = Jurisdiction(
        name=name,
        code=code,
        type=jurisdiction_type,
        parent_id=(
            parent.id
            if parent is not None
            else None
        ),
        country_code="IN",
        is_active=True,
    )

    db_session.add(jurisdiction)
    await db_session.flush()

    return jurisdiction


def create_authority(
    *,
    name: str,
    jurisdiction_id: int,
    service_key: str = "police_complaint",
    is_verified: bool = True,
    is_active: bool = True,
    priority: int = 100,
) -> Authority:
    return Authority(
        name=name,
        authority_type="police",
        domain="criminal",
        service_key=service_key,
        service_name="Police complaint",
        description="Test authority.",
        jurisdiction_id=jurisdiction_id,
        official_portal_url=(
            "https://example.com/official"
        ),
        complaint_url=(
            "https://example.com/complaint"
        ),
        phone_number=None,
        email=None,
        primary_source_name="Test Government Source",
        primary_source_url=(
            "https://example.com/source"
        ),
        secondary_source_name=None,
        secondary_source_url=None,
        is_verified=is_verified,
        verified_at=None,
        verification_notes="Test record.",
        is_active=is_active,
        priority=priority,
    )


@pytest.mark.asyncio
async def test_state_authority_preferred_over_parent(
    db_session,
):
    india = await create_jurisdiction(
        db_session,
        name="Test India Authority 1",
        code="T-IN-A1",
        jurisdiction_type="country",
    )

    assam = await create_jurisdiction(
        db_session,
        name="Test Assam Authority 1",
        code="T-AS-A1",
        jurisdiction_type="state",
        parent=india,
    )

    india_authority = create_authority(
        name="Test India Police",
        jurisdiction_id=india.id,
    )

    assam_authority = create_authority(
        name="Test Assam Police",
        jurisdiction_id=assam.id,
    )

    db_session.add_all(
        [
            india_authority,
            assam_authority,
        ]
    )

    await db_session.commit()

    authorities = (
        await AuthorityService.get_verified_authorities(
            db=db_session,
            service_key="police_complaint",
            jurisdiction="T-AS-A1",
        )
    )

    assert len(authorities) == 1
    assert authorities[0].name == "Test Assam Police"

    assert (
        authorities[0].jurisdiction_code
        == "T-AS-A1"
    )


@pytest.mark.asyncio
async def test_authority_falls_back_to_parent_jurisdiction(
    db_session,
):
    india = await create_jurisdiction(
        db_session,
        name="Test India Authority 2",
        code="T-IN-A2",
        jurisdiction_type="country",
    )

    state = await create_jurisdiction(
        db_session,
        name="Test State Authority 2",
        code="T-ST-A2",
        jurisdiction_type="state",
        parent=india,
    )

    india_authority = create_authority(
        name="Test National Police Authority",
        jurisdiction_id=india.id,
    )

    db_session.add(india_authority)
    await db_session.commit()

    authorities = (
        await AuthorityService.get_verified_authorities(
            db=db_session,
            service_key="police_complaint",
            jurisdiction="T-ST-A2",
        )
    )

    assert len(authorities) == 1

    assert (
        authorities[0].name
        == "Test National Police Authority"
    )

    assert (
        authorities[0].jurisdiction_code
        == "T-IN-A2"
    )


@pytest.mark.asyncio
async def test_unverified_and_inactive_authorities_are_ignored(
    db_session,
):
    jurisdiction = await create_jurisdiction(
        db_session,
        name="Test State Authority 3",
        code="T-ST-A3",
        jurisdiction_type="state",
    )

    unverified = create_authority(
        name="Unverified Authority",
        jurisdiction_id=jurisdiction.id,
        is_verified=False,
    )

    inactive = create_authority(
        name="Inactive Authority",
        jurisdiction_id=jurisdiction.id,
        is_active=False,
    )

    valid = create_authority(
        name="Verified Active Authority",
        jurisdiction_id=jurisdiction.id,
    )

    db_session.add_all(
        [
            unverified,
            inactive,
            valid,
        ]
    )

    await db_session.commit()

    authorities = (
        await AuthorityService.get_verified_authorities(
            db=db_session,
            service_key="police_complaint",
            jurisdiction="T-ST-A3",
        )
    )

    assert len(authorities) == 1

    assert (
        authorities[0].name
        == "Verified Active Authority"
    )

    assert authorities[0].is_verified is True
    assert authorities[0].is_active is True


@pytest.mark.asyncio
async def test_authorities_are_ordered_by_priority(
    db_session,
):
    jurisdiction = await create_jurisdiction(
        db_session,
        name="Test State Authority 4",
        code="T-ST-A4",
        jurisdiction_type="state",
    )

    lower_priority = create_authority(
        name="Secondary Authority",
        jurisdiction_id=jurisdiction.id,
        priority=50,
    )

    higher_priority = create_authority(
        name="Primary Authority",
        jurisdiction_id=jurisdiction.id,
        priority=10,
    )

    db_session.add_all(
        [
            lower_priority,
            higher_priority,
        ]
    )

    await db_session.commit()

    authorities = (
        await AuthorityService.get_verified_authorities(
            db=db_session,
            service_key="police_complaint",
            jurisdiction="T-ST-A4",
        )
    )

    assert len(authorities) == 2

    assert authorities[0].name == "Primary Authority"
    assert authorities[1].name == "Secondary Authority"


@pytest.mark.asyncio
async def test_unknown_jurisdiction_returns_empty_result(
    db_session,
):
    authorities = (
        await AuthorityService.get_verified_authorities(
            db=db_session,
            service_key="police_complaint",
            jurisdiction="THIS-DOES-NOT-EXIST",
        )
    )

    assert authorities == []