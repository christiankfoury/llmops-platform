import hashlib

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import ApiKey, Application


def hash_api_key(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def resolve_active_api_key(db: Session, api_key_value: str) -> ApiKey | None:
    return db.scalar(
        select(ApiKey).where(
            ApiKey.key_hash == hash_api_key(api_key_value),
            ApiKey.is_active.is_(True),
            ApiKey.revoked_at.is_(None),
        )
    )


def resolve_active_application(db: Session, api_key: ApiKey) -> Application | None:
    application = db.get(Application, api_key.application_id)
    if application is None or not application.is_active:
        return None
    return application
