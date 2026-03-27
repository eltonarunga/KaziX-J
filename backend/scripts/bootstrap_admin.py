#!/usr/bin/env python3
"""Promote an existing profile to admin role.

Usage examples:
  python scripts/bootstrap_admin.py --phone +254712345678
  python scripts/bootstrap_admin.py --email user@example.com
  python scripts/bootstrap_admin.py --user-id 00000000-0000-0000-0000-000000000000
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Allow running this file directly from the backend root.
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.core.supabase import get_admin_client


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Promote a KaziX profile to admin role")
    selector = parser.add_mutually_exclusive_group(required=True)
    selector.add_argument("--user-id", help="Profile UUID")
    selector.add_argument("--email", help="Profile email")
    selector.add_argument("--phone", help="Profile phone in +254XXXXXXXXX format")
    return parser.parse_args()


def find_profile(admin, args: argparse.Namespace) -> dict | None:
    q = admin.table("profiles").select("id, role, full_name, email, phone")

    if args.user_id:
        q = q.eq("id", args.user_id)
    elif args.email:
        q = q.eq("email", args.email)
    else:
        q = q.eq("phone", args.phone)

    result = q.maybe_single().execute()
    return result.data


def main() -> int:
    args = parse_args()
    admin = get_admin_client()

    try:
        profile = find_profile(admin, args)
    except Exception as exc:
        print(f"Failed to query profiles: {exc}", file=sys.stderr)
        return 1

    if not profile:
        print(
            "No matching profile found. Ask the user to complete registration first, then retry.",
            file=sys.stderr,
        )
        return 1

    if profile.get("role") == "admin":
        print(f"Profile {profile['id']} is already an admin.")
        return 0

    updates = {
        "role": "admin",
        "is_verified": True,
        "is_suspended": False,
    }

    try:
        admin.table("profiles").update(updates).eq("id", profile["id"]).execute()
    except Exception as exc:
        print(f"Failed to promote profile to admin: {exc}", file=sys.stderr)
        return 1

    print(
        "Promoted profile to admin:",
        f"id={profile['id']}",
        f"email={profile.get('email') or '-'}",
        f"phone={profile.get('phone') or '-'}",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
