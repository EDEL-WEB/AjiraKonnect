"""
Offline sync feature tests.
Usage:
  1. pipenv run python run.py          (in one terminal)
  2. pipenv run python test_offline.py (in another)
"""
import requests
import json
from datetime import datetime, timedelta

BASE = "http://localhost:5000"

# ── helpers ───────────────────────────────────────────────────────────────────

def p(label, r):
    print(f"\n{'─'*55}")
    print(f"[{label}]  HTTP {r.status_code}")
    try:
        print(json.dumps(r.json(), indent=2))
    except Exception:
        print(r.text)

def post(path, data, token=None):
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    return requests.post(f"{BASE}{path}", json=data, headers=headers)

def get(path, token=None, params=None):
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    return requests.get(f"{BASE}{path}", headers=headers, params=params)

def ts(offset_minutes=0):
    return (datetime.utcnow() + timedelta(minutes=offset_minutes)).isoformat()

# ── setup ─────────────────────────────────────────────────────────────────────

def register_and_activate(email, password, full_name, phone, role):
    """Register user and bypass OTP by reading it from the DB directly."""
    r = post("/api/auth/register", {
        "email": email, "password": password,
        "full_name": full_name, "phone": phone, "role": role
    })
    if r.status_code not in (201, 400):
        p(f"Register {role}", r)
        return None

    user_id = r.json().get("user_id")
    if not user_id:
        # already registered — just login
        return None

    # fetch OTP from DB and verify
    import subprocess, re
    result = subprocess.run(
        ["pipenv", "run", "python", "-c",
         f"from app import create_app, db; app = create_app();\n"
         f"ctx = app.app_context(); ctx.push();\n"
         f"from app.models import OTPVerification;\n"
         f"o = OTPVerification.query.filter_by(user_id='{user_id}', is_verified=False).order_by(OTPVerification.expires_at.desc()).first();\n"
         f"print(o.otp_code if o else 'NONE')"
        ],
        capture_output=True, text=True
    )
    otp = result.stdout.strip().splitlines()[-1]
    if otp == "NONE":
        print(f"  [!] No OTP found for {email}")
        return user_id

    r2 = post("/api/auth/verify-otp", {"user_id": user_id, "otp_code": otp})
    p(f"Verify OTP ({role})", r2)
    return user_id

def get_token(email, password):
    r = post("/api/auth/login", {"email": email, "password": password})
    data = r.json()
    if data.get("requires_2fa"):
        print(f"  [!] 2FA triggered for {email} — check server logs for OTP")
        return None
    return data.get("token")

def get_category_id(token):
    r = get("/api/categories", token)
    cats = r.json().get("categories", [])
    if cats:
        return cats[0]["id"]
    # create one if none exist
    r2 = post("/api/categories", {"name": "Plumbing", "description": "Pipe work"}, token)
    return r2.json().get("category_id")

# ── tests ─────────────────────────────────────────────────────────────────────

def test_sync_status(token):
    print("\n\n══ 1. SYNC STATUS ══")
    r = get("/api/sync/status", token)
    p("GET /sync/status", r)
    assert r.status_code == 200
    assert "pending_count" in r.json()

def test_queue_create_job(token, category_id):
    print("\n\n══ 2. QUEUE SINGLE: create_job ══")
    r = post("/api/sync/queue", {
        "device_id": "device-test-001",
        "action_type": "create_job",
        "client_timestamp": ts(-5),
        "payload": {
            "category_id": category_id,
            "title": "Fix leaking pipe",
            "description": "Kitchen sink leaking badly",
            "location": "Nairobi CBD",
            "budget": 2500
        }
    }, token)
    p("POST /sync/queue (create_job)", r)
    assert r.status_code == 201
    assert r.json().get("status") == "queued"
    return r.json()["sync_id"]

def test_queue_invalid_action(token):
    print("\n\n══ 3. QUEUE INVALID action_type ══")
    r = post("/api/sync/queue", {
        "device_id": "device-test-001",
        "action_type": "create_job",   # valid enum
        "client_timestamp": ts(),
        "payload": {}                  # missing required fields — should fail on process
    }, token)
    p("POST /sync/queue (empty payload)", r)
    # queuing itself succeeds; failure happens at process time

def test_batch_sync(token, category_id, job_id=None):
    print("\n\n══ 4. BATCH SYNC ══")
    actions = [
        {
            "device_id": "device-test-001",
            "action_type": "create_job",
            "client_timestamp": ts(-10),
            "payload": {
                "category_id": category_id,
                "title": "Electrical wiring",
                "description": "Install new sockets",
                "location": "Westlands",
                "budget": 4000
            }
        },
        {
            "device_id": "device-test-001",
            "action_type": "create_job",
            "client_timestamp": ts(-8),
            "payload": {
                "category_id": category_id,
                "title": "Paint living room",
                "description": "Two coats needed",
                "location": "Kilimani",
                "budget": 8000
            }
        }
    ]

    # add an update_job action if we have a real job_id
    if job_id:
        actions.append({
            "device_id": "device-test-001",
            "action_type": "update_job",
            "client_timestamp": ts(-2),
            "payload": {"job_id": job_id, "status": "in_progress"}
        })

    r = post("/api/sync/batch", {"actions": actions}, token)
    p("POST /sync/batch", r)
    assert r.status_code == 200
    data = r.json()
    assert "queued" in data and "processed" in data
    print(f"\n  queued={data['queued']}  processed={data['processed']}")
    for res in data.get("results", []):
        status = "✓" if res["success"] else "✗"
        print(f"  {status} {res['id'][:8]}...  {res.get('note', res.get('error', ''))}")

def test_duplicate_prevention(token, category_id):
    print("\n\n══ 5. DUPLICATE PREVENTION ══")
    payload = {
        "device_id": "device-test-001",
        "action_type": "create_job",
        "client_timestamp": ts(-30),   # same timestamp as a past job
        "payload": {
            "category_id": category_id,
            "title": "Fix leaking pipe",  # same title as test 2
            "description": "Kitchen sink leaking badly",
            "location": "Nairobi CBD",
            "budget": 2500
        }
    }
    r = post("/api/sync/batch", {"actions": [payload]}, token)
    p("POST /sync/batch (duplicate)", r)
    results = r.json().get("results", [])
    if results:
        note = results[0].get("note", "")
        print(f"\n  Duplicate handled: {note or '(no note — may have created new)'}")

def test_add_note(token, job_id):
    print("\n\n══ 6. QUEUE: add_note ══")
    r = post("/api/sync/queue", {
        "device_id": "device-test-001",
        "action_type": "add_note",
        "client_timestamp": ts(),
        "payload": {
            "job_id": job_id,
            "note": "Customer confirmed access at 9am"
        }
    }, token)
    p("POST /sync/queue (add_note)", r)

def test_stale_update(token, job_id):
    print("\n\n══ 7. STALE UPDATE (old timestamp) ══")
    r = post("/api/sync/batch", {"actions": [{
        "device_id": "device-test-001",
        "action_type": "update_job",
        "client_timestamp": ts(-120),   # 2 hours ago — older than server state
        "payload": {"job_id": job_id, "status": "cancelled"}
    }]}, token)
    p("POST /sync/batch (stale update)", r)
    results = r.json().get("results", [])
    if results:
        print(f"\n  Stale handled: {results[0].get('note', results[0].get('error', ''))}")

def test_sync_status_after(token):
    print("\n\n══ 8. SYNC STATUS (after processing) ══")
    r = get("/api/sync/status", token)
    p("GET /sync/status", r)
    print(f"\n  Remaining pending: {r.json().get('pending_count')}")

def test_no_auth():
    print("\n\n══ 9. NO AUTH ══")
    r = requests.post(f"{BASE}/api/sync/queue", json={
        "device_id": "x", "action_type": "create_job",
        "client_timestamp": ts(), "payload": {}
    })
    p("POST /sync/queue (no token)", r)
    assert r.status_code == 401, f"Expected 401, got {r.status_code}"
    print("  ✓ Correctly rejected unauthenticated request")

# ── main ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("KaziConnect — Offline Sync Tests")
    print("Make sure server is running: pipenv run python run.py\n")

    # setup customer
    register_and_activate(
        "offline_customer@test.com", "Test1234!",
        "Offline Customer", "+254711000001", "customer"
    )
    token = get_token("offline_customer@test.com", "Test1234!")
    if not token:
        print("\n[!] Could not get token. Is the server running?")
        exit(1)
    print(f"\n✓ Got token: {token[:30]}...")

    # get or create a category (need admin token for create)
    cat_r = get("/api/categories", token)
    cats = cat_r.json().get("categories", [])
    if not cats:
        print("\n[!] No categories found. Create one via admin first:")
        print("    POST /api/categories  {name: 'Plumbing'}")
        exit(1)
    category_id = cats[0]["id"]
    print(f"✓ Using category: {cats[0]['name']} ({category_id[:8]}...)")

    # run tests
    test_no_auth()
    test_sync_status(token)
    sync_id = test_queue_create_job(token, category_id)
    test_queue_invalid_action(token)
    test_batch_sync(token, category_id)
    test_duplicate_prevention(token, category_id)

    # get a real job_id for update/note tests
    jobs_r = get("/api/sync/status", token)  # just to confirm server alive
    # create a job directly to get its ID for note/stale tests
    direct_job = post("/api/jobs", {
        "category_id": category_id,
        "title": "Direct job for sync test",
        "description": "Testing notes and stale updates",
        "location": "Nairobi",
        "budget": 1000
    }, token)
    job_id = direct_job.json().get("job_id")
    if job_id:
        print(f"\n✓ Created direct job: {job_id[:8]}...")
        test_add_note(token, job_id)
        test_stale_update(token, job_id)

    test_sync_status_after(token)

    print("\n\n✓ Offline sync tests complete.")
