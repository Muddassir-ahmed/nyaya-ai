from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.authority import Authority
from app.models.jurisdiction import Jurisdiction
from app.schemas.authority import AuthorityRecord


class AuthorityService:
    """
    Deterministic lookup service for verified government authorities.

    Authorities are never invented by the LLM.

    Lookup hierarchy follows the jurisdiction tree:

        district
          ↓
        state
          ↓
        India

    The first jurisdiction level containing verified, active
    authorities for the requested service is returned.
    """

    @staticmethod
    async def _resolve_jurisdiction(
        db: AsyncSession,
        jurisdiction: str,
    ) -> Jurisdiction | None:
        """
        Resolve an active jurisdiction by code first, then name.

        Examples:
            AS     -> Assam
            Assam  -> Assam
        """

        value = jurisdiction.strip().lower()

        if not value:
            return None

        # Prefer exact jurisdiction code.
        code_statement = (
            select(Jurisdiction)
            .where(
                Jurisdiction.is_active.is_(True),
                func.lower(Jurisdiction.code) == value,
            )
            .limit(1)
        )

        code_result = await db.execute(code_statement)
        resolved = code_result.scalar_one_or_none()

        if resolved is not None:
            return resolved

        # Fall back to jurisdiction name.
        name_statement = (
            select(Jurisdiction)
            .where(
                Jurisdiction.is_active.is_(True),
                func.lower(Jurisdiction.name) == value,
            )
            .limit(1)
        )

        name_result = await db.execute(name_statement)

        return name_result.scalar_one_or_none()

    @staticmethod
    async def _get_parent_jurisdiction(
        db: AsyncSession,
        jurisdiction: Jurisdiction,
    ) -> Jurisdiction | None:
        """
        Return the active parent jurisdiction, if one exists.
        """

        if jurisdiction.parent_id is None:
            return None

        statement = (
            select(Jurisdiction)
            .where(
                Jurisdiction.id == jurisdiction.parent_id,
                Jurisdiction.is_active.is_(True),
            )
            .limit(1)
        )

        result = await db.execute(statement)

        return result.scalar_one_or_none()

    @staticmethod
    async def _get_authorities_for_jurisdiction(
        db: AsyncSession,
        service_key: str,
        jurisdiction_id: int,
    ) -> list[tuple[Authority, Jurisdiction]]:
        """
        Retrieve verified and active authorities for one service
        and one jurisdiction.
        """

        statement = (
            select(
                Authority,
                Jurisdiction,
            )
            .join(
                Jurisdiction,
                Authority.jurisdiction_id
                == Jurisdiction.id,
            )
            .where(
                Authority.service_key == service_key,
                Authority.jurisdiction_id
                == jurisdiction_id,
                Authority.is_verified.is_(True),
                Authority.is_active.is_(True),
                Jurisdiction.is_active.is_(True),
            )
            .order_by(
                Authority.priority.asc(),
                Authority.name.asc(),
            )
        )

        result = await db.execute(statement)

        return list(result.all())

    @staticmethod
    def _to_schema(
        authority: Authority,
        jurisdiction: Jurisdiction,
    ) -> AuthorityRecord:
        """
        Convert database authority data into the public
        structured authority schema.
        """

        return AuthorityRecord(
            id=authority.id,
            name=authority.name,
            authority_type=authority.authority_type,
            domain=authority.domain,
            service_key=authority.service_key,
            service_name=authority.service_name,
            description=authority.description,
            jurisdiction_id=jurisdiction.id,
            jurisdiction_name=jurisdiction.name,
            jurisdiction_code=jurisdiction.code,
            official_portal_url=(
                authority.official_portal_url
            ),
            complaint_url=authority.complaint_url,
            phone_number=authority.phone_number,
            email=authority.email,
            primary_source_name=(
                authority.primary_source_name
            ),
            primary_source_url=(
                authority.primary_source_url
            ),
            secondary_source_name=(
                authority.secondary_source_name
            ),
            secondary_source_url=(
                authority.secondary_source_url
            ),
            is_verified=authority.is_verified,
            verified_at=authority.verified_at,
            verification_notes=(
                authority.verification_notes
            ),
            is_active=authority.is_active,
        )

    @staticmethod
    async def get_verified_authorities(
        db: AsyncSession,
        service_key: str,
        jurisdiction: str,
    ) -> list[AuthorityRecord]:
        """
        Find verified authorities using jurisdiction fallback.

        Example:

            Assam
              ↓
            India

        If Assam has a matching verified authority, that level
        is returned.

        Otherwise the service checks Assam's parent jurisdiction.

        The LLM is never used for authority names, URLs,
        telephone numbers, email addresses, or complaint portals.
        """

        service_key = service_key.strip()

        if not service_key:
            return []

        current_jurisdiction = (
            await AuthorityService._resolve_jurisdiction(
                db=db,
                jurisdiction=jurisdiction,
            )
        )

        if current_jurisdiction is None:
            return []

        visited_ids: set[int] = set()

        while current_jurisdiction is not None:
            # Protect against malformed jurisdiction cycles.
            if current_jurisdiction.id in visited_ids:
                break

            visited_ids.add(current_jurisdiction.id)

            matches = (
                await AuthorityService
                ._get_authorities_for_jurisdiction(
                    db=db,
                    service_key=service_key,
                    jurisdiction_id=current_jurisdiction.id,
                )
            )

            if matches:
                return [
                    AuthorityService._to_schema(
                        authority=authority,
                        jurisdiction=jurisdiction_obj,
                    )
                    for authority, jurisdiction_obj
                    in matches
                ]

            current_jurisdiction = (
                await AuthorityService._get_parent_jurisdiction(
                    db=db,
                    jurisdiction=current_jurisdiction,
                )
            )

        return []