#!/usr/bin/env python3
"""
Script to manage user roles in the AutoML API.

This script helps create users and assign roles for testing and administration.
"""

import argparse
import sys
import uuid

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Add the src directory to Python path
sys.path.insert(0, "src")

from automlapi.db.models import Role as RoleModel
from automlapi.db.models import User as UserModel


def get_session(database_url: str = "sqlite:///automl_local.db"):
    """Create a database session."""
    engine = create_engine(database_url)
    Session = sessionmaker(bind=engine)
    return Session()


def list_roles(session):
    """List all available roles."""
    roles = session.query(RoleModel).all()
    print("Available roles:")
    for role in roles:
        print(f"  ID: {role.id}, Name: {role.name}")
    return roles


def list_users(session):
    """List all users with their roles."""
    users = session.query(UserModel).all()
    print("Current users:")
    for user in users:
        role_name = "No role"
        if user.role_id:
            role = session.query(RoleModel).filter(RoleModel.id == user.role_id).first()
            if role:
                role_name = role.name
        print(f"  ID: {user.id}, Role: {role_name}")


def create_user(session, role_name: str = None, user_id: str = None):
    """Create a new user with optional role."""
    if not user_id:
        user_id = str(uuid.uuid4())

    role_id = None
    if role_name:
        role = (
            session.query(RoleModel).filter(RoleModel.name == role_name.upper()).first()
        )
        if not role:
            print(f"Error: Role '{role_name}' not found")
            return None
        role_id = role.id

    # Check if user already exists
    existing_user = session.query(UserModel).filter(UserModel.id == user_id).first()
    if existing_user:
        print(f"Error: User with ID '{user_id}' already exists")
        return None

    user = UserModel(id=user_id, role_id=role_id)

    session.add(user)
    session.commit()
    session.refresh(user)

    role_name_display = role_name if role_name else "No role"
    print(f"Created user: ID={user.id}, Role={role_name_display}")
    return user


def update_user_role(session, user_id: str, role_name: str):
    """Update a user's role."""
    user = session.query(UserModel).filter(UserModel.id == user_id).first()
    if not user:
        print(f"Error: User with ID '{user_id}' not found")
        return False

    role = session.query(RoleModel).filter(RoleModel.name == role_name.upper()).first()
    if not role:
        print(f"Error: Role '{role_name}' not found")
        return False

    user.role_id = role.id
    session.commit()

    print(f"Updated user {user_id} to role {role_name}")
    return True


def main():
    parser = argparse.ArgumentParser(description="Manage users and roles in AutoML API")
    parser.add_argument(
        "--db", default="sqlite:///automl_local.db", help="Database URL"
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # List commands
    list_parser = subparsers.add_parser("list", help="List users or roles")
    list_parser.add_argument("type", choices=["users", "roles"], help="What to list")

    # Create user command
    create_parser = subparsers.add_parser("create-user", help="Create a new user")
    create_parser.add_argument("--role", help="Role name (USER, MAINTAINER, ADMIN)")
    create_parser.add_argument("--id", help="User ID (generates UUID if not provided)")

    # Update role command
    update_parser = subparsers.add_parser("update-role", help="Update a user's role")
    update_parser.add_argument("user_id", help="User ID to update")
    update_parser.add_argument("role", help="New role name (USER, MAINTAINER, ADMIN)")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    session = get_session(args.db)

    try:
        if args.command == "list":
            if args.type == "roles":
                list_roles(session)
            elif args.type == "users":
                list_users(session)

        elif args.command == "create-user":
            create_user(session, args.role, args.id)

        elif args.command == "update-role":
            update_user_role(session, args.user_id, args.role)

    finally:
        session.close()


if __name__ == "__main__":
    main()
