#!/usr/bin/env python3
"""CLI utility to reset user passwords directly in the MongoDB store.

Useful for Docker image users who cannot edit .env files or access email/SMTP.

Usage:
    # Interactive mode:
    docker exec -it warden-app python reset_password.py

    # Non-interactive mode:
    docker exec -it warden-app python reset_password.py admin "NewAdminPass123"
"""
import getpass
import os
import sys
import argparse
import auth
from store import Store

MONGO_URI = os.getenv("MONGO_URI") or os.getenv("MONGO_URI_BUNDLED") or "mongodb://localhost:27017"
DB_NAME = os.getenv("DB_NAME", "wardeniq")
EMBED_DIM = int(os.getenv("EMBED_DIM", "768"))

store = Store(MONGO_URI, DB_NAME, EMBED_DIM)


def main():
    parser = argparse.ArgumentParser(description="Reset a WardenIQ user password.")
    parser.add_argument("pos_username", nargs="?", help="Username or email (default: admin)")
    parser.add_argument("pos_password", nargs="?", help="New password (optional; prompted interactively if omitted)")
    parser.add_argument("--username", "-u", help="Username or email (default: admin)")
    parser.add_argument("--password", "-p", help="New password")
    args = parser.parse_args()

    target = args.username or args.pos_username or "admin"
    new_password = args.password or args.pos_password

    if not new_password:
        if sys.stdin.isatty():
            print(f"--- WardenIQ Password Reset for '{target}' ---")
            p1 = getpass.getpass("Enter new password: ")
            p2 = getpass.getpass("Confirm new password: ")
            if p1 != p2:
                print("Error: Passwords do not match.")
                sys.exit(1)
            new_password = p1
        else:
            print("Error: New password is required when running non-interactively.")
            print("Usage: python reset_password.py [username] [new_password]")
            sys.exit(1)

    errs = auth.password_policy_errors(new_password)
    if errs:
        print(f"Error: Password does not meet policy requirements ({', '.join(errs)}).")
        sys.exit(1)

    user = store.get_user_by_email(target.lower())
    if not user and (target.lower() == "admin" or target == "admin"):
        user = store.get_user_by_email("admin")

    if not user:
        if target.lower() == "admin" or target == "admin":
            print("Creating local 'admin' user...")
            user = store.create_user("admin", "Admin", "admin")
        else:
            print(f"Error: User '{target}' not found.")
            sys.exit(1)

    store.set_user_password(user["id"], auth.hash_password(new_password))
    store.clear_reset_code(user["id"])
    print(f"Successfully reset password for user '{user.get('email', target)}'.")
    print("All active sessions for this user have been invalidated.")


if __name__ == "__main__":
    main()
