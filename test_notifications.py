#!/usr/bin/env python3
"""
KaziConnect — Notification System Test
Tests: heartbeat, online/offline detection, push vs SMS fallback, WebSocket simulation

Run: pipenv run python test_notifications.py
Server must be running: pipenv run python run.py
"""
import requests
import json
import time
import threading
import socketio  # pip: python-socketio[client]

BASE = "http://localhost:5000"

# ── known credentials (already in DB) ────────────────────────────────────────
ADMIN_EMAIL    = "kaziconnect@26.com"
CUSTOMER_EMAIL = "customer@test.com"
WORKER_EMAIL   = "worker@test.com"
PASSWORD       = "Test1234!"

CATEGORY_ID    = "62294ee3-f0fd-4872-bbac-ef7110ce60a0"   # Plumbing
WORKER_ID      = "c1ea2d40-c8fd-4840-a9ab-95cdb2de40c4"

# ── helpers ───────────────────────────────────────────────────────────────────

def p(label, r):
    print(f"\n{'─'*60}")
    print(f"  {label}  →  HTTP {r.status_code}")
    try:
        print(json.dumps(r.json(), indent=2))
    except Exception:
        print(r.text[:300])

def post(path, data=None, token=None):
    h = {"Authorization": f"Bearer {token}"} if token else {}
    return requests.post(f"{BASE}{path}", json=data or {}, headers=h)

def get(path, token=None):
    h = {"Authorization": f"Bearer {token}"} if token else {}
    return requests.get(f"{BASE}{path}", headers=h)

def login(email):
    r = post("/api/auth/login", {"email": email, "password": PASSWORD})
    token = r.json().get("token")
    if not token:
        print(f"  [!] Login failed for {email}: {r.json()}")
    return token

def section(title):
    print(f"\n\n{'═'*60}")
    print(f"  {title}")
    print(f"{'═'*60}")

# ── setup: give worker a skill + verify them so notifications fire ─────────────

def setup_worker_skill(admin_token):
    """Add Plumbing skill to worker and mark verified so notify_job_created finds them."""
    import subprocess, textwrap
    script = textwrap.dedent(f"""
        from app import create_app, db
        app = create_app()
        with app.app_context():
            from app.models.worker import Worker, WorkerSkill
            w = Worker.query.get('{WORKER_ID}')
            if w:
                w.verification_status = 'verified'
                w.availability = True
                existing = WorkerSkill.query.filter_by(
                    worker_id='{WORKER_ID}', category_id='{CATEGORY_ID}'
                ).first()
                if not existing:
                    skill = WorkerSkill(
                        worker_id='{WORKER_ID}',
                        category_id='{CATEGORY_ID}',
                        experience_years=2
                    )
                    db.session.add(skill)
                db.session.commit()
                print('Worker setup OK')
    """)
    result = subprocess.run(
        ["pipenv", "run", "python", "-c", script],
        capture_output=True, text=True
    )
    print(f"  Worker setup: {result.stdout.strip().splitlines()[-1] if result.stdout.strip() else result.stderr[-100:]}")

# ══════════════════════════════════════════════════════════════════════════════
# TEST 1 — Heartbeat (mark worker ONLINE)
# ══════════════════════════════════════════════════════════════════════════════

def test_heartbeat_online(worker_token):
    section("TEST 1 — Heartbeat → mark worker ONLINE")

    r = post("/api/notifications/heartbeat", {
        "device_id":   "android-device-001",
        "device_type": "android"
    }, worker_token)
    p("POST /api/notifications/heartbeat", r)
    assert r.status_code == 200
    assert r.json()["status"] == "online"
    print("\n  ✓ Worker is now ONLINE")

# ══════════════════════════════════════════════════════════════════════════════
# TEST 2 — Check worker online status
# ══════════════════════════════════════════════════════════════════════════════

def test_check_status_online(customer_token):
    section("TEST 2 — Check worker status (expect: online)")

    r = get(f"/api/notifications/status/{WORKER_ID}", customer_token)
    p(f"GET /api/notifications/status/{WORKER_ID[:8]}...", r)
    assert r.json()["is_online"] == True
    print("\n  ✓ Status correctly reported as ONLINE")

# ══════════════════════════════════════════════════════════════════════════════
# TEST 3 — Book job while worker is ONLINE → expect PUSH notification
# ══════════════════════════════════════════════════════════════════════════════

