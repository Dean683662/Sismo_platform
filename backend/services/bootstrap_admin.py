"""Create the first administrator from explicitly configured environment values."""

from pydantic import EmailStr, TypeAdapter, ValidationError
from sqlalchemy import select

from backend.core.config import settings
from backend.core.database import SessionLocal
from backend.core.security import hash_password
from backend.database.models import AuditLog, Role, User


def main() -> None:
    if not settings.bootstrap_admin_email or not settings.bootstrap_admin_password:
        raise SystemExit("Set BOOTSTRAP_ADMIN_EMAIL and BOOTSTRAP_ADMIN_PASSWORD before running this command.")
    if len(settings.bootstrap_admin_password) < 12:
        raise SystemExit("BOOTSTRAP_ADMIN_PASSWORD must contain at least 12 characters.")
    try:
        email = str(TypeAdapter(EmailStr).validate_python(settings.bootstrap_admin_email)).lower()
    except ValidationError as error:
        raise SystemExit("BOOTSTRAP_ADMIN_EMAIL is not a valid email address.") from error

    with SessionLocal.begin() as db:
        if db.scalar(select(User.id).where(User.email == email)):
            raise SystemExit("A user with BOOTSTRAP_ADMIN_EMAIL already exists.")
        role = db.get(Role, "administrator")
        if role is None:
            raise SystemExit("Identity tables are missing. Run `alembic upgrade head` first.")
        user = User(
            full_name=settings.bootstrap_admin_name.strip(),
            email=email,
            password_hash=hash_password(settings.bootstrap_admin_password),
            roles=[role],
        )
        db.add(user)
        db.flush()
        db.add(
            AuditLog(
                actor_id=user.id,
                action="admin.bootstrap_created",
                entity_type="user",
                entity_id=str(user.id),
                after_json={"email": email, "roles": ["administrator"]},
            )
        )
    print(f"Administrator created: {email}")


if __name__ == "__main__":
    main()