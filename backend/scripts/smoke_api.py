#!/usr/bin/env python3
"""Quick API smoke tests against the configured Supabase project.

Usage:
  python scripts/smoke_api.py          # read-only checks
  python scripts/smoke_api.py --write  # includes temporary write flow + cleanup
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path

from dotenv import load_dotenv
from fastapi.testclient import TestClient
from supabase import create_client

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run quick backend API smoke checks")
    parser.add_argument(
        "--write",
        action="store_true",
        help="Create temporary auth/profile/job records and verify list/detail endpoints",
    )
    return parser.parse_args()


def run_read_only(client: TestClient) -> None:
    health = client.get("/health")
    jobs = client.get("/v1/jobs")

    if health.status_code != 200:
        raise RuntimeError(f"/health failed ({health.status_code}): {health.text}")
    if jobs.status_code != 200:
        raise RuntimeError(f"/v1/jobs failed ({jobs.status_code}): {jobs.text}")

    print(f"PASS read-only: /health=200, /v1/jobs=200 (count={jobs.json().get('count')})")


def run_write_flow(client: TestClient, admin) -> None:
    stamp = int(time.time())
    email = f"smoke-{stamp}@kazix.local"
    password = "KaziXSmoke#1234"
    phone = "+254" + f"{stamp % 1_000_000_000:09d}"

    user_id = None
    job_id = None

    try:
        user = admin.auth.admin.create_user(
            {
                "email": email,
                "password": password,
                "email_confirm": True,
                "phone": phone,
                "phone_confirm": True,
                "user_metadata": {"full_name": "Smoke Client"},
            }
        )
        user_id = user.user.id

        admin.table("profiles").upsert(
            {
                "id": user_id,
                "role": "client",
                "full_name": "Smoke Client",
                "phone": phone,
                "email": email,
                "county": "Nairobi",
                "area": "Westlands",
                "mpesa_number": phone,
                "preferred_language": "en",
            },
            on_conflict="id",
        ).execute()

        job_result = admin.table("jobs").insert(
            {
                "client_id": user_id,
                "title": "Smoke test plumbing repair",
                "description": "Need urgent sink leak repair and pipe replacement in kitchen area.",
                "trade": "plumber",
                "county": "Nairobi",
                "area": "Westlands",
                "street": "Parklands Road",
                "budget_min": 1000,
                "budget_max": 2500,
                "payment_type": "fixed",
                "urgency": "urgent",
                "materials_provided": False,
                "status": "open",
            }
        ).execute()
        job_id = job_result.data[0]["id"]

        detail = client.get(f"/v1/jobs/{job_id}")
        profile = client.get(f"/v1/profiles/{user_id}")
        listed = client.get("/v1/jobs")

        if detail.status_code != 200:
            raise RuntimeError(f"/v1/jobs/{{id}} failed ({detail.status_code}): {detail.text}")
        if profile.status_code != 200:
            raise RuntimeError(f"/v1/profiles/{{id}} failed ({profile.status_code}): {profile.text}")
        if listed.status_code != 200:
            raise RuntimeError(f"/v1/jobs listing failed ({listed.status_code}): {listed.text}")

        if not any(row.get("id") == job_id for row in listed.json().get("data", [])):
            raise RuntimeError("Inserted job not found in /v1/jobs response")

        print("PASS write-flow: created temp auth/profile/job and verified public endpoints")

    finally:
        if job_id:
            try:
                admin.table("jobs").delete().eq("id", job_id).execute()
            except Exception:
                pass
        if user_id:
            try:
                admin.table("profiles").delete().eq("id", user_id).execute()
            except Exception:
                pass
            try:
                admin.auth.admin.delete_user(user_id)
            except Exception:
                pass


def main() -> int:
    args = parse_args()
    load_dotenv(ROOT / ".env")

    url = os.getenv("SUPABASE_URL")
    service = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

    if not url or not service:
        print("Missing SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY in backend/.env", file=sys.stderr)
        return 1

    from app.main import app

    api = TestClient(app)
    admin = create_client(url, service)

    run_read_only(api)
    if args.write:
        run_write_flow(api, admin)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
