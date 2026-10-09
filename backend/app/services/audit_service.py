from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit_log import AuditLog


async def create_audit_log(
    db: AsyncSession,
    action: str,
    user_id: int | None = None,
    resource: str | None = None,
    resource_id: str | None = None,
    ip_address: str | None = None,
    request_id: str | None = None,
    details: str | None = None,
) -> AuditLog:

    audit_log = AuditLog(
        user_id=user_id,
        action=action,
        resource=resource,
        resource_id=resource_id,
        ip_address=ip_address,
        request_id=request_id,
        details=details,
    )

    db.add(audit_log)
    await db.commit()
    await db.refresh(audit_log)

    return audit_log