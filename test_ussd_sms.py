"""
Test USSD and SMS offline flows.
Run: pipenv run python test_ussd_sms.py
"""
import requests
import json

BASE = "http://localhost:5000"

# ── helpers ──────────────────────────────────────────────────────────────────

def p(label, r):
    print(f"\n{'='*50}")
    print(f"[{label}] {r.status_code}")
    try:
        print(json.dumps(r.json(), indent=2))
    except Exception:
        print(r.text)

def post(path, data, json_body=True):
    if json_body:
        return requests.post(f"{BASE}{path}", json=data)
    return requests.post(f"{BASE}{path}", data=data)

# ── setup: register a customer and a worker ───────────────────────────────────

def setup_users():
    customer = post("/api/auth/register", {
        "email": "ussd_customer@test.com",
        "password": "Test1234!",
        "full_name": "USSD Customer",
        "phone": "+254700000001",
        "role": "customer"
    })
    p("Register Customer", customer)

    worker = post("/api/auth/register", {
        "email": "sms_worker@test.com",
        "password": "Test1234!",
        "full_name": "SMS Worker",
        "phone": "+254700000002",
        "role": "worker"
    })
    p("Register Worker", worker)

    return customer.json(), worker.json()

def get_token(email, password):
    r = post("/api/auth/login", {"email": email, "password": password})
    data = r.json()
    # If 2FA is required, skip OTP for test (sandbox OTP won't arrive)
    if data.get("requires_2fa"):
        print(f"  [!] 2FA required for {email} — skipping token (OTP not available in test)")
        return None
    return data.get("token")

# ── USSD tests ────────────────────────────────────────────────────────────────

def test_ussd():
    print("\n" + "="*50)
    print("USSD TESTS")
    SESSION = "ussd-test-session-001"
    PHONE   = "+254700000001"

    # Step 1: open session (empty text)
    r = post("/api/ussd/callback", {
        "sessionId": SESSION,
        "phoneNumber": PHONE,
        "text": ""
    }, json_body=False)
    p("USSD: Main Menu", r)
    assert "CON" in r.text or "END" in r.text, "Expected CON/END response"

    # Step 2: choose "Book Service" (1)
    r = post("/api/ussd/callback", {
        "sessionId": SESSION,
        "phoneNumber": PHONE,
        "text": "1"
    }, json_body=False)
    p("USSD: Select Category", r)

    # Step 3: pick first category
    r = post("/api/ussd/callback", {
        "sessionId": SESSION,
        "phoneNumber": PHONE,
        "text": "1*1"
    }, json_body=False)
    p("USSD: Enter Location", r)

    # Step 4: enter location
    r = post("/api/ussd/callback", {
        "sessionId": SESSION,
        "phoneNumber": PHONE,
        "text": "1*1*Nairobi"
    }, json_body=False)
    p("USSD: Enter Budget", r)

    # Step 5: enter budget → job created
    r = post("/api/ussd/callback", {
        "sessionId": SESSION,
        "phoneNumber": PHONE,
        "text": "1*1*Nairobi*1500"
    }, json_body=False)
    p("USSD: Job Created", r)
    assert "END" in r.text, "Expected END after job creation"

    # Step 6: new session → check My Jobs (2)
    SESSION2 = "ussd-test-session-002"
    r = post("/api/ussd/callback", {
        "sessionId": SESSION2,
        "phoneNumber": PHONE,
        "text": ""
    }, json_body=False)
    p("USSD: Main Menu (session 2)", r)

    r = post("/api/ussd/callback", {
        "sessionId": SESSION2,
        "phoneNumber": PHONE,
        "text": "2"
    }, json_body=False)
    p("USSD: My Jobs", r)

# ── SMS tests ─────────────────────────────────────────────────────────────────

def test_sms_send():
    print("\n" + "="*50)
    print("SMS SEND TEST (sandbox — no real delivery)")

    r = post("/api/sms/send", {
        "phone": "+254700000002",
        "message": "KaziConnect test message"
    })
    p("SMS: Send", r)

def test_sms_incoming_accept():
    print("\n" + "="*50)
    print("SMS INCOMING: Worker replies YES <job_id>")

    # Simulate Africa's Talking inbound webhook
    r = post("/api/sms/callback", {
        "from": "+254700000002",
        "text": "YES abc12345",
        "id": "ext-msg-001"
    })
    p("SMS: Incoming YES (accept)", r)

def test_sms_incoming_decline():
    r = post("/api/sms/callback", {
        "from": "+254700000002",
        "text": "NO abc12345",
        "id": "ext-msg-002"
    })
    p("SMS: Incoming NO (decline)", r)

def test_sms_incoming_unknown():
    r = post("/api/sms/callback", {
        "from": "+254700000002",
        "text": "Hello there",
        "id": "ext-msg-003"
    })
    p("SMS: Incoming unknown text", r)

# ── run ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("KaziConnect — USSD & SMS Offline Test")
    print("Make sure the server is running: pipenv run python run.py\n")

    setup_users()
    test_ussd()
    test_sms_send()
    test_sms_incoming_accept()
    test_sms_incoming_decline()
    test_sms_incoming_unknown()

    print("\n✓ All tests completed.")