def test_job_creates_push_notification(customer_token):
    section("TEST 3 — Book job (worker ONLINE) → expect PUSH notification")

    r = post("/api/jobs", {
        "category_id": CATEGORY_ID,
        "title":       "Fix kitchen sink",
        "description": "Pipe leaking under sink",
        "location":    "Nairobi CBD",
        "budget":      2500
    }, customer_token)
    p("POST /api/jobs", r)
    assert r.status_code == 201
    job_id = r.json()["job_id"]
    print(f"\n  Job created: {job_id[:8]}...")

    # check notification was created as 'push'
    import subprocess, textwrap
    script = textwrap.dedent(f"""
        from app import create_app
        app = create_app()
        with app.app_context():
            from app.models import Notification
            n = Notification.query.filter_by(
                user_id=(
                    __import__('app').db.session.execute(
                        __import__('sqlalchemy').text(
                            "SELECT user_id FROM workers WHERE id='{WORKER_ID}'"
                        )
                    ).scalar()
                )
            ).order_by(Notification.created_at.desc()).first()
            if n:
                print(f'type={{n.type}} status={{n.status}} title={{n.title}}')
            else:
                print('No notification found')
    """)
    # simpler direct query
    script2 = textwrap.dedent(f"""
        from app import create_app, db
        app = create_app()
        with app.app_context():
            from app.models import Notification
            from app.models.worker import Worker
            w = Worker.query.get('{WORKER_ID}')
            n = Notification.query.filter_by(user_id=w.user_id).order_by(
                Notification.created_at.desc()
            ).first()
            if n:
                print(f'type={{n.type}} | status={{n.status}} | title={{n.title}}')
            else:
                print('No notification found')
    """)
    result = subprocess.run(
        ["pipenv", "run", "python", "-c", script2],
        capture_output=True, text=True
    )
    output = result.stdout.strip().splitlines()[-1] if result.stdout.strip() else "error"
    print(f"\n  Notification record: {output}")
    assert "push" in output, f"Expected push notification, got: {output}"
    print("  ✓ Correct — PUSH notification created (worker was online)")
    return job_id

# ══════════════════════════════════════════════════════════════════════════════
# TEST 4 — Mark worker OFFLINE
# ══════════════════════════════════════════════════════════════════════════════

def test_go_offline(worker_token):
    section("TEST 4 — Mark worker OFFLINE")

    r = post("/api/notifications/offline", token=worker_token)
    p("POST /api/notifications/offline", r)
    assert r.status_code == 200
    assert r.json()["status"] == "offline"
    print("\n  ✓ Worker marked OFFLINE")

# ══════════════════════════════════════════════════════════════════════════════
# TEST 5 — Check worker status (expect: offline)
# ══════════════════════════════════════════════════════════════════════════════

def test_check_status_offline(customer_token):
    section("TEST 5 — Check worker status (expect: offline)")

    r = get(f"/api/notifications/status/{WORKER_ID}", customer_token)
    p(f"GET /api/notifications/status/{WORKER_ID[:8]}...", r)
    assert r.json()["is_online"] == False
    print("\n  ✓ Status correctly reported as OFFLINE")

# ══════════════════════════════════════════════════════════════════════════════
# TEST 6 — Book job while worker is OFFLINE → expect SMS fallback
# ══════════════════════════════════════════════════════════════════════════════

def test_job_creates_sms_notification(customer_token):
    section("TEST 6 — Book job (worker OFFLINE) → expect SMS fallback")

    r = post("/api/jobs", {
        "category_id": CATEGORY_ID,
        "title":       "Fix bathroom tap",
        "description": "Dripping tap needs washer replacement",
        "location":    "Westlands",
        "budget":      1500
    }, customer_token)
    p("POST /api/jobs", r)
    assert r.status_code == 201
    job_id = r.json()["job_id"]

    import subprocess, textwrap
    script = textwrap.dedent(f"""
        from app import create_app, db
        app = create_app()
        with app.app_context():
            from app.models import Notification
            from app.models.worker import Worker
            w = Worker.query.get('{WORKER_ID}')
            n = Notification.query.filter_by(user_id=w.user_id).order_by(
                Notification.created_at.desc()
            ).first()
            if n:
                print(f'type={{n.type}} | status={{n.status}} | title={{n.title}}')
            else:
                print('No notification found')
    """)
    result = subprocess.run(
        ["pipenv", "run", "python", "-c", script],
        capture_output=True, text=True
    )
    output = result.stdout.strip().splitlines()[-1] if result.stdout.strip() else "error"
    print(f"\n  Notification record: {output}")
    assert "sms" in output, f"Expected SMS notification, got: {output}"
    print("  ✓ Correct — SMS notification sent (worker was offline)")
    return job_id

# ══════════════════════════════════════════════════════════════════════════════
# TEST 7 — Get pending notifications (worker polls when back online)
# ══════════════════════════════════════════════════════════════════════════════

def test_get_pending_notifications(worker_token):
    section("TEST 7 — Worker polls pending notifications")

    r = get("/api/notifications/pending", worker_token)
    p("GET /api/notifications/pending", r)
    assert r.status_code == 200
    notifications = r.json().get("notifications", [])
    print(f"\n  Found {len(notifications)} pending notification(s)")
    for n in notifications:
        print(f"  → [{n['type']:4}] {n['title']} | priority={n['priority']}")

