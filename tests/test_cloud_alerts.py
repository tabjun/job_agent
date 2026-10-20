"""Owner-only server subscription: allowlist, split secrets, retries, export flag.

No Supabase, mail provider or network: every HTTP call goes to a mock transport.
"""

import json
import os
import tempfile
import threading
import unittest
from datetime import datetime
from http.server import ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import httpx

from job_agent.alerts.cloud import CloudBackend, CloudConfig, ServerWorker
from job_agent.core.job_status import KST
from job_agent.hosting.alert_handler import SubscriptionHandler, WorkerHandler, dispatch
from job_agent.hosting.build import build

OWNER = "owner@example.com"
DELIVERY = "11111111-1111-4111-8111-111111111111"
SUBSCRIPTION = "22222222-2222-4222-8222-222222222222"
USER = "33333333-3333-4333-8333-333333333333"
ENV = {
    "ALERT_SUPABASE_URL": "https://db.example.test",
    "ALERT_SUPABASE_ANON_KEY": "publishable-fixture",
    "ALERT_SUPABASE_SERVICE_KEY": "service-fixture",
    "ALERT_WORKER_SECRET": "w" * 40,
    "ALERT_UNSUBSCRIBE_SECRET": "u" * 40,
    "ALERT_RATE_PEPPER": "p" * 40,
    "ALERT_SERVER_SEARCH_KEY": "search-fixture",
    "ALERT_PUBLIC_ORIGIN": "https://alerts.example.test",
    "ALERT_SERVER_FROM": "alerts@example.test",
    "ALERT_ALLOWED_EMAILS": f" {OWNER.upper()} , not-an-email",
    "ALERT_RESEND_KEY": "",
    "ALERT_SERVER_SMTP_HOST": "smtp.example.test",
    "ALERT_SERVER_SMTP_USER": "user",
    "ALERT_SERVER_SMTP_PASSWORD": "password",
    "ALERT_SERVER_SMTP_PORT": "587",
    "ALERT_SERVICE_ENABLED": "true",
    "ALERT_SCHEDULER_READY": "true",
}


def config(**changes):
    with patch.dict(os.environ, {**ENV, **changes}):
        return CloudConfig.environment()


class FakeSupabase:
    """Records calls; answers RPCs from a table of canned results."""

    def __init__(self, rpc=None):
        self.calls = []
        self.rpc = {"alert_reserve_code": True, "alert_health": {"ready": True}}
        self.rpc.update(rpc or {})

    def __call__(self, request):
        body = json.loads(request.content) if request.content else None
        self.calls.append((request.url.path, body))
        path = request.url.path
        if path.startswith("/rest/v1/rpc/"):
            return httpx.Response(200, json=self.rpc.get(path.rsplit("/", 1)[1]))
        if path == "/auth/v1/verify":
            return httpx.Response(200, json={"access_token": "t" * 40})
        if path == "/auth/v1/user":
            return httpx.Response(
                200,
                json={"id": USER, "email": OWNER, "email_confirmed_at": "2026-10-20"},
            )
        return httpx.Response(200, json={})

    def paths(self):
        return [path for path, _ in self.calls]


def backend(fake, **changes):
    return CloudBackend(
        config(**changes), httpx.Client(transport=httpx.MockTransport(fake))
    )


class ConfigTests(unittest.TestCase):
    def test_ready_needs_allowlist_and_three_distinct_secrets(self):
        self.assertTrue(config().ready())
        self.assertEqual(config().allowed, frozenset({OWNER}))
        for changes in [
            {"ALERT_ALLOWED_EMAILS": ""},
            {"ALERT_RATE_PEPPER": "w" * 40},  # same value as the worker secret
            {"ALERT_UNSUBSCRIBE_SECRET": "short"},
            {"ALERT_SCHEDULER_READY": "false"},
        ]:
            with self.subTest(changes=changes):
                self.assertFalse(config(**changes).ready())


