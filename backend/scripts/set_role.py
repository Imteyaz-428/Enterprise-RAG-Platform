#!/usr/bin/env python3
"""
Script to update a user's role in the database.
Usage:
    python backend/scripts/set_role.py <email> <ROLE>
"""

import sys
import os
from pathlib import Path

# Ensure backend root is on sys.path
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from dotenv import load_dotenv
load_dotenv()
if not os.getenv("DATABASE_URL"):
    env_path = backend_dir / ".env"
    if env_path.exists():
        load_dotenv(dotenv_path=env_path)

from database.database import SessionLocal
from models.user import User
from core.enums import UserRole


ROLE_MAP = {
    "super_admin": UserRole.SUPER_ADMIN,
    "superadmin": UserRole.SUPER_ADMIN,
    "platform_admin": UserRole.SUPER_ADMIN,
    "admin": UserRole.ADMIN,
    "manager": UserRole.MANAGER,
    "employee": UserRole.EMPLOYEE,
    "user": UserRole.EMPLOYEE,
}


def parse_role(role_str: str) -> UserRole:
    clean = role_str.strip().lower()
    if clean in ROLE_MAP:
        return ROLE_MAP[clean]
    valid_roles = ", ".join(r.name for r in UserRole)
    raise ValueError(f"Invalid role '{role_str}'. Valid roles: {valid_roles} (or 'user')")


def set_user_role(email: str, role_str: str):
    target_role = parse_role(role_str)

    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == email).first()
        if not user:
            print(f"Error: User with email '{email}' not found.", file=sys.stderr)
            sys.exit(1)

        # Print before state (without passwords)
        role_display = user.role.value if hasattr(user.role, "value") else str(user.role)
        print(f"Before: User(id={user.id}, email='{user.email}', role='{role_display}')")

        # Update role only - NEVER touch password or other fields
        user.role = target_role
        db.commit()
        db.refresh(user)

        # Print after state
        new_role_display = user.role.value if hasattr(user.role, "value") else str(user.role)
        print(f"After:  User(id={user.id}, email='{user.email}', role='{new_role_display}')")

    finally:
        db.close()


def main():
    if len(sys.argv) != 3:
        print("Usage: python backend/scripts/set_role.py <email> <ROLE>", file=sys.stderr)
        sys.exit(1)

    email = sys.argv[1].strip()
    role_str = sys.argv[2].strip()

    try:
        set_user_role(email, role_str)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
