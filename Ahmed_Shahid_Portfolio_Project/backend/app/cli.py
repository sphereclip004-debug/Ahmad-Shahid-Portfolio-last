"""Safe administrative setup commands. No initial password is printed or stored in source."""
from __future__ import annotations
import argparse, getpass, sys
from sqlalchemy.orm import Session
from app.core.database import Base, engine, SessionLocal
from app.core.security import hash_password
from app.models import AdminAccount


def create_admin():
    Base.metadata.create_all(bind=engine)
    db: Session = SessionLocal()
    try:
        username = input("Admin username: ").strip()
        if not username or len(username) > 80 or any(ch.isspace() for ch in username):
            print("Use a username of 1-80 characters without spaces.", file=sys.stderr)
            return 2
        if db.query(AdminAccount).filter_by(username=username).first():
            print("That username already exists.", file=sys.stderr)
            return 2
        password = getpass.getpass("Password (at least 14 characters): ")
        confirm = getpass.getpass("Confirm password: ")
        if len(password) < 14:
            print("Choose a password with at least 14 characters.", file=sys.stderr)
            return 2
        if password != confirm:
            print("Passwords did not match.", file=sys.stderr)
            return 2
        db.add(AdminAccount(username=username, password_hash=hash_password(password), active=True))
        db.commit()
        print("Administrator created. The password was not displayed or written to a file.")
        return 0
    finally:
        db.close()


def reset_admin_password():
    Base.metadata.create_all(bind=engine)
    db: Session = SessionLocal()
    try:
        username = input("Existing admin username: ").strip()
        user = db.query(AdminAccount).filter_by(username=username).first()
        if not user:
            print("No administrator with that username was found.", file=sys.stderr)
            return 2
        password = getpass.getpass("New password (at least 14 characters): ")
        confirm = getpass.getpass("Confirm new password: ")
        if len(password) < 14:
            print("Choose a password with at least 14 characters.", file=sys.stderr)
            return 2
        if password != confirm:
            print("Passwords did not match.", file=sys.stderr)
            return 2
        user.password_hash = hash_password(password)
        user.session_version += 1  # revoke every session created before this reset
        from app.models import AuditEvent
        db.add(AuditEvent(actor_username=username, action="admin.password_reset", entity_type="admin", entity_id=str(user.id), details={"sessions_revoked": True}))
        db.commit()
        print("Administrator password reset. Existing sessions have been invalidated.")
        return 0
    finally:
        db.close()


def main():
    parser = argparse.ArgumentParser(description="Portfolio administration utilities")
    parser.add_argument("command", choices=["create-admin", "reset-password"], help="Command to run")
    args = parser.parse_args()
    if args.command == "create-admin":
        raise SystemExit(create_admin())
    if args.command == "reset-password":
        raise SystemExit(reset_admin_password())

if __name__ == "__main__":
    main()
