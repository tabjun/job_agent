import asyncio
import html
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import tempfile
import threading
import unittest

from job_agent.browser.sync import ResumeSync, SyncWorker, resume_editor, control_value
from job_agent.core.paths import ProjectPaths
from job_agent.documents.profile import FORMAT


class FixtureHandler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def do_GET(self):
        content = f"""<label for="summary">소개</label><textarea id="summary">{html.escape(self.server.value)}</textarea>
        <button id="save" onclick="fetch('/save',{{method:'POST',body:document.querySelector('#summary').value}})">저장</button>
        <button id="no-save">저장하기</button><button id="submit" onclick="fetch('/submit',{{method:'POST'}})">지원하기</button>""".encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(content)

    def do_POST(self):
        if self.path == "/save":
            self.server.value = self.rfile.read(
                int(self.headers["Content-Length"])
            ).decode()
        else:
            self.server.submissions += 1
        self.send_response(200)
        self.end_headers()


class FixtureRegistry:
    def __init__(self, url):
        self.url = url

    def normalize(self, site):
        return site

    def target(self, site):
        return {"name": "Fixture", "candidate_urls": [self.url]}

    def matches_url(self, site, url):
        return url.startswith(self.url)

    def is_custom(self, site):
        return False


class SyncTests(unittest.IsolatedAsyncioTestCase):
    async def test_five_sites_selected_profile_save_and_local_session_reuse(self):
        with tempfile.TemporaryDirectory() as folder:
            server = ThreadingHTTPServer(("127.0.0.1", 0), FixtureHandler)
            server.value, server.submissions = "old", 0
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            url = f"http://127.0.0.1:{server.server_port}/"

            def profile(value):
                return {
                    "format": FORMAT,
                    "fields": [
                        {
                            "id": "summary",
                            "label": "소개",
                            "value": value,
                            "reviewed": True,
                            "evidence": [
                                {
                                    "source_id": "fixture",
                                    "paragraph_index": 0,
                                    "text": value,
                                }
                            ],
                        }
                    ],
                }

            source = profile("Common original fact")
            selected = profile("Reviewed organized fact")
            engine = ResumeSync(
                ProjectPaths(Path(folder)),
                lambda: source,
                registry=FixtureRegistry(url),
                headed=False,
                editor_check=lambda site, url: True,
            )
            try:
                for site in ["catch", "jobkorea", "saramin", "wanted", "incruit"]:
                    await engine.open({"site": site})
                    await engine.contexts[site].add_cookies(
                        [
                            {
                                "name": "fixture-session",
                                "value": site,
                                "url": url,
                                "expires": 2000000000,
                                "httpOnly": True,
                            }
                        ]
                    )
                    preview = await engine.capture({"site": site, "profile": selected})
                    self.assertEqual(
                        preview["suggested_mappings"],
                        [{"field_id": "summary", "target_index": 0}],
                    )
                    self.assertEqual(
                        preview["profile_fields"][0]["value"], "Reviewed organized fact"
                    )
                    payload = {
                        "site": site,
                        "profile": selected,
                        "nonce": preview["nonce"],
                        "consent": True,
                        "mappings": preview["suggested_mappings"],
                        "save_index": 0,
                    }
                    with self.assertRaises(ValueError):
                        await engine.apply({**payload, "profile": source})
                    result = await engine.apply(payload)
                    self.assertEqual(result["status"], "saved_verified")
                    self.assertEqual(server.value, "Reviewed organized fact")
                    self.assertEqual(
                        source["fields"][0]["value"], "Common original fact"
                    )
                    await engine.close_site({"site": site})
                    await engine.open({"site": site})
                    cookies = await engine.contexts[site].cookies()
                    self.assertTrue(
                        any(
                            cookie["name"] == "fixture-session"
                            and cookie["value"] == site
                            for cookie in cookies
                        )
                    )
                    self.assertNotIn(
                        "fixture-session", str(await engine.status({"site": site}))
                    )
                    await engine.close_site({"site": site})
                self.assertEqual(server.submissions, 0)
            finally:
                await engine.close()
                server.shutdown()
                server.server_close()
                thread.join()

    async def test_login_mfa_security_status_blocks_capture_and_apply(self):
        with tempfile.TemporaryDirectory() as folder:
            server = ThreadingHTTPServer(("127.0.0.1", 0), FixtureHandler)
            server.value, server.submissions = "old", 0
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            url = f"http://127.0.0.1:{server.server_port}/"
            profile = {
                "format": FORMAT,
                "fields": [
                    {
                        "id": "summary",
                        "label": "소개",
                        "value": "Synthetic fact",
                        "reviewed": True,
                        "evidence": [
                            {
                                "source_id": "fixture",
                                "paragraph_index": 0,
                                "text": "Synthetic fact",
                            }
                        ],
                    }
                ],
            }
            engine = ResumeSync(
                ProjectPaths(Path(folder)),
                lambda: profile,
                registry=FixtureRegistry(url),
                headed=False,
                editor_check=lambda site, url: True,
            )
            try:
                self.assertEqual(
                    (await engine.status({"site": "wanted"}))["status"], "not_opened"
                )
                await engine.open({"site": "wanted"})
                page = engine.contexts["wanted"].pages[0]
                preview = await engine.capture({"site": "wanted"})
                await page.set_content(
                    '<input autocomplete="one-time-code" value="DO-NOT-READ-OTP"><input type="password" value="DO-NOT-READ-PASSWORD">'
                )
                state = await engine.status({"site": "wanted"})
                self.assertEqual(state["status"], "mfa_required")
                self.assertNotIn("DO-NOT-READ", json.dumps(state))
                with self.assertRaisesRegex(ValueError, "2차 인증"):
                    await engine.capture({"site": "wanted"})
                with self.assertRaisesRegex(ValueError, "2차 인증"):
                    await engine.apply(
                        {
                            "site": "wanted",
                            "nonce": preview["nonce"],
                            "consent": True,
                            "mappings": [{"field_id": "summary", "target_index": 0}],
                            "save_index": 0,
                        }
                    )
                await page.set_content(
                    '<input type="password" value="DO-NOT-READ-PASSWORD">'
                )
                self.assertEqual(
                    (await engine.status({"site": "wanted"}))["status"],
                    "login_required",
                )
                await page.set_content(
                    '<div id="challenge-running">Security check</div>'
                )
                self.assertEqual(
                    (await engine.status({"site": "wanted"}))["status"],
                    "security_check",
                )
                engine.editor_check = lambda site, url: False
                await page.set_content("<textarea>Fixture</textarea>")
                self.assertEqual(
                    (await engine.status({"site": "wanted"}))["status"], "open_editor"
                )
                self.assertEqual(server.value, "old")
                self.assertEqual(server.submissions, 0)
                self.assertFalse(engine.store.directory.exists())
            finally:
                await engine.close()
                server.shutdown()
                server.server_close()
                thread.join()

    async def test_real_save_reload_stale_review_controls_and_no_submission(self):
        with tempfile.TemporaryDirectory() as folder:
            server = ThreadingHTTPServer(("127.0.0.1", 0), FixtureHandler)
            server.value, server.submissions = "old", 0
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            url = f"http://127.0.0.1:{server.server_port}/"
            profile = {
                "format": FORMAT,
                "fields": [
                    {
                        "id": "summary",
                        "label": "소개",
                        "value": "SQL source fact",
                        "reviewed": True,
                        "evidence": [
                            {
                                "source_id": "fixture",
                                "paragraph_index": 0,
                                "text": "SQL source fact",
                            }
                        ],
                    }
                ],
            }
            engine = ResumeSync(
                ProjectPaths(Path(folder)),
                lambda: profile,
                registry=FixtureRegistry(url),
                headed=False,
                editor_check=lambda site, url: True,
            )
            try:
                await engine.open({"site": "wanted"})
                preview = await engine.capture({"site": "wanted"})
                self.assertEqual(len(preview["buttons"]), 2)
                self.assertNotIn(
                    "지원하기", [row["label"] for row in preview["buttons"]]
                )
                payload = {
                    "site": "wanted",
                    "nonce": preview["nonce"],
                    "consent": True,
                    "mappings": [{"field_id": "summary", "target_index": 0}],
                    "save_index": 0,
                }
                for change in [
                    {"consent": False},
                    {"nonce": "stale"},
                    {"save_index": 99},
                    {"mappings": [{"field_id": "summary", "target_index": 0}] * 2},
                ]:
                    with self.assertRaises(ValueError):
                        await engine.apply({**payload, **change})
                profile["fields"][0]["value"] = "changed"
                with self.assertRaises(ValueError):
                    await engine.apply(payload)
                profile["fields"][0]["value"] = "SQL source fact"
                result = await engine.apply(payload)
                self.assertEqual(result["status"], "saved_verified")
                self.assertEqual(server.value, "SQL source fact")
                self.assertEqual(server.submissions, 0)
                records = [
                    p
                    for p in engine.store.directory.glob("*.json")
                    if "bindings" not in p.name
                ]
                self.assertEqual(
                    json.loads(records[0].read_text(encoding="utf-8"))["backup"][0][
                        "before"
                    ],
                    "old",
                )
                with self.assertRaises(ValueError):
                    await engine.apply(payload)
                preview = await engine.capture({"site": "wanted"})
                self.assertEqual(preview["saved_mappings"][0]["field_id"], "summary")
                await (
                    engine.contexts["wanted"]
                    .pages[0]
                    .locator("#summary")
                    .evaluate("el => el.readOnly = true")
                )
                with self.assertRaises(ValueError):
                    await engine.apply({**payload, "nonce": preview["nonce"]})
                await engine.contexts["wanted"].pages[0].reload()
                profile["fields"][0]["value"] = "new source fact"
                preview = await engine.capture({"site": "wanted"})
                result = await engine.apply(
                    {**payload, "nonce": preview["nonce"], "save_index": 1}
                )
                self.assertEqual(result["status"], "save_unverified")
                self.assertEqual(server.value, "SQL source fact")
                self.assertEqual(server.submissions, 0)
                self.assertNotIn("wanted", engine.previews)
            finally:
                await engine.close()
                server.shutdown()
                server.server_close()
                thread.join()

    async def test_autosave_and_non_wanted_guard(self):
        with tempfile.TemporaryDirectory() as folder:
            server = ThreadingHTTPServer(("127.0.0.1", 0), FixtureHandler)
            server.value, server.submissions = "old", 0
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            url = f"http://127.0.0.1:{server.server_port}/"
            profile = {
                "format": FORMAT,
                "fields": [
                    {
                        "id": "summary",
                        "label": "소개",
                        "value": "source fact",
                        "reviewed": True,
                        "evidence": [
                            {
                                "source_id": "fixture",
                                "paragraph_index": 0,
                                "text": "source fact",
                            }
                        ],
                    }
                ],
            }
            engine = ResumeSync(
                ProjectPaths(Path(folder)),
                lambda: profile,
                registry=FixtureRegistry(url),
                headed=False,
                editor_check=lambda site, url: True,
            )
            try:
                for site in ["catch", "wanted"]:
                    await engine.open({"site": site})
                    page = engine.contexts[site].pages[0]
                    await page.locator("#summary").evaluate(
                        "el => el.onblur = () => fetch('/save', {method:'POST',body:el.value})"
                    )
                    preview = await engine.capture({"site": site})
                    payload = {
                        "site": site,
                        "nonce": preview["nonce"],
                        "consent": True,
                        "mappings": [{"field_id": "summary", "target_index": 0}],
                        "autosave": True,
                    }
                    if site == "catch":
                        with self.assertRaises(ValueError):
                            await engine.apply(payload)
                        self.assertEqual(server.value, "old")
                    else:
                        result = await engine.apply(payload)
                        self.assertEqual(result["status"], "saved_verified")
                        self.assertEqual(server.value, "source fact")
            finally:
                await engine.close()
                server.shutdown()
                server.server_close()
                thread.join()


