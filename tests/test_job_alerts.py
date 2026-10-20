import json
import os
import re
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, patch
from urllib.error import HTTPError

import test_sharing
import test_ui

from job_agent.alerts.service import (
    JobAlerts,
    allowed_regions,
    latest_slot,
    matches,
    next_slot,
    region_check,
)
from job_agent.core.paths import ProjectPaths


class FakeMailer:
    def __init__(self):
        self.sent = []
        self.fail = False
        self.html = []

    def configured(self):
        return True

    def send(self, to, subject, text, html=None):
        if self.fail:
            raise OSError("smtp down")
        self.sent.append((to, subject, text))
        self.html.append(html)


def code_from(mailer):
    return re.search(r"인증 코드: (\d{6})", mailer.sent[-1][2]).group(1)


RULE = {
    "role": "데이터 분석가",
    "location": "서울",
    "keywords": "Python, SQL",
    "exclude": "인턴",
    "require_keywords": True,
}


class JobAlertTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.mailer = FakeMailer()
        self.searcher = Mock(return_value=[])
        self.confirmed = {
            "status": "open",
            "evidence": "fixture",
            "job_location": "서울",
            "job_title": "데이터 분석가",
            "application_available": True,
            "experience": {"kind": "any"},
        }
        self.verifier = Mock(return_value=self.confirmed)
        self.now = datetime(2026, 10, 12, 9, 0)  # Monday
        self.alerts = JobAlerts(
            ProjectPaths(Path(self.folder.name)),
            self.searcher,
            self.mailer,
            clock=lambda: self.now,
            verifier=self.verifier,
        )
        self.env = patch.dict(os.environ, {"TAVILY_API_KEY": "fixture"})
        self.env.start()

    def tearDown(self):
        self.env.stop()
        self.folder.cleanup()

    def verify(self, email="me@example.com"):
        self.alerts.request_code({"email": email})
        return self.alerts.verify({"email": email, "code": code_from(self.mailer)})

    def save(self, target=None, **extra):
        return (target or self.alerts).save(
            {
                "email": "me@example.com",
                "name": "분석",
                "platforms": {"wanted": RULE, "saramin": {**RULE, "keywords": "SQL"}},
                "schedule": {"frequency": "weekdays", "hour": 8},
                "search_consent": True,
                **extra,
            }
        )

    def test_code_verification_rate_limit_and_attempts(self):
        with self.assertRaises(ValueError):
            self.alerts.request_code({"email": "not-an-email"})
        self.alerts.request_code({"email": "Me@Example.com"})
        to, subject, _ = self.mailer.sent[0]
        self.assertEqual(to, "me@example.com")
        self.assertIn("인증 코드", subject)
        stored = self.alerts.file.read_text(encoding="utf-8")
        self.assertNotIn(code_from(self.mailer), stored)
        with self.assertRaisesRegex(ValueError, "1분"):
            self.alerts.request_code({"email": "me@example.com"})
        code = code_from(self.mailer)
        wrong = "000000" if code != "000000" else "111111"
        for _ in range(4):
            with self.assertRaisesRegex(ValueError, "일치하지"):
                self.alerts.verify({"email": "me@example.com", "code": wrong})
        with self.assertRaisesRegex(ValueError, "시도 횟수"):
            self.alerts.verify({"email": "me@example.com", "code": wrong})
        with self.assertRaisesRegex(ValueError, "만료"):
            self.alerts.verify({"email": "me@example.com", "code": code})
        self.assertEqual(self.alerts.status()["emails"], [])

    def test_save_requires_verified_email_consent_and_conditions(self):
        with self.assertRaisesRegex(ValueError, "이메일 인증"):
            self.save()
        self.verify()
        with self.assertRaisesRegex(ValueError, "동의"):
            self.save(search_consent=False)
        with self.assertRaisesRegex(ValueError, "직무 또는 키워드"):
            self.save(platforms={"wanted": {"role": "", "keywords": ""}})
        with self.assertRaises(ValueError):
            self.save(platforms={"linkedin": RULE})
        with self.assertRaises(ValueError):
            self.save(schedule={"frequency": "hourly", "hour": 8})
        with (
            patch.dict(os.environ, {"TAVILY_API_KEY": ""}),
            self.assertRaisesRegex(ValueError, "TAVILY"),
        ):
            self.save()
        status = self.save()
        alert = status["alerts"][0]
        self.assertEqual(set(alert["platforms"]), {"wanted", "saramin"})
        self.assertEqual(alert["next_run"], "2026-10-13T08:00")
        self.assertNotIn("sent_urls", alert)
        updated = self.save(id=alert["id"], name="수정")
        self.assertEqual(len(updated["alerts"]), 1)
        self.assertEqual(updated["alerts"][0]["name"], "수정")

    def test_per_platform_search_filters_and_no_resend(self):
        self.verify()
        alert_id = self.save()["alerts"][0]["id"]
        results = {
            "wanted.co.kr": [
                {
                    "title": "데이터 분석가 Python SQL",
                    "url": "https://www.wanted.co.kr/wd/1",
                    "content": "서울",
                },
                {
                    "title": "데이터 분석 인턴 Python",
                    "url": "https://www.wanted.co.kr/wd/2",
                    "content": "",
                },
                {
                    "title": "마케터",
                    "url": "https://www.wanted.co.kr/wd/3",
                    "content": "영업",
                },
                {
                    "title": "Python 외부",
                    "url": "https://evil.example/wd/4",
                    "content": "",
                },
            ],
            "saramin.co.kr": [
                {
                    "title": "SQL 분석",
                    "url": "https://www.saramin.co.kr/a",
                    "content": "",
                },
                {
                    "title": "데이터 분석 채용정보 | 총 348건의 검색결과 - 사람인",
                    "url": "https://www.saramin.co.kr/list",
                    "content": "Python SQL",
                },
                {
                    "title": "SQL  분석",
                    "url": "https://www.saramin.co.kr/a?copy=1",
                    "content": "",
                },
                {
                    "title": "중복",
                    "url": "https://www.wanted.co.kr/wd/1",
                    "content": "SQL",
                },
            ],
        }
        self.searcher.side_effect = lambda query, domains: results[domains[0]]
        result = self.alerts.run_now({"id": alert_id})
        queries = [call.args for call in self.searcher.call_args_list]
        self.assertIn(("데이터 분석가 서울 채용", ["wanted.co.kr"]), queries)
        self.assertEqual(
            [job["url"] for job in result["jobs"]],
            [
                "https://www.wanted.co.kr/wd/1",
                "https://www.saramin.co.kr/a",
                "https://www.saramin.co.kr/a?copy=1",
            ],
        )
        self.assertTrue(result["mailed"])
        _, subject, text = self.mailer.sent[-1]
        self.assertIn("새 공고 3건", subject)
        self.assertIn("원티드", text)
        self.assertIn("회사명 | 직무 | 공고 기간", text)
        self.assertIn("<table", self.mailer.html[-1])
        self.assertIn("원문에서 확인", text)
        again = self.alerts.run_now({"id": alert_id})
        self.assertFalse(again["mailed"])
        self.assertIn("새 공고 없음", again["status"])
        self.assertEqual(len(self.mailer.sent), 2)  # code + one alert mail

    def test_same_title_different_employers_and_requisitions_are_not_hidden(self):
        self.verify()
        alert_id = self.save(platforms={"wanted": RULE})["alerts"][0]["id"]
        self.searcher.return_value = [
            {
                "title": "데이터 분석가 Python SQL",
                "company_name": company,
                "url": f"https://www.wanted.co.kr/wd/{index}",
                "content": "서울",
            }
            for index, company in enumerate(
                ("가상기업 A", "가상기업 B", "가상기업 A"), 1
            )
        ]
        result = self.alerts.run_now({"id": alert_id})
        self.assertEqual(len(result["jobs"]), 3)
        self.assertFalse(self.alerts.run_now({"id": alert_id})["mailed"])
        self.searcher.return_value.append(
            {
                "title": "데이터 분석가 Python SQL",
                "company_name": "가상기업 C",
                "url": "https://www.wanted.co.kr/wd/4",
                "content": "서울",
            }
        )
        later = self.alerts.run_now({"id": alert_id})
        self.assertEqual([job["company"] for job in later["jobs"]], ["가상기업 C"])

    def test_mail_contains_only_currently_confirmed_open_details(self):
        self.verify()
        alert_id = self.save(platforms={"wanted": RULE})["alerts"][0]["id"]
        self.searcher.return_value = [
            {
                "title": "SQL 분석",
                "url": f"https://www.wanted.co.kr/wd/{i}",
                "content": "서울",
            }
            for i in range(1, 5)
        ]

        def check(url, now):
            return {
                **self.confirmed,
                "status": {"1": "closed", "2": "unknown", "3": "open"}.get(
                    url.rsplit("/", 1)[1]
                ),
                "deadline": "2026-11-30",
            }

        self.verifier.side_effect = check
        before = len(self.mailer.sent)
        result = self.alerts.run_now({"id": alert_id})
        self.assertEqual(
            [j["url"] for j in result["jobs"]], ["https://www.wanted.co.kr/wd/3"]
        )
        self.assertEqual(len(self.mailer.sent), before + 1)
        self.assertIn("2026-11-30", self.mailer.sent[-1][2])
        self.assertEqual(result["collection"]["detail_closed"], 1)
        self.assertEqual(result["collection"]["status_unverified"], 2)
        self.verifier.side_effect = TimeoutError("unreadable")
        again = self.alerts.run_now({"id": alert_id})
        self.assertFalse(again["mailed"])
        self.assertIn("보류", again["status"])
        self.assertEqual(self.alerts.status()["alerts"][0]["sent_count"], 1)

    def test_preview_explains_collection_limit_and_keyword_rejections(self):
        self.verify()
        alert_id = self.save(platforms={"wanted": RULE}, max_results=1)["alerts"][0][
            "id"
        ]
        self.searcher.return_value = [
            {
                "title": "[가상기업 A] 분석가 SQL",
                "url": "https://www.wanted.co.kr/wd/11",
                "content": "서울",
            },
            {
                "title": "[가상기업 B] 분석가 Python",
                "url": "https://www.wanted.co.kr/wd/12",
                "content": "서울",
            },
            {
                "title": "[가상기업 C] 분석가",
                "url": "https://www.wanted.co.kr/wd/13",
                "content": "서울",
            },
        ]
        result = self.alerts.run_now({"id": alert_id, "send": False})
        self.assertEqual(result["collection"]["fetched"], 3)
        self.assertEqual(result["collection"]["eligible"], 2)
        self.assertEqual(result["collection"]["selected"], 1)
        self.assertEqual(result["collection"]["missing_keyword_evidence"], 1)
        self.assertFalse(result["mailed"])
        self.assertEqual(len(self.mailer.sent), 1)  # verification only

    def test_open_posting_without_apply_button_is_mailed_with_label(self):
        self.verify()
        alert_id = self.save(platforms={"wanted": RULE})["alerts"][0]["id"]
        self.searcher.return_value = [
            {
                "title": "데이터 분석가 SQL",
                "url": "https://www.wanted.co.kr/wd/21",
                "content": "서울",
            }
        ]
        self.verifier.return_value = {
            **self.confirmed,
            "application_available": False,
            "deadline": "2026-11-30",
        }
        result = self.alerts.run_now({"id": alert_id})
        self.assertTrue(result["mailed"])
        self.assertEqual(result["collection"]["application_unconfirmed"], 1)
        self.assertIn("지원 버튼 미확인", self.mailer.sent[-1][2])
        self.assertIn("지원 버튼 미확인", self.mailer.html[-1])

    def test_detail_budget_skips_unsupported_urls_and_checks_likely_jobs_first(self):
        from job_agent.core.job_status import detail_url

        self.verify()
        alerts = JobAlerts(
            ProjectPaths(Path(self.folder.name)),
            self.searcher,
            self.mailer,
            clock=lambda: self.now,
            verifier=self.verifier,
            supported=detail_url,
        )
        alert_id = self.save(
            target=alerts, platforms={"catch": {**RULE, "keywords": ""}}
        )["alerts"][0]["id"]
        self.searcher.return_value = [
            {
                "title": "카페 행사 데이터 분석",
                "url": "https://www.catch.co.kr/CatchCafe/LiveFair/1",
                "content": "서울",
            },
            {
                "title": "보험 영업 채용",
                "url": "https://www.catch.co.kr/NCS/RecruitInfoDetails/2",
                "content": "서울",
            },
            {
                "title": "데이터 분석가",
                "url": "https://www.catch.co.kr/NCS/RecruitInfoDetails/3",
                "content": "서울",
            },
        ]
        with patch.object(JobAlerts, "DETAIL_BUDGET", 1):
            result = alerts.run_now({"id": alert_id, "send": False})
        checked = [call.args[0] for call in self.verifier.call_args_list]
        self.assertEqual(checked, ["https://www.catch.co.kr/NCS/RecruitInfoDetails/3"])
        self.assertEqual(result["collection"]["unsupported_detail_url"], 1)
        self.assertEqual(result["collection"]["detail_not_checked"], 1)
        trace = json.loads(
            (Path(self.folder.name) / "result/job_alerts/runs" / f"{alert_id}.json")
            .read_text(encoding="utf-8")
        )
        outcomes = {row["url"].rsplit("/", 1)[1]: row["outcome"] for row in trace["candidates"]}
        self.assertEqual(
            outcomes,
            {"1": "unsupported_detail_url", "2": "detail_not_checked", "3": "selected"},
        )
        stored = json.loads(
            (Path(self.folder.name) / "result/job_alerts/alerts.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertNotIn("candidates", json.dumps(stored))

    def test_full_text_keyword_evidence_survives_short_summary(self):
        self.verify()
        alert_id = self.save(platforms={"wanted": RULE})["alerts"][0]["id"]
        self.searcher.return_value = [
            {
                "title": "[가상기업] 데이터 분석가",
                "url": "https://www.wanted.co.kr/wd/14",
                "content": "요약에 기술 없음",
                "raw_content": "설명 " * 1000 + "서울 SQL",
            }
        ]
        result = self.alerts.run_now({"id": alert_id, "send": False})
        self.assertEqual(len(result["jobs"]), 1)
        self.assertEqual(result["jobs"][0]["matched_keywords"], ["sql"])

    def test_preview_and_mail_failure_do_not_mark_sent(self):
        self.verify()
        alert_id = self.save()["alerts"][0]["id"]
        self.searcher.return_value = [
            {
                "title": "Python SQL",
                "url": "https://www.wanted.co.kr/wd/9",
                "content": "",
            }
        ]
        preview = self.alerts.run_now({"id": alert_id, "send": False})
        self.assertEqual(len(preview["jobs"]), 1)
        self.assertNotIn("last_run_at", self.alerts.status()["alerts"][0])
        self.mailer.fail = True
        failed = self.alerts.run_now({"id": alert_id})
        self.assertIn("메일 발송 실패", failed["status"])
        self.assertEqual(self.alerts.status()["alerts"][0]["sent_count"], 0)
        self.mailer.fail = False
        self.assertTrue(self.alerts.run_now({"id": alert_id})["mailed"])

    def test_deadline_that_passed_during_collection_is_not_mailed(self):
        self.verify()
        alert_id = self.save(platforms={"wanted": RULE})["alerts"][0]["id"]
        self.searcher.return_value = [
            {
                "title": "SQL",
                "url": "https://www.wanted.co.kr/wd/55",
                "content": "서울",
            }
        ]
        self.verifier.return_value = {
            **self.confirmed,
            "status": "open",
            "deadline": "2026-10-12T08:59:59+09:00",
        }
        result = self.alerts.run_now({"id": alert_id})
        self.assertFalse(result["mailed"])
        self.assertEqual(result["collection"]["closed_before_send"], 1)
        self.assertEqual(len(self.mailer.sent), 1)  # verification code only

    def test_due_schedule_catches_up_once(self):
        weekdays = {"frequency": "weekdays", "hour": 8}
        saturday = datetime(2026, 10, 17, 12, 0)
        self.assertEqual(latest_slot(weekdays, saturday), datetime(2026, 10, 16, 8))
        self.assertEqual(next_slot(weekdays, saturday), datetime(2026, 10, 19, 8))
        weekly = {"frequency": "weekly", "hour": 21, "weekday": 2}
        self.assertEqual(next_slot(weekly, self.now), datetime(2026, 10, 14, 21))
        self.verify()
        self.save()
        self.assertEqual(self.alerts.due(datetime(2026, 10, 12, 23, 0)), [])
        self.assertEqual(len(self.alerts.due(datetime(2026, 10, 13, 8, 30))), 1)
        self.now = datetime(2026, 10, 15, 10, 0)  # PC was off two days
        with patch.object(self.alerts.mailer, "configured", return_value=True):
            ran = self.alerts.run_due()
        self.assertEqual(len(ran), 1)
        self.assertEqual(self.alerts.due(datetime(2026, 10, 15, 23, 0)), [])

    def other_process(self):
        return JobAlerts(
            ProjectPaths(Path(self.folder.name)),
            self.searcher,
            self.mailer,
            clock=lambda: self.now,
            verifier=self.verifier,
        )

    def test_changes_during_search_are_honoured_before_mailing(self):
        self.verify()
        alert_id = self.save()["alerts"][0]["id"]
        hit = [
            {"title": "Python", "url": "https://www.wanted.co.kr/wd/7", "content": ""}
        ]
        ui = self.other_process()
        for change, expected in [
            (lambda: self.save(ui, id=alert_id, name="변경"), "설정이 바뀌어"),
            (lambda: ui.forget_email({"email": "me@example.com"}), "삭제되어"),
        ]:
            calls = []

            def search(query, domains, change=change, calls=calls):
                if not calls:
                    change()
                calls.append(query)
                return hit

            self.searcher.side_effect = search
            result = self.alerts.run_now({"id": alert_id})
            self.assertFalse(result["mailed"])
            self.assertIn(expected, result["status"])
        self.assertEqual(len(self.mailer.sent), 1)  # only the code mail
        self.assertEqual(ui.status()["alerts"], [])  # deletion was not undone

    def test_two_instances_keep_each_others_records(self):
        self.verify()
        alert_id = self.save()["alerts"][0]["id"]
        self.searcher.return_value = [
            {"title": "SQL", "url": "https://www.wanted.co.kr/wd/8", "content": ""}
        ]
        cli = self.other_process()
        self.assertTrue(cli.run_now({"id": alert_id})["mailed"])
        self.save(id=alert_id, name="UI 수정")
        stored = self.alerts.status()["alerts"][0]
        self.assertEqual(stored["sent_count"], 1)
        self.assertEqual(stored["name"], "UI 수정")
        self.assertFalse(cli.run_now({"id": alert_id})["mailed"])
        self.assertEqual(list(self.alerts.folder.glob("*.lock")), [])

    def test_short_english_keywords_match_whole_words(self):
        body = "ml엔지니어 r/python 통계 · mail html wordpress c++"
        for term, expected in [
            ("r", True),
            ("ml", True),
            ("ai", False),
            ("python", True),
            ("c++", True),
            ("통계", True),
            ("분석", False),
        ]:
            self.assertEqual(matches(term, body), expected, term)

    def test_region_keeps_seoul_gyeonggi_and_unknown_drops_others(self):
        allowed = allowed_regions("서울, 경기")
        for body, keep in [
            ("판교 테크노밸리 데이터 분석", True),
            ("서울 강남구 · 부산 지사 협업", True),
            ("부산광역시 해운대구 근무", False),
            ("대구 수성구", False),
            ("인천 송도", False),
            ("ai 대전환 시대의 데이터 분석가", True),
            ("근무지 미기재 데이터 분석", True),
        ]:
            self.assertEqual(region_check(body, allowed)[0], keep, body)
        self.verify()
        alert_id = self.save(
            platforms={"wanted": {**RULE, "location": "서울, 경기", "exclude": ""}}
        )["alerts"][0]["id"]
        self.searcher.return_value = [
            {
                "title": "Python 분석",
                "url": "https://www.wanted.co.kr/wd/21",
                "content": "성남시 분당구",
            },
            {
                "title": "Python 분석가",
                "url": "https://www.wanted.co.kr/wd/22",
                "content": "대전광역시",
            },
            {
                "title": "SQL 분석가",
                "url": "https://www.wanted.co.kr/wd/23",
                "content": "",
            },
        ]
        result = self.alerts.run_now({"id": alert_id})
        self.assertEqual([j["region"] for j in result["jobs"]], ["성남", ""])
        text = self.mailer.sent[-1][2]
        self.assertNotIn(
            "지역:", text
        )  # Keep filtering, omit verbose per-posting metadata.
        self.assertIn("원문 확인", text)

    def test_forget_email_removes_its_alerts(self):
        self.verify()
        self.save()
        status = self.alerts.forget_email({"email": "me@example.com"})
        self.assertEqual(status["removed"], "me@example.com")
        self.assertEqual(self.alerts.status()["alerts"], [])
        self.assertEqual(self.alerts.status()["emails"], [])


class AlertHttpTests(unittest.TestCase):
    setUp = test_ui.HttpTests.setUp
    tearDown = test_ui.HttpTests.tearDown
    request = test_ui.HttpTests.request
    remote_headers = test_sharing.RemoteHttpTests.remote_headers

    def test_alerts_api_is_local_owner_only(self):
        with self.assertRaises(HTTPError) as error:
            self.request("/api/alerts", **{"X-Session-Token": self.server.token})
        self.assertEqual(error.exception.code, 403)
        owner = {
            "X-Session-Token": self.server.token,
            "X-Admin-Token": self.server.admin_token,
        }
        with self.request("/api/alerts", **owner) as response:
            status = json.load(response)
        self.assertEqual(len(status["platforms"]), 5)
        with self.assertRaises(HTTPError) as error:
            self.request("/api/alerts", {"action": "nope"}, **owner)
        self.assertEqual(error.exception.code, 400)
        headers = self.remote_headers()
        with self.request(
            "/api/login", {"code": self.server.sharing.code}, **headers
        ) as response:
            cookie = response.headers["Set-Cookie"].split(";")[0]
        remote = {**headers, "Cookie": cookie, **owner}
        for payload in [None, {"action": "request_code", "email": "a@b.co"}]:
            with self.assertRaises(HTTPError) as error:
                self.request("/api/alerts", payload, **remote)
            self.assertEqual(error.exception.code, 403)


if __name__ == "__main__":
    unittest.main()