# ══════════════════════════════════════════════════════════════════════════════
# TEST 8 — WebSocket simulation (push notification real-time)
# ══════════════════════════════════════════════════════════════════════════════

def test_websocket_push(worker_token, customer_token):
    section("TEST 8 — WebSocket simulation (real-time push)")

    received = []
    sio = socketio.Client()

    @sio.event
    def connect():
        print("  [WS] Connected to server")
        sio.emit("join", {"token": worker_token})
        print("  [WS] Joined notification room")

    @sio.on("notification")
    def on_notification(data):
        print(f"  [WS] ✓ PUSH received: {json.dumps(data, indent=4)}")
        received.append(data)

    @sio.event
    def disconnect():
        print("  [WS] Disconnected")

    try:
        sio.connect(BASE)
        time.sleep(1)

        # send heartbeat to mark worker online
        post("/api/notifications/heartbeat", {
            "device_id": "android-device-001", "device_type": "android"
        }, worker_token)
        print("  [WS] Worker marked online via heartbeat")
        time.sleep(0.5)

        # customer books a job — should trigger push to connected worker
        print("  [WS] Customer booking job...")
        r = post("/api/jobs", {
            "category_id": CATEGORY_ID,
            "title":       "Install new pipes",
            "description": "Full bathroom refit",
            "location":    "Karen",
            "budget":      12000
        }, customer_token)
        print(f"  [WS] Job created: HTTP {r.status_code}")

        # wait for push to arrive
        time.sleep(2)

        if received:
            print(f"\n  ✓ WebSocket push delivered successfully ({len(received)} message(s))")
        else:
            print("\n  [!] No WebSocket push received — check socketio room join")

        sio.disconnect()

    except Exception as e:
        print(f"  [!] WebSocket error: {e}")
        print("      Install client: pipenv install 'python-socketio[client]'")

# ══════════════════════════════════════════════════════════════════════════════
# TEST 9 — Heartbeat timeout simulation (5 min threshold)
# ══════════════════════════════════════════════════════════════════════════════

def test_heartbeat_timeout_simulation(worker_token, customer_token):
    section("TEST 9 — Simulate stale heartbeat (backdated last_heartbeat)")

    import subprocess, textwrap
    # backdate last_heartbeat by 10 minutes to simulate timeout
    script = textwrap.dedent(f"""
        from app import create_app, db
        from datetime import datetime, timedelta
        app = create_app()
        with app.app_context():
            from app.models import UserPresence
            from app.models.worker import Worker
            w = Worker.query.get('{WORKER_ID}')
            p = UserPresence.query.filter_by(user_id=w.user_id).first()
            if p:
                p.last_heartbeat = datetime.utcnow() - timedelta(minutes=10)
                p.is_online = True   # flag says online but heartbeat is stale
                db.session.commit()
                print('Backdated heartbeat by 10 minutes')
    """)
    result = subprocess.run(
        ["pipenv", "run", "python", "-c", script],
        capture_output=True, text=True
    )
    print(f"  Setup: {result.stdout.strip().splitlines()[-1] if result.stdout.strip() else 'done'}")

    # now check status — should report offline despite is_online=True
    r = get(f"/api/notifications/status/{WORKER_ID}", customer_token)
    p("GET /api/notifications/status (stale heartbeat)", r)
    is_online = r.json()["is_online"]
    print(f"\n  is_online flag=True but last_heartbeat=10min ago → reported as: {'online' if is_online else 'offline'}")
    if not is_online:
        print("  ✓ Correct — stale heartbeat correctly treated as offline")
    else:
        print("  [!] Threshold check may not be working")

# ══════════════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("KaziConnect — Notification System Tests")
    print(f"Server: {BASE}\n")

    # login
    print("Logging in...")
    admin_token    = login(ADMIN_EMAIL)
    customer_token = login(CUSTOMER_EMAIL)
    worker_token   = login(WORKER_EMAIL)

    if not all([admin_token, customer_token, worker_token]):
        print("\n[!] Could not get all tokens. Aborting.")
        exit(1)

    print(f"  ✓ admin    token: {admin_token[:30]}...")
    print(f"  ✓ customer token: {customer_token[:30]}...")
    print(f"  ✓ worker   token: {worker_token[:30]}...")

    # ensure worker has skill + is verified
    print("\nSetting up worker skill...")
    setup_worker_skill(admin_token)

    # run tests
    test_heartbeat_online(worker_token)
    test_check_status_online(customer_token)
    test_job_creates_push_notification(customer_token)
    test_go_offline(worker_token)
    test_check_status_offline(customer_token)
    test_job_creates_sms_notification(customer_token)
    test_get_pending_notifications(worker_token)
    test_heartbeat_timeout_simulation(worker_token, customer_token)
    test_websocket_push(worker_token, customer_token)   # runs last (blocking)

    print("\n\n" + "═"*60)
    print("  All notification tests complete.")
    print("═"*60)
