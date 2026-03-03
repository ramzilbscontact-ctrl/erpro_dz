#!/usr/bin/env python3
"""
Standalone user management script for Radiance ERP.
Connects directly to MongoDB Atlas — no Django required.

Requirements: pip install pymongo bcrypt

Usage:
    # List all users
    python scripts/manage_users.py list

    # Create a user
    python scripts/manage_users.py create --email admin@example.com --password secret123 --role admin

    # Reset a password
    python scripts/manage_users.py reset-password --email admin@example.com --password newpass123

    # Activate / deactivate
    python scripts/manage_users.py activate --email user@example.com
    python scripts/manage_users.py deactivate --email user@example.com

Environment variable required:
    MONGO_URI=mongodb+srv://user:pass@cluster.mongodb.net/erp_radiance?retryWrites=true&w=majority
    MONGO_DB=erp_radiance  (optional, defaults to erp_radiance)
"""
import argparse
import os
import sys
from datetime import datetime, timezone

try:
    from pymongo import MongoClient
    import bcrypt
except ImportError:
    print("Missing dependencies. Run: pip install pymongo bcrypt")
    sys.exit(1)


ROLE_CHOICES = ('admin', 'manager', 'sales', 'accountant', 'hr', 'viewer')


def get_db():
    uri = os.environ.get('MONGO_URI')
    if not uri:
        print("ERROR: MONGO_URI environment variable is not set.")
        print("  Example: export MONGO_URI='mongodb+srv://user:pass@cluster.mongodb.net/erp_radiance'")
        sys.exit(1)
    db_name = os.environ.get('MONGO_DB', 'erp_radiance')
    client = MongoClient(uri, serverSelectionTimeoutMS=5000)
    # Verify connection
    client.server_info()
    return client[db_name]


def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt()).decode()


def cmd_list(db, _args):
    users = list(db.users.find({}, {'password': 0}))
    if not users:
        print("No users found.")
        return
    print(f"{'EMAIL':<35} {'ROLE':<12} {'ACTIVE':<8} {'ID'}")
    print("-" * 80)
    for u in users:
        print(f"{u.get('email',''):<35} {u.get('role',''):<12} {str(u.get('is_active', True)):<8} {u['_id']}")


def cmd_create(db, args):
    email = args.email.lower().strip()
    if db.users.find_one({'email': email}):
        print(f"ERROR: User '{email}' already exists.")
        sys.exit(1)
    if args.role not in ROLE_CHOICES:
        print(f"ERROR: Invalid role '{args.role}'. Choose from: {', '.join(ROLE_CHOICES)}")
        sys.exit(1)
    now = datetime.now(timezone.utc)
    doc = {
        'email': email,
        'password': hash_password(args.password),
        'role': args.role,
        'first_name': args.first_name or '',
        'last_name': args.last_name or '',
        'is_active': True,
        'is_staff': args.role == 'admin',
        'totp_enabled': False,
        'failed_login_attempts': 0,
        'date_joined': now,
        'created_at': now,
        'updated_at': now,
    }
    result = db.users.insert_one(doc)
    print(f"User created: {email} | role={args.role} | id={result.inserted_id}")


def cmd_reset_password(db, args):
    email = args.email.lower().strip()
    user = db.users.find_one({'email': email})
    if not user:
        print(f"ERROR: User '{email}' not found.")
        sys.exit(1)
    new_hash = hash_password(args.password)
    db.users.update_one({'email': email}, {
        '$set': {'password': new_hash, 'failed_login_attempts': 0, 'updated_at': datetime.now(timezone.utc)}
    })
    print(f"Password reset for: {email}")


def cmd_activate(db, args, active: bool):
    email = args.email.lower().strip()
    result = db.users.update_one({'email': email}, {
        '$set': {'is_active': active, 'updated_at': datetime.now(timezone.utc)}
    })
    if result.matched_count == 0:
        print(f"ERROR: User '{email}' not found.")
        sys.exit(1)
    state = "activated" if active else "deactivated"
    print(f"User {state}: {email}")


def main():
    parser = argparse.ArgumentParser(description='Radiance ERP — User management script')
    sub = parser.add_subparsers(dest='command', required=True)

    # list
    sub.add_parser('list', help='List all users')

    # create
    p_create = sub.add_parser('create', help='Create a new user')
    p_create.add_argument('--email',      required=True)
    p_create.add_argument('--password',   required=True)
    p_create.add_argument('--role',       default='viewer', choices=ROLE_CHOICES)
    p_create.add_argument('--first-name', default='', dest='first_name')
    p_create.add_argument('--last-name',  default='', dest='last_name')

    # reset-password
    p_reset = sub.add_parser('reset-password', help='Reset a user password')
    p_reset.add_argument('--email',    required=True)
    p_reset.add_argument('--password', required=True)

    # activate / deactivate
    p_act = sub.add_parser('activate', help='Activate a user')
    p_act.add_argument('--email', required=True)
    p_deact = sub.add_parser('deactivate', help='Deactivate a user')
    p_deact.add_argument('--email', required=True)

    args = parser.parse_args()

    print(f"Connecting to MongoDB Atlas...")
    try:
        db = get_db()
        print("Connected.\n")
    except Exception as e:
        print(f"ERROR: Cannot connect to MongoDB: {e}")
        sys.exit(1)

    if args.command == 'list':
        cmd_list(db, args)
    elif args.command == 'create':
        cmd_create(db, args)
    elif args.command == 'reset-password':
        cmd_reset_password(db, args)
    elif args.command == 'activate':
        cmd_activate(db, args, True)
    elif args.command == 'deactivate':
        cmd_activate(db, args, False)


if __name__ == '__main__':
    main()