class BackendTests(unittest.TestCase):
    def test_code_is_only_requested_for_the_allowlisted_owner(self):
        fake = FakeSupabase()
        self.assertEqual(
            backend(fake).code("stranger@example.com", "203.0.113.1"),
            {"requested": True},
        )
        self.assertEqual(fake.calls, [])  # same answer, nothing sent
        backend(fake).code(OWNER, "203.0.113.1")
        self.assertEqual(
            fake.paths(), ["/rest/v1/rpc/alert_reserve_code", "/auth/v1/otp"]
        )
        self.assertFalse(fake.calls[1][1]["create_user"])
        keys = fake.calls[0][1]["p_keys"]
        self.assertNotIn(OWNER, json.dumps(keys))  # hashed, never raw

    def test_code_checks_are_rate_limited_per_address_before_supabase(self):
        fake = FakeSupabase()
        result = backend(fake).verify(OWNER, "12345678", "203.0.113.1")
        self.assertEqual(result["email"], OWNER)
        self.assertEqual(fake.paths()[:2], ["/rest/v1/rpc/alert_reserve_code", "/auth/v1/verify"])
        keys = fake.calls[0][1]["p_keys"]
        self.assertEqual(keys[0], "verifyglobal")
        self.assertTrue(keys[1].startswith("verify:") and keys[2].startswith("verifyip:"))
        blocked = FakeSupabase({"alert_reserve_code": False})
        with self.assertRaises(ValueError):
            backend(blocked).verify(OWNER, "12345678", "203.0.113.1")
        self.assertNotIn("/auth/v1/verify", blocked.paths())
        with self.assertRaises(PermissionError):
            backend(FakeSupabase()).verify("stranger@example.com", "12345678")

    def test_save_waits_for_database_health_and_sends_consent_version(self):
        payload = {
            "platforms": {"wanted": {"role": "데이터 분석가", "location": "서울"}},
            "schedule": {"frequency": "daily", "hour": 8},
            "search_consent": True,
            "storage_consent": True,
            "name": "분석",
        }
        with self.assertRaises(ConnectionError):
            backend(FakeSupabase({"alert_health": {"ready": False}})).save(
                "t" * 40, payload
            )
        fake = FakeSupabase({"alert_save": {"id": SUBSCRIPTION}})
        backend(fake).save("t" * 40, payload)
        saved = dict(fake.calls)["/rest/v1/rpc/alert_save"]
        self.assertEqual(saved["p_consent_version"], "job-alerts/v2")

    def test_unsubscribe_links_use_their_own_key_and_survive_rotation(self):
        fake = FakeSupabase()
        old = backend(fake).unsubscribe_token(SUBSCRIPTION)
        self.assertTrue(old.startswith("v1." + SUBSCRIPTION + "."))
        rotated = backend(
            fake,
            ALERT_UNSUBSCRIBE_SECRET="n" * 40,
            ALERT_UNSUBSCRIBE_SECRET_PREVIOUS="u" * 40,
        )
        self.assertEqual(rotated.unsubscribe(old), {"unsubscribed": True})
        for token in [
            old.replace("v1.", "v2.", 1),
            old[:-1] + ("0" if old[-1] != "0" else "1"),
            SUBSCRIPTION + "." + old.rsplit(".", 1)[1],  # unversioned format
        ]:
            with self.subTest(token=token), self.assertRaises(PermissionError):
                backend(FakeSupabase(), ALERT_UNSUBSCRIBE_SECRET="n" * 40).unsubscribe(
                    token
                )
        # A worker-secret leak cannot forge links.
        self.assertNotEqual(
            backend(fake).unsubscribe_token(SUBSCRIPTION, "w" * 40), old
        )


class Mailer:
    def __init__(self, fail=False):
        self.sent, self.fail = [], fail

    def send(self, payload, identity):
        self.sent.append(identity)
        if self.fail:
            raise OSError("connection dropped")
        return "smtp-accepted"


class WorkerTests(unittest.TestCase):
    def claim(self, state="collecting", payload=None, platforms=None):
        return {
            "delivery": {"id": DELIVERY, "state": state, "payload": payload},
            "subscription": {
                "id": SUBSCRIPTION,
                "email": OWNER,
                "name": "분석",
                "platforms": platforms
                or {"wanted": {"role": "데이터 분석가", "location": "", "keywords": "", "exclude": ""}},
                "schedule": {"frequency": "daily", "hour": 8, "weekday": 0},
                "max_results": 10,
            },
            "sent_urls": [],
        }

    def worker(self, fake, mailer, rows=(), **changes):
        check = {
            "status": "open",
            "deadline": "2099-11-30",
            "job_title": "데이터 분석가",
            "experience": {"kind": "any"},
        }
        return ServerWorker(
            backend(fake, **changes),
            mailer=mailer,
            searcher=lambda query, domains: list(rows),
            verifier=lambda url, now: check,
            clock=lambda: datetime(2026, 10, 20, 9, tzinfo=KST),
        )

    def finished(self, fake):
        return dict(fake.calls)["/rest/v1/rpc/alert_finish"]["p_state"]

    def test_smtp_failure_before_hand_over_retries_after_it_is_unknown(self):
        row = {"title": "데이터 분석가", "url": "https://www.wanted.co.kr/wd/1"}
        fake = FakeSupabase({"alert_claim": self.claim(), "alert_prepare": True, "alert_can_send": False})
        self.assertEqual(self.worker(fake, Mailer(), [row]).run_one()["state"], "cancelled")
        fake = FakeSupabase({"alert_claim": self.claim(), "alert_prepare": True, "alert_can_send": True})
        mailer = Mailer(fail=True)
        self.assertEqual(self.worker(fake, mailer, [row]).run_one()["state"], "unknown")
        self.assertEqual(self.finished(fake), "unknown")
        # A database error before the mail server was contacted is retried.
        fake = FakeSupabase({"alert_claim": self.claim(), "alert_prepare": True})
        fake.rpc["alert_can_send"] = None

        def broken(request, inner=fake):
            if request.url.path.endswith("alert_can_send"):
                return httpx.Response(500)
            return inner(request)

        worker = self.worker(fake, Mailer(), [row])
        worker.backend.client = httpx.Client(transport=httpx.MockTransport(broken))
        self.assertEqual(worker.run_one()["state"], "retry")

    def test_resumed_send_reuses_payload_without_cancelling_it(self):
        payload = {
            "email": OWNER,
            "subject": "s",
            "text": "t",
            "html": "<p>t</p>",
            "transport": "resend",
            # Deadline already passed: a recheck would wrongly cancel a mail
            # that may have been delivered before the last attempt failed.
            "jobs": [{"url": "https://www.wanted.co.kr/wd/1", "status_check": {"status": "open", "deadline": "2026-10-01"}}],
            "urls": ["https://www.wanted.co.kr/wd/1"],
        }
        fake = FakeSupabase({"alert_claim": self.claim("sending", payload)})
        mailer = Mailer()
        result = self.worker(fake, mailer, ALERT_RESEND_KEY="resend-fixture").run_one()
        self.assertEqual(result["state"], "sent")
        self.assertEqual(mailer.sent, [DELIVERY])
        self.assertNotIn("/rest/v1/rpc/alert_can_send", fake.paths())

    def test_worker_collects_with_validated_conditions_only(self):
        fake = FakeSupabase({"alert_claim": self.claim(platforms={"wanted": {"role": "데이터 분석가", "injected": "x" * 10}})})
        seen = []
        worker = self.worker(fake, Mailer())
        worker.searcher = lambda query, domains: seen.append(query) or []
        self.assertEqual(worker.run_one()["state"], "empty")
        self.assertEqual(seen, ["데이터 분석가 채용"])
        fake = FakeSupabase({"alert_claim": self.claim(platforms={"wanted": {"location": "서울"}})})
        self.assertEqual(self.worker(fake, Mailer()).run_one()["state"], "retry")