class WorkerTests(unittest.TestCase):
    def test_native_select_exact_label_conversion_without_guessing(self):
        target = {
            "tag": "select",
            "options": [
                {"label": "정규직", "value": "regular"},
                {"label": "Other", "value": "other", "disabled": True},
            ],
        }
        self.assertEqual(control_value(target, "정규직"), "regular")
        self.assertEqual(control_value(target, "regular"), "regular")
        with self.assertRaises(ValueError):
            control_value(target, "Other")
        target["options"].append({"label": "정규직", "value": "duplicate"})
        with self.assertRaises(ValueError):
            control_value(target, "정규직")

    def test_editor_boundary(self):
        self.assertTrue(resume_editor("wanted", "https://www.wanted.co.kr/cv/fixture"))
        self.assertTrue(
            resume_editor("catch", "https://www.catch.co.kr/Member/Resume/fixture")
        )
        self.assertTrue(
            resume_editor("jobkorea", "https://www.jobkorea.co.kr/User/Resume/Edit")
        )
        for site, path in [
            ("wanted", "/cv/list"),
            ("catch", "/Member/ResumeList"),
            ("saramin", "/zf_user/resume/resume-manage"),
            ("wanted", "/jobs/apply"),
            ("incruit", "/login"),
        ]:
            self.assertFalse(resume_editor(site, "https://example.test" + path))

    def test_worker_one_loop_and_cleanup(self):
        class Engine:
            async def open(self, payload):
                return id(asyncio.get_running_loop())

            async def close(self):
                self.closed = True

        engine = Engine()
        worker = SyncWorker(engine)
        self.assertEqual(worker.call("open", {}), worker.call("open", {}))
        worker.close()
        self.assertTrue(engine.closed)
        self.assertFalse(worker.thread.is_alive())


if __name__ == "__main__":
    unittest.main()
