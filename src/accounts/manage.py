"""User account management CLI.

Usage:
    python -m screenconnect.manage adduser <name>
    python -m screenconnect.manage deluser <name>
    python -m screenconnect.manage passwd  <name>
    python -m screenconnect.manage list
"""
from __future__ import annotations

import argparse
import getpass
import sys
from pathlib import Path

from .store import UserStore

DEFAULT_DB = Path(__file__).parent.parent.parent / "data" / "users.json"


def cmd_adduser(store: UserStore, name: str) -> None:
    pw = getpass.getpass(f"Password for '{name}': ")
    pw2 = getpass.getpass("Confirm password: ")
    if pw != pw2:
        print("Passwords do not match.")
        sys.exit(1)
    user = store.add(name, pw)
    print(f"User '{name}' created (id={user.id})")


def cmd_deluser(store: UserStore, name: str) -> None:
    store.remove(name)
    print(f"User '{name}' removed.")


def cmd_passwd(store: UserStore, name: str) -> None:
    pw = getpass.getpass(f"New password for '{name}': ")
    pw2 = getpass.getpass("Confirm: ")
    if pw != pw2:
        print("Passwords do not match.")
        sys.exit(1)
    store.set_password(name, pw)
    print(f"Password updated for '{name}'.")


def cmd_list(store: UserStore) -> None:
    users = store.list_users()
    if not users:
        print("No users.")
        return
    for u in users:
        print(f"  {u.name:<20} id={u.id}  created={u.created_at}")


def main() -> None:
    parser = argparse.ArgumentParser(description="ScreenConnect user management")
    parser.add_argument("--db", default=str(DEFAULT_DB), help="Path to users.json")
    sub = parser.add_subparsers(dest="command", required=True)

    p_add = sub.add_parser("adduser", help="Add a user")
    p_add.add_argument("name")

    p_del = sub.add_parser("deluser", help="Delete a user")
    p_del.add_argument("name")

    p_pw = sub.add_parser("passwd", help="Change password")
    p_pw.add_argument("name")

    sub.add_parser("list", help="List users")

    args = parser.parse_args()
    store = UserStore(args.db)

    if args.command == "adduser":
        cmd_adduser(store, args.name)
    elif args.command == "deluser":
        cmd_deluser(store, args.name)
    elif args.command == "passwd":
        cmd_passwd(store, args.name)
    elif args.command == "list":
        cmd_list(store)


if __name__ == "__main__":
    main()
