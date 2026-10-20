"""Google Sheet export: owner's Apps Script URL only, token in body, no other hosts."""

import json
import os
import unittest
from unittest.mock import patch

import httpx

from job_agent.alerts.sheet import SheetExporter, sheet_rows

URL = "https://script.google.com/macros/s/AKfy-fixture_ID/exec"
ENV = {"ALERT_SHEET_URL": URL, "ALERT_SHEET_TOKEN": "t" * 32}
JOB = {
    "site": "wanted",
    "company": "가상기업",
    "role": "데이터 분석가",
    "url": "https://www.wanted.co.kr/wd/1",
    "period": "~ 2026-11-30",
    "status_check": {
        "job_location": "서울 강남구",
        "experience": {"evidence": "경력 1~5년"},
        "checked_at": "2026-10-21T08:00:00",
    },
    "requirements_check": {"application_confirmed": False},
}


class SheetTests(unittest.TestCase):
    def test_configured_only_for_an_apps_script_web_app_and_long_token(self):
        with patch.dict(os.environ, ENV):
            self.assertTrue(SheetExporter().configured())
        for changes in [
            {"ALERT_SHEET_URL": "https://example.com/macros/s/x/exec"},
            {"ALERT_SHEET_URL": "http://script.google.com/macros/s/x/exec"},
            {"ALERT_SHEET_TOKEN": "short"},
            {"ALERT_SHEET_URL": ""},
        ]:
            with self.subTest(changes=changes), patch.dict(os.environ, {**ENV, **changes}):
                self.assertFalse(SheetExporter().configured())

    def test_rows_carry_the_fields_people_compare(self):
        row = sheet_rows("분석 알림", [JOB], {JOB["url"]}, "2026-10-21")[0]
        self.assertEqual(row["platform"], "원티드")
        self.assertEqual(row["location"], "서울 강남구")
        self.assertEqual(row["experience"], "경력 1~5년")
        self.assertEqual(row["apply_button"], "미확인")
        self.assertEqual(row["mailed"], "2026-10-21")
        self.assertEqual(sheet_rows("a", [JOB], set(), "2026-10-21")[0]["mailed"], "")

    def test_post_follows_only_the_apps_script_result_redirect(self):
        seen = []

        def handle(request):
            seen.append((request.method, str(request.url), request.content))
            if request.url.host == "script.google.com":
                return httpx.Response(
                    302,
                    headers={"location": "https://script.googleusercontent.com/macros/echo?user_content_key=k"},
                )
            return httpx.Response(200, json={"ok": True, "added": 1, "updated": 0})

        exporter = SheetExporter(URL, "t" * 32, httpx.Client(transport=httpx.MockTransport(handle)))
        self.assertEqual(exporter.export([{"url": "u"}])["added"], 1)
        body = json.loads(seen[0][2])
        self.assertEqual(body["token"], "t" * 32)
        self.assertEqual(seen[1][0], "GET")

        def elsewhere(request):
            return httpx.Response(302, headers={"location": "https://evil.example/collect"})

        exporter = SheetExporter(URL, "t" * 32, httpx.Client(transport=httpx.MockTransport(elsewhere)))
        with self.assertRaises(ValueError):
            exporter.export([{"url": "u"}])

        def refused(request):
            if request.url.host == "script.google.com":
                return httpx.Response(200, json={"ok": False, "error": "token"})
            raise AssertionError("unexpected request")

        exporter = SheetExporter(URL, "t" * 32, httpx.Client(transport=httpx.MockTransport(refused)))
        with self.assertRaises(ValueError):
            exporter.export([{"url": "u"}])


if __name__ == "__main__":
    unittest.main()