class HandlerTests(unittest.TestCase):
    def serve(self, handler):
        server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        return f"http://127.0.0.1:{server.server_address[1]}"

    def test_worker_route_is_post_with_its_own_secret(self):
        base = self.serve(WorkerHandler)
        with patch.dict(os.environ, ENV):
            with self.assertRaises(HTTPError) as caught:
                urlopen(base)
            self.assertEqual(caught.exception.code, 405)
            for secret in ["u" * 40, "p" * 40]:  # other purposes' secrets
                request = Request(base, data=b"{}", method="POST", headers={"Authorization": "Bearer " + secret})
                with self.assertRaises(HTTPError) as caught:
                    urlopen(request)
                self.assertEqual(caught.exception.code, 401)

    def test_status_is_not_ready_until_the_database_says_so(self):
        base = self.serve(SubscriptionHandler)
        with patch.dict(os.environ, ENV), patch.object(
            CloudBackend, "health", return_value={"ready": False}
        ):
            self.assertFalse(json.loads(urlopen(base).read())["ready"])
        with patch.dict(os.environ, ENV), patch.object(
            CloudBackend, "health", return_value={"ready": True}
        ):
            self.assertTrue(json.loads(urlopen(base).read())["ready"])
        with patch.dict(os.environ, {**ENV, "ALERT_ALLOWED_EMAILS": ""}):
            self.assertFalse(json.loads(urlopen(base).read())["ready"])

    def test_dispatch_passes_the_visitor_ip_to_code_checks(self):
        class Recorder:
            def verify(self, email, code, ip):
                return {"ip": ip}

        self.assertEqual(
            dispatch(Recorder(), {"action": "verify", "email": OWNER, "code": "1"}, ip="198.51.100.2"),
            {"ip": "198.51.100.2"},
        )
        with self.assertRaises(ValueError):
            dispatch(Recorder(), {"action": "verify", "email": OWNER, "code": "1", "extra": 1})


class ExportTests(unittest.TestCase):
    def test_subscription_module_is_exported_only_on_request(self):
        with tempfile.TemporaryDirectory() as folder:
            plain = build(Path(folder) / "plain")
            full = build(Path(folder) / "full", with_subscriptions=True)
            for name in [
                "public/job-alerts.html",
                "public/subscription.js",
                "api/subscribe.py",
                "api/alert-worker.py",
                "job_agent/alerts/cloud.py",
                "job_agent/hosting/alert_handler.py",
            ]:
                with self.subTest(name=name):
                    self.assertFalse((plain / name).exists())
                    self.assertTrue((full / name).exists())
            functions = json.loads((plain / "vercel.json").read_text("utf-8"))["functions"]
            self.assertEqual(list(functions), ["api/run.py"])
            manifest = json.loads((plain / "export-manifest.json").read_text("utf-8"))
            self.assertFalse(manifest["server_subscriptions"])
            index = (plain / "public/index.html").read_text("utf-8")
            self.assertNotIn("job-alerts.html", index)


if __name__ == "__main__":
    unittest.main()
