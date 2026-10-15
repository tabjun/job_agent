"""Retrieval coverage and metadata regressions, without paid API calls."""

import unittest
from datetime import date
from unittest.mock import patch

from job_agent.core.postings import (
    canonical_url,
    diverse_jobs,
    posting_fields,
    queries,
    rejection,
)
from job_agent.ui.service import SITES, WorkspaceService


class SearchQualityTests(unittest.TestCase):
    def test_provider_budget_is_per_platform_and_full_text_is_requested(self):
        with (
            patch("job_agent.core.native_jobs.native_search", return_value=[]),
            patch("tavily.TavilyClient") as client,
        ):
            client.return_value.search.return_value = {"results": []}
            WorkspaceService._web_search("데이터 분석 채용", ["wanted.co.kr"])
        options = client.return_value.search.call_args.kwargs
        self.assertEqual(options["max_results"], 20)
        self.assertEqual(options["include_raw_content"], "markdown")
        self.assertEqual(options["search_depth"], "basic")

    def test_alternative_roles_are_searched_separately_without_anding_skills(self):
        plan = queries(
            "데이터 분석가, 데이터 사이언티스트, 머신러닝, 통계",
            "서울 경기",
            "Python SQL",
        )
        self.assertEqual(len(plan), 3)
        self.assertIn("데이터 사이언티스트 서울 경기 채용", plan)
        self.assertIn("통계", " ".join(plan))
        self.assertNotIn("Python SQL", " ".join(plan))
        self.assertNotIn("2026", " ".join(plan))

    def test_existing_space_joined_alert_role_and_region_preferences_expand(self):
        plan = queries(
            "데이터 분석 데이터 사이언티스트 머신러닝 AI",
            "서울, 경기, 판교",
            "Python R AI",
        )
        self.assertEqual(
            plan,
            ["데이터 분석 채용", "데이터 사이언티스트 채용", "머신러닝 OR AI 채용"],
        )

    def test_closed_text_and_full_year_deadline_from_live_shapes(self):
        row = {"url": "https://www.wanted.co.kr/wd/1", "title": "데이터 분석가"}
        for content in (
            "해당 공고는 마감된 공고입니다.",
            "공고는 마감되었습니다.",
            "마감일: 마감. 급여: 회사내규",
            "마감일:2025-04-23,",
        ):
            self.assertEqual(
                rejection(
                    {**row, "content": content}, "wanted.co.kr", date(2026, 10, 15)
                ),
                "closed",
            )
        self.assertEqual(
            posting_fields({"title": "[리니지W] 데이터 분석가 모집 - 엔씨 채용"})[
                "company"
            ],
            "엔씨",
        )

    def test_realistic_listing_and_sibling_service_noise_is_rejected(self):
        for url in (
            "https://www.saramin.co.kr/zf_user/jobs/list/job-category?cat_kewd=293",
            "https://www.jobkorea.co.kr/Search?stext=SQL",
            "https://jumpit.saramin.co.kr/position/123",
        ):
            domain = "jobkorea.co.kr" if "jobkorea" in url else "saramin.co.kr"
            self.assertTrue(rejection({"url": url, "title": "SQL 채용"}, domain))
        self.assertEqual(
            rejection(
                {
                    "url": "https://www.jobkorea.co.kr/Recruit/GI_Read/123",
                    "title": "SQL 분석가",
                },
                "jobkorea.co.kr",
            ),
            "",
        )

    def test_mobile_tracking_aliases_share_one_posting_identity(self):
        self.assertEqual(
            canonical_url(
                "https://m.catch.co.kr/NCS/RecruitInfoDetails/123?utm_source=test"
            ),
            canonical_url("https://www.catch.co.kr/NCS/RecruitInfoDetails/123"),
        )
        self.assertEqual(
            canonical_url("https://lab.incruit.com/jobs/2610080000076"),
            canonical_url(
                "https://m.incruit.com/jobdb_info/jobpost.asp?job=2610080000076&startno=46&page=1"
            ),
        )
        self.assertNotEqual(
            canonical_url("https://job.incruit.com/jobdb_info/jobpost.asp?job=1"),
            canonical_url("https://job.incruit.com/jobdb_info/jobpost.asp?job=2"),
        )

    def test_company_evidence_kept_and_department_is_not_invented_as_employer(self):
        row = {
            "title": "[AI CX사업부문] 데이터 분석가",
            "raw_content": "회사명: 가상기업 A\n담당업무: SQL 분석",
        }
        self.assertEqual(posting_fields(row)["company"], "가상기업 A")
        self.assertEqual(
            posting_fields({"title": row["title"]})["company"], "원문 확인"
        )
        self.assertEqual(
            posting_fields({**row, "hiringOrganization": {"name": "검증된 기업"}})[
                "company"
            ],
            "검증된 기업",
        )

    def test_only_explicit_past_deadlines_are_closed(self):
        row = {"url": "https://www.wanted.co.kr/wd/123", "title": "SQL 분석가"}
        self.assertEqual(
            rejection(
                {**row, "validThrough": "2026-10-01"},
                "wanted.co.kr",
                date(2026, 10, 15),
            ),
            "closed",
        )
        self.assertEqual(
            rejection({**row, "deadline": "10/01"}, "wanted.co.kr", date(2026, 10, 15)),
            "",
        )

    def test_small_mail_budget_prioritizes_different_known_companies(self):
        jobs = [
            {"site": "wanted", "company": company, "url": str(i)}
            for i, company in enumerate(("A", "A", "A", "B", "C"))
        ]
        self.assertEqual([j["company"] for j in diverse_jobs(jobs, 3)], ["A", "B", "C"])
        self.assertEqual(len(diverse_jobs(jobs, 5)), 5)

    def test_one_platform_failure_does_not_hide_other_results(self):
        def search(query, domains):
            if domains == ["catch.co.kr"]:
                raise TimeoutError("private provider message")
            return [
                {
                    "title": "[가상기업] SQL",
                    "url": "https://www.wanted.co.kr/wd/1",
                    "content": "SQL",
                }
            ]

        service = WorkspaceService(searcher=search, ephemeral=True)
        with patch.dict("os.environ", {"TAVILY_API_KEY": "fixture"}):
            result = service._search(
                {
                    "source": "web",
                    "role": "분석",
                    "sites": ["catch", "wanted"],
                    "search_consent": True,
                }
            )
        self.assertEqual(len(result["jobs"]), 1)
        self.assertEqual(result["coverage"]["platforms"][0]["error"], "TimeoutError")
        self.assertNotIn("private provider message", str(result))

    def test_five_platforms_do_not_share_one_twelve_result_budget(self):
        calls = []

        def search(query, domains):
            calls.append(domains)
            return [
                {
                    "title": f"[가상기업 {site}-{i}] 데이터 분석가",
                    "company_name": f"가상기업 {site}-{i}",
                    "url": f"https://{domain}/job/{i}",
                    "content": "서울 Python SQL",
                }
                for site, domain in SITES.items()
                if domain in domains
                for i in range(10)
            ][:12]

        service = WorkspaceService(searcher=search, ephemeral=True)
        with patch.dict("os.environ", {"TAVILY_API_KEY": "fixture"}):
            result = service._search(
                {
                    "source": "web",
                    "role": "데이터 분석가",
                    "sites": list(SITES),
                    "search_consent": True,
                }
            )
        self.assertEqual(len(result["jobs"]), 50)
        self.assertTrue(all(len(domains) == 1 for domains in calls))
        self.assertEqual(len({job["company"] for job in result["jobs"]}), 50)

    def test_short_english_terms_do_not_match_inside_other_words(self):
        service = WorkspaceService(ephemeral=True)
        result = service._search(
            {"postings": '[{"title":"email career 안내"}]', "keywords": "AI, R"}
        )
        self.assertEqual(result["jobs"][0]["matched_keywords"], [])


if __name__ == "__main__":
    unittest.main()
