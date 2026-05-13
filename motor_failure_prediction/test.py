import os
import sys
import uuid
import json
from typing import Dict, Optional
from dotenv import load_dotenv

load_dotenv()

import requests
API_KEY = (os.getenv("MOTOR_API_KEY") or "").strip()

BASE_URL = os.getenv("BASE_URL", "http://127.0.0.1:5001").rstrip("/")
API_KEY = os.getenv("MOTOR_API_KEY", "8da8847a3160d7e48e66efc235b65ba3ef9688b8325e09b172291fb68040008c")
TEST_USER_EMAIL = os.getenv("TEST_USER_EMAIL", "smoke.test@example.com")
TEST_USER_PASSWORD = os.getenv("TEST_USER_PASSWORD", "StrongPass123")
TEST_USER_NAME = os.getenv("TEST_USER_NAME", "smoke_user")
MOTOR_ID = os.getenv("TEST_MOTOR_ID", "Motor-A-01")


class SmokeRunner:
    def __init__(self):
        self.session = requests.Session()
        self.results = []
        self.token: Optional[str] = None
        self.created_motor_id: Optional[str] = None

    def _record(self, name: str, ok: bool, detail: str = ""):
        self.results.append((name, ok, detail))
        prefix = "PASS" if ok else "FAIL"
        print(f"[{prefix}] {name} {('- ' + detail) if detail else ''}")

    def _get_headers(self, use_bearer: bool = True) -> Dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if use_bearer and self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        else:
            headers["X-API-Key"] = API_KEY
        return headers

    def _request(self, method: str, path: str, **kwargs) -> requests.Response:
        url = f"{BASE_URL}{path}"
        timeout = kwargs.pop("timeout", 15)
        return self.session.request(method, url, timeout=timeout, **kwargs)

    def test_health_and_contract(self):
        r = self._request("GET", "/health")
        self._record("health", r.status_code == 200, f"status={r.status_code}")

        r = self._request("GET", "/openapi.json")
        ok = r.status_code == 200 and "paths" in r.json()
        self._record("openapi", ok, f"status={r.status_code}")

    def test_auth_flow(self):
        # Register is idempotent for smoke testing.
        register_payload = {
            "username": f"{TEST_USER_NAME}_{uuid.uuid4().hex[:6]}",
            "email": TEST_USER_EMAIL,
            "password": TEST_USER_PASSWORD,
        }
        r = self._request("POST", "/auth/register", json=register_payload)
        self._record("auth_register", r.status_code in (201, 409), f"status={r.status_code}")

        login_payload = {
            "identifier": TEST_USER_EMAIL,
            "password": TEST_USER_PASSWORD,
        }
        r = self._request("POST", "/auth/login", json=login_payload)
        if r.status_code != 200:
            self._record("auth_login", False, f"status={r.status_code}")
            return
        self._record("auth_login", True, "otp issued")

        login_json = r.json()
        otp = login_json.get("dev_otp")
        if not otp:
            # Try resend once (useful when SMTP not configured but fallback enabled there).
            r2 = self._request("POST", "/auth/resend-otp", json={"email": TEST_USER_EMAIL})
            if r2.status_code == 200:
                otp = r2.json().get("dev_otp")

        if not otp:
            self._record("auth_verify_otp", False, "dev_otp missing; configure SMTP or DEV_OTP_IN_RESPONSE=true")
            return

        verify_payload = {"email": TEST_USER_EMAIL, "otp": otp}
        r = self._request("POST", "/auth/verify-otp", json=verify_payload)
        if r.status_code == 200 and r.json().get("access_token"):
            self.token = r.json()["access_token"]
            self._record("auth_verify_otp", True, "token received")
        else:
            self._record("auth_verify_otp", False, f"status={r.status_code}")

        r = self._request("GET", "/auth/me", headers=self._get_headers(use_bearer=True))
        self._record("auth_me", r.status_code == 200, f"status={r.status_code}")

    def test_motor_crud(self):
        test_motor = f"Motor-Test-{uuid.uuid4().hex[:6]}"
        payload = {
            "motor_id": test_motor,
            "motor_type": "AC Induction",
        }
        r = self._request("POST", "/motors", headers=self._get_headers(), json=payload)
        created = r.status_code in (201, 409)
        self._record("motor_create", created, f"status={r.status_code}")
        if created:
            self.created_motor_id = test_motor

        r = self._request("GET", "/motors", headers=self._get_headers())
        self._record("motor_list", r.status_code == 200, f"status={r.status_code}")

        if self.created_motor_id:
            r = self._request("DELETE", f"/motors/{self.created_motor_id}", headers=self._get_headers())
            self._record("motor_deactivate", r.status_code == 200, f"status={r.status_code}")

            r = self._request("POST", f"/motors/{self.created_motor_id}/reactivate", headers=self._get_headers())
            self._record("motor_reactivate", r.status_code == 200, f"status={r.status_code}")

    def test_prediction_and_explain(self):
        r = self._request("GET", f"/predict/{MOTOR_ID}", headers=self._get_headers())
        self._record("predict_single", r.status_code in (200, 404), f"status={r.status_code}")

        r = self._request(
            "POST",
            "/predict/batch",
            headers=self._get_headers(),
            json={"motor_ids": ["Motor-A-01", "Motor-B-02"]},
        )
        self._record("predict_batch", r.status_code in (200, 404), f"status={r.status_code}")

        r = self._request("POST", "/predict/all", headers=self._get_headers())
        self._record("predict_all", r.status_code in (200, 404), f"status={r.status_code}")

        r = self._request("GET", f"/explain/status/{MOTOR_ID}", headers=self._get_headers())
        self._record("explain_status", r.status_code in (200, 404, 503), f"status={r.status_code}")

        r = self._request("GET", f"/explain/rul/{MOTOR_ID}", headers=self._get_headers())
        self._record("explain_rul", r.status_code in (200, 404, 503), f"status={r.status_code}")

    def test_alerts_and_insights(self):
        r = self._request("GET", "/alerts?limit=20", headers=self._get_headers())
        self._record("alerts_list", r.status_code == 200, f"status={r.status_code}")

        if r.status_code == 200:
            alerts = r.json().get("alerts", [])
            if alerts:
                alert_id = alerts[0]["alert_id"]
                r2 = self._request("POST", f"/alerts/{alert_id}/ack", headers=self._get_headers())
                self._record("alerts_ack_one", r2.status_code == 200, f"status={r2.status_code}")

        # Insights
        endpoints = [
            ("insights_fleet", "/insights/fleet-overview"),
            ("insights_distribution", "/insights/status-distribution"),
            ("insights_trend", "/insights/alerts-trend?days=7"),
            ("insights_sensor", f"/insights/sensor-trend/{MOTOR_ID}?sensor=s11&limit=50"),
            ("readings_latest", "/motors/readings/latest"),
            ("readings_history", f"/motors/{MOTOR_ID}/readings?limit=50"),
        ]
        for name, path in endpoints:
            rr = self._request("GET", path, headers=self._get_headers())
            self._record(name, rr.status_code in (200, 404), f"status={rr.status_code}")

    def test_live_stream(self):
        # Validate SSE endpoint returns at least one data frame.
        r = self._request(
            "GET",
            "/insights/live/stream?interval=2",
            headers=self._get_headers(),
            stream=True,
            timeout=20,
        )
        if r.status_code != 200:
            self._record("live_stream", False, f"status={r.status_code}")
            return

        got_frame = False
        for line in r.iter_lines(decode_unicode=True):
            if line and line.startswith("data: "):
                got_frame = True
                break
        self._record("live_stream", got_frame, "frame received" if got_frame else "no frame")

    def summary(self):
        total = len(self.results)
        passed = len([r for r in self.results if r[1]])
        failed = total - passed
        print("\n" + "=" * 72)
        print(f"Smoke test complete: {passed}/{total} passed, {failed} failed")
        if failed:
            print("Failed checks:")
            for name, ok, detail in self.results:
                if not ok:
                    print(f" - {name}: {detail}")
            return 1
        return 0


def main():
    print(f"Running backend smoke test against {BASE_URL}")
    print("Tip: start backend first with python3 app.py and data generator with python3 data_generator.py\n")

    runner = SmokeRunner()
    try:
        runner.test_health_and_contract()
        runner.test_auth_flow()
        runner.test_motor_crud()
        runner.test_prediction_and_explain()
        runner.test_alerts_and_insights()
        runner.test_live_stream()
    except requests.RequestException as req_err:
        print(f"Network error while testing: {req_err}")
        sys.exit(1)

    sys.exit(runner.summary())


if __name__ == "__main__":
    main()