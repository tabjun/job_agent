from io import StringIO
import json
from unittest.mock import Mock, patch
from urllib.error import HTTPError
import unittest

from job_agent.ui.sharing import Sharing
import test_ui


class SharingTests(unittest.TestCase):
    def test_tunnel_lifecycle_confirmation_and_session_revocation(self):
        share = Sharing(8765)
        process = Mock()
        process.poll.return_value = None
        process.stdout = StringIO("https://fixture-test.trycloudflare.com\n")
        with (
            patch.object(Sharing, "binary", return_value="cloudflared"),
            patch(
                "job_agent.ui.sharing.subprocess.Popen", return_value=process
            ) as spawn,
            patch("job_agent.ui.sharing.threading.Thread"),
        ):
            with self.assertRaises(ValueError):
                share.start(False)
            share.start(True)
            share._watch(process)
            state = share.status(True)
            self.assertEqual(state["state"], "active")
            self.assertEqual(state["url"], "https://fixture-test.trycloudflare.com")
            cookie = "__Host-resume_session=" + share.login(state["access_code"])
            self.assertTrue(share.authenticated(cookie))
            self.assertNotIn("access_code", share.status())
            self.assertNotIn("owner_access_code", share.status())
            self.assertNotIn(state["access_code"], str(spawn.call_args))
            share.start(True)
            spawn.assert_called_once()
            share.stop()
            process.terminate.assert_called_once()
            self.assertFalse(share.authenticated(cookie))
            self.assertEqual(share.status()["state"], "stopped")

    def test_wrong_code_rate_limited(self):
        share = Sharing(8765)
        for _ in range(20):
            with self.assertRaises(ValueError):
                share.login("wrong")
        with self.assertRaisesRegex(ValueError, "잠시"):
            share.login("wrong")


class RemoteHttpTests(test_ui.HttpTests):
    def test_external_link_navigation_opens_only_login_shell(self):
        headers = {
            **self.remote_headers(),
            "Origin": "https://chatgpt.com",
            "Sec-Fetch-Site": "cross-site",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Dest": "document",
        }
        session = self.server.sharing.login(self.server.sharing.code)
        headers["Cookie"] = "__Host-resume_session=" + session
        with self.request("/", **headers) as response:
            self.assertIn('id="login-form"', response.read().decode())
        for path, data in [
            ("/api/config", None),
            ("/api/profile", None),
            ("/api/login", {"code": self.server.sharing.code}),
            ("/", {}),
        ]:
            with self.assertRaises(HTTPError) as error:
                self.request(path, data, **headers)
            self.assertEqual(error.exception.code, 403)
        headers["Sec-Fetch-Mode"] = "cors"
        with self.assertRaises(HTTPError) as error:
            self.request("/", **headers)
        self.assertEqual(error.exception.code, 403)

    def remote_headers(self):
        self.server.sharing.process = Mock()
        self.server.sharing.process.poll.return_value = None
        self.server.sharing.process.stdout = None
        self.server.sharing.url = "https://fixture.trycloudflare.com"
        self.server.sharing.code = "fixture-secret-access-code"
        return {
            "Host": "fixture.trycloudflare.com",
            "Origin": "https://fixture.trycloudflare.com",
            "CF-Connecting-IP": "192.0.2.1",
        }

    def test_remote_login_gate_cookie_and_admin_boundary(self):
        headers = self.remote_headers()
        with self.request("/", **headers) as response:
            self.assertIn('id="login-form"', response.read().decode())
        for path in ["/api/config", "/api/profile", "/api/runs"]:
            with self.assertRaises(HTTPError) as error:
                self.request(path, **headers, **{"X-Session-Token": self.server.token})
            self.assertEqual(error.exception.code, 401)
        with self.request(
            "/api/login", {"code": self.server.sharing.code}, **headers
        ) as response:
            cookie = response.headers["Set-Cookie"]
            for flag in ["HttpOnly", "Secure", "SameSite=Strict", "Path=/"]:
                self.assertIn(flag, cookie)
        auth = {
            **headers,
            "Cookie": cookie.split(";")[0],
            "X-Session-Token": self.server.token,
        }
        with self.request("/api/config", **auth) as response:
            data = json.load(response)
            self.assertFalse(data["local_owner"])
            self.assertNotIn("admin_token", data)
            self.assertEqual(data["allowed_providers"], ["none"])
            self.assertNotIn("openai", data["providers"])
            self.assertNotIn("gemini", data["models"])
        with self.request("/api/profile", **auth) as response:
            self.assertEqual(json.load(response)["format"], "job-agent.resume/v1")
        with self.request("/api/sharing", **auth) as response:
            self.assertNotIn("access_code", json.load(response))
        with patch.object(self.server.service, "run") as run:
            for provider in ["custom", "openai", "gemini", "unknown"]:
                with self.assertRaises(HTTPError) as error:
                    self.request("/api/run", {"provider": provider}, **auth)
                self.assertEqual(error.exception.code, 403)
            run.assert_not_called()
            run.return_value = {"ok": True}
            for provider in ["none"]:
                with self.request(
                    "/api/run", {"provider": provider}, **auth
                ) as response:
                    self.assertTrue(json.load(response)["ok"])
            self.assertEqual(run.call_count, 1)
        for path in [
            "/api/model-connection",
            "/api/model-list",
            "/api/sharing/start",
            "/api/sharing/stop",
        ]:
            with self.assertRaises(HTTPError) as error:
                self.request(
                    path, {}, **auth, **{"X-Admin-Token": self.server.admin_token}
                )
            self.assertEqual(error.exception.code, 403)
        self.server.sharing.stop()
        self.assertFalse(self.server.sharing.authenticated(auth["Cookie"]))

    def test_forwarded_local_host_cannot_bypass_remote_login(self):
        self.remote_headers()
        with self.assertRaises(HTTPError):
            self.request("/api/config", **{"CF-Connecting-IP": "192.0.2.1"})

    def test_local_admin_connection_and_no_secret_readback(self):
        headers = {
            "X-Session-Token": self.server.token,
            "X-Admin-Token": self.server.admin_token,
        }
        connection = {
            "base_url": "http://127.0.0.1:11434/v1",
            "model": "test:model",
            "api_key": "private-key",
            "connection_consent": True,
        }
        with self.request("/api/model-connection", connection, **headers) as response:
            self.assertTrue(json.load(response)["configured"])
        with self.request("/api/model-connection", **headers) as response:
            self.assertNotIn("private-key", response.read().decode())

    def test_remote_policy_is_server_only_and_default_denies_resources(self):
        headers = self.remote_headers()
        session = self.server.sharing.login(self.server.sharing.code)
        headers.update(
            {
                "Cookie": "__Host-resume_session=" + session,
                "X-Session-Token": self.server.token,
            }
        )
        with self.request("/api/config", **headers) as response:
            config = json.load(response)
            self.assertEqual(config["allowed_providers"], ["none"])
            self.assertFalse(config["web_search"])
            self.assertNotIn("can_manage_remote_models", config)
        with self.request("/", **headers) as response:
            document = response.read().decode()
            self.assertNotIn('<option value="openai">', document)
            self.assertNotIn('<option value="gemini">', document)
            self.assertNotIn('<option value="custom">AI', document)
            self.assertNotIn('<option value="web">', document)
            self.assertNotIn("과금", document)
            self.assertIn("입력 자료의 AI 전송에 동의", document)
        for request_headers in [
            headers,
            {
                "X-Session-Token": self.server.token,
                "X-Admin-Token": self.server.admin_token,
            },
        ]:
            with self.assertRaises(HTTPError) as error:
                self.request(
                    "/api/sharing/providers",
                    {"providers": ["openai"]},
                    **request_headers,
                )
            self.assertEqual(error.exception.code, 404)
        with patch.object(self.server.service, "run") as run:
            for payload in [
                {"provider": "custom"},
                {"provider": "openai"},
                {"provider": "gemini"},
                {"provider": "none", "source": "web"},
            ]:
                with self.assertRaises(HTTPError) as error:
                    self.request("/api/run", payload, **headers)
                self.assertEqual(error.exception.code, 403)
            run.assert_not_called()

    def test_startup_policy_paid_guard_and_explicit_custom(self):
        from job_agent.ui.server import LocalServer

        with self.assertRaisesRegex(ValueError, "Paid"):
            LocalServer(
                ("127.0.0.1", 0), self.server.service, remote_providers=["openai"]
            )
        explicit = LocalServer(
            ("127.0.0.1", 0), self.server.service, remote_providers=["custom"]
        )
        try:
            self.assertEqual(explicit.remote_providers, ("none", "custom"))
        finally:
            explicit.server_close()
