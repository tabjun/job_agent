"""Current detail evidence, timezone boundaries, and public URL restrictions."""

import json
import unittest
from datetime import datetime
from unittest.mock import patch

import httpx

from job_agent.core.job_status import detail_status, detail_url, verify_posting
from job_agent.core.postings import rejection

URL = "https://www.jobkorea.co.kr/Recruit/GI_Read/123"
NOW = datetime(2026, 10, 20, 9)


def schema(**fields):
    return (
        '<script type="application/ld+json">'
        + json.dumps(
            {
                "@context": "https://schema.org",
                "@type": "JobPosting",
                **fields,
            }
        )
        + "</script>"
    )


class PostingStatusTests(unittest.TestCase):
    def test_header_recommendation_does_not_hide_actual_job_conditions(self):
        html = (
            "<head><title>검색 포털</title></head><nav>AI 추천 공고</nav>"
            + schema(
                title="데이터 분석가",
                validThrough="2099-11-30",
                hiringOrganization={"name": "가상기업"},
                jobLocation={"address": {"addressRegion": "서울"}},
            )
            + "<h1>데이터 분석가</h1><p>지원자격 경력 3년 이상 SQL 활용 우대사항 없음</p><button>지원하기</button>"
        )
        row = detail_status(html, URL, NOW)
        self.assertEqual(row["status"], "open")
        self.assertIn("SQL", row["job_description"])
        self.assertEqual(row["experience"]["min_years"], 3)
        self.assertTrue(row["application_available"])
        self.assertEqual(row["job_location"], "서울")
        blocked = detail_status(html.replace("<button>", "<button disabled>"), URL, NOW)
        self.assertFalse(blocked["application_available"])
        self.assertTrue(blocked["application_blocked"])

    def test_expired_structured_date_wins_over_generic_ongoing_text(self):
        # Date shape observed on the reported employer's public July posting.
        html = schema(validThrough="2026-07-17T13:00", datePosted="2026-07-03")
        self.assertEqual(
            detail_status(html + "<p>채용 시 마감</p>", URL, NOW)["status"], "closed"
        )

    def test_old_publication_and_future_deadline_is_open(self):
        html = schema(validThrough="2026-11-30", datePosted="2026-07-03")
        self.assertEqual(detail_status(html, URL, NOW)["status"], "open")

    def test_current_closed_text_wins_over_future_schema(self):
        html = schema(validThrough="2026-11-30") + "<p>마감되었습니다.</p>"
        self.assertEqual(detail_status(html, URL, NOW)["status"], "closed")

    def test_missing_or_invalid_status_never_becomes_open(self):
        for html in [
            "<p>로그인 필요</p>",
            schema(datePosted="2026-07-03"),
            schema(validThrough="2026-02-30"),
            "<p>마감일 07/17</p>",
            '<script>var message = "채용 시 마감"</script>',
        ]:
            with self.subTest(html=html):
                self.assertEqual(detail_status(html, URL, NOW)["status"], "unknown")

    def test_kst_timestamp_and_date_only_boundaries(self):
        for expiry, status in [
            ("2026-10-20T08:59:59+09:00", "closed"),
            ("2026-10-19T23:59:59Z", "closed"),
            ("2026-10-20T00:01:00Z", "open"),
            ("2026-10-20", "open"),
            ("2026-10-20T10:00", "open"),
        ]:
            self.assertEqual(
                detail_status(schema(validThrough=expiry), URL, NOW)["status"], status
            )
        for text in [
            "마감일 2026.10.20(화) 08시 00분",
            "접수기간 2026.07.03 ~ 2026.10.20 08:00",
        ]:
            self.assertEqual(
                detail_status("<p>" + text + "</p>", URL, NOW)["status"], "closed"
            )

    def test_visible_labeled_dates_and_ranges(self):
        for text, status in [
            ("마감일 : 2026년 7월 17일", "closed"),
            ("접수기간 2026.07.03(금) ~ 07.17(금)", "closed"),
            ("접수기간 2026.12.20 ~ 01.03", "unknown"),
            ("접수 마감일: 2026/11/30", "open"),
            ("마감일 상시 채용", "open"),
            ("사이트 메뉴 상시 채용", "unknown"),
            ("등록일 2026.07.03", "unknown"),
            ("마감일은 변경될 수 있습니다", "unknown"),
        ]:
            with self.subTest(text=text):
                self.assertEqual(
                    detail_status("<p>" + text + "</p>", URL, NOW)["status"], status
                )
        self.assertEqual(
            detail_status(
                "<p>접수기간 2025.12.20 ~ 01.03</p>", URL, datetime(2026, 1, 1)
            )["status"],
            "open",
        )

    def test_recommended_jobs_cannot_confirm_unknown_main_posting(self):
        html = "<h1>SQL</h1><h2>추천 공고</h2><p>마감일 2026.11.30</p>"
        self.assertEqual(detail_status(html, URL, NOW)["status"], "unknown")
        html = schema(
            url="https://www.jobkorea.co.kr/Recruit/GI_Read/999",
            validThrough="2026-11-30",
        )
        self.assertEqual(detail_status(html, URL, NOW)["status"], "unknown")
        html = "<h1>SQL</h1><p>본문</p><div>추천 공고</div><p>마감일 2026.11.30</p>"
        self.assertEqual(detail_status(html, URL, NOW)["status"], "unknown")

    def test_closed_text_outside_the_title_section_still_wins(self):
        html = "<div>마감된 공고입니다</div><h1>SQL 분석가</h1><p>마감일 2026.11.30</p>"
        self.assertEqual(detail_status(html, URL, NOW)["status"], "closed")
        # The schema title may only appear in the meta description.
        html = (
            '<meta name="description" content="SQL 분석가 모집">'
            + schema(url=URL, title="SQL 분석가", validThrough="2026-11-30")
            + "<p>채용이 마감되었습니다</p>"
        )
        self.assertEqual(detail_status(html, URL, NOW)["status"], "closed")

    def test_platform_apply_labels_share_one_pattern(self):
        page = "<h1>데이터 분석가</h1><p>마감일 2026.11.30</p>"
        for label in ["바로지원", "인크루트 지원", "즉시 지원", "입사지원", "홈페이지 지원"]:
            with self.subTest(label=label):
                row = detail_status(page + f"<button>{label}</button>", URL, NOW)
                self.assertTrue(row["application_available"])
        for label in ["지원자 통계 보기", "식대지원", "입사지원 현황"]:
            with self.subTest(label=label):
                row = detail_status(page + f"<a>{label}</a>", URL, NOW)
                self.assertFalse(row["application_available"])

    def test_recommended_posting_buttons_are_not_this_postings_apply_path(self):
        html = (
            "<h1>데이터 분석가</h1><p>마감일 2026.11.30</p>"
            "<h2>추천 공고</h2><p>다른 공고</p><button>지원하기</button>"
        )
        self.assertFalse(detail_status(html, URL, NOW)["application_available"])

    def test_wanted_embedded_page_data_supplies_status_and_conditions(self):
        wanted = "https://www.wanted.co.kr/wd/376628"

        def page(**fields):
            data = {
                "id": 376628,
                "status": "active",
                "due_time": None,
                "hidden": False,
                "position": "[Data팀] Data Analyst",
                "company": {"company_name": "가상기업"},
                "career": {"annual_from": 1, "annual_to": 5, "is_newbie": False},
                "address": {
                    "location": "서울",
                    "district": "강남구",
                    "full_location": "서울 강남구 테헤란로",
                },
                **fields,
            }
            script = json.dumps({"props": {"pageProps": {"initialData": data}}})
            return (
                f'<script id="__NEXT_DATA__" type="application/json">{script}</script>'
                "<h1>[Data팀] Data Analyst</h1><p>주요업무 SQL</p>"
            )

        row = detail_status(page(), wanted, NOW)
        self.assertEqual(row["status"], "open")
        self.assertEqual(row["evidence"], "wanted_active")
        self.assertIn("서울 강남구", row["job_location"])
        self.assertEqual(
            (row["experience"]["min_years"], row["experience"]["max_years"]), (1, 5)
        )
        self.assertEqual(row["company"], "가상기업")
        row = detail_status(page(due_time="2026-11-30"), wanted, NOW)
        self.assertEqual((row["status"], row["deadline"]), ("open", "2026-11-30"))
        for fields in [{"status": "close"}, {"due_time": "2026-10-01"}]:
            with self.subTest(fields=fields):
                self.assertEqual(
                    detail_status(page(**fields), wanted, NOW)["status"], "closed"
                )
        entry = detail_status(
            page(career={"annual_from": 0, "annual_to": 0, "is_newbie": True}),
            wanted,
            NOW,
        )
        self.assertEqual(entry["experience"]["kind"], "entry")
        # Another posting's data never confirms this one.
        other = detail_status(page(id=1), wanted, NOW)
        self.assertNotEqual(other.get("evidence"), "wanted_active")

    def test_bracketed_experience_is_read_even_with_a_requirements_section(self):
        for body in [
            "<h1>데이터 분석가</h1><p>경력(3년 이상)</p><p>마감일 2026.11.30</p>",
            "<h1>데이터 분석가</h1><p>자격요건 SQL 활용 우대사항 없음</p>"
            "<p>경력(3년 이상)</p><p>마감일 2026.11.30</p>",
        ]:
            with self.subTest(body=body):
                row = detail_status(body, URL, NOW)
                self.assertEqual(row["experience"]["min_years"], 3)

    def test_catch_uses_its_own_schema_and_cuts_viewed_together_widgets(self):
        catch = "https://www.catch.co.kr/NCS/RecruitInfoDetails/560629"
        html = (
            schema(
                title="[골프존] 데이터 사이언티스트 채용",
                validThrough="2026-11-29T23:59:59+09:00",
                experienceRequirements=["경력"],
                description="[지원자격]\n경력 : 경력(2년 이상)\n근무지 : 서울 강남구",
            )
            + "<h1>[골프존] 데이터 사이언티스트 채용</h1><p>~ 11.29(일) 24시</p>"
            "<div>방금 본 공고와 비슷한 공고</div><p>다른기업 경력 10년 이상</p>"
            "<button>지원하기</button>"
            "<div>다른 회원이 함께 본 공고!</div><p>마감되었습니다</p>"
        )
        row = detail_status(html, catch, NOW)
        self.assertEqual(row["status"], "open")
        self.assertEqual(row["experience"]["min_years"], 2)
        self.assertFalse(row["application_available"])

    def test_rate_limited_pages_are_reported_as_such(self):
        original = httpx.Client
        for response in [
            httpx.Response(429),
            httpx.Response(
                200,
                headers={"content-type": "text/html"},
                text="<title>Access denied</title><p>Error 1015</p><p>You are being rate limited</p>",
            ),
        ]:
            with patch(
                "job_agent.core.job_status.httpx.Client",
                side_effect=lambda response=response, **kw: original(
                    transport=httpx.MockTransport(lambda _: response), **kw
                ),
            ):
                self.assertEqual(
                    verify_posting(URL, NOW),
                    {"status": "unknown", "evidence": "rate_limited"},
                )

    def test_same_posting_redirect_is_followed_once(self):
        requests = []
        target = "https://www.catch.co.kr/NCS/RecruitInfoDetails/123"

        def handle(request):
            requests.append(str(request.url))
            if "lang=ko" not in str(request.url):
                return httpx.Response(302, headers={"location": target + "?lang=ko"})
            return httpx.Response(
                200,
                headers={"content-type": "text/html"},
                text="<h1>데이터 분석가</h1><p>마감일 : 2026-11-30</p>",
            )

        original = httpx.Client
        with patch(
            "job_agent.core.job_status.httpx.Client",
            side_effect=lambda **kw: original(
                transport=httpx.MockTransport(handle), **kw
            ),
        ):
            self.assertEqual(verify_posting(target, NOW)["status"], "open")
        self.assertEqual(requests, [target, target + "?lang=ko"])

    def test_shared_rejection_normalizes_structured_deadlines(self):
        for key, value in [
            ("deadline", "2026.07.17"),
            ("end_date", "2026/07/17"),
            ("validThrough", "2026-07-17T13:00"),
            ("content", "접수기간: 2026년 7월 3일 ~ 2026년 7월 17일"),
        ]:
            row = {"url": URL, "title": "데이터", key: value}
            self.assertEqual(rejection(row, "jobkorea.co.kr", NOW.date()), "closed")
        self.assertEqual(
            rejection(
                {"url": URL, "content": "접수 마감일 2026.11.30"},
                "jobkorea.co.kr",
                NOW.date(),
            ),
            "",
        )

    def test_fetch_is_bounded_and_redirects_do_not_leave_the_posting(self):
        requests = []

        def handle(request):
            requests.append(request)
            return httpx.Response(
                302,
                headers={
                    "location": "http://127.0.0.1/private",
                    "set-cookie": "id=secret",
                },
            )

        original = httpx.Client
        with patch(
            "job_agent.core.job_status.httpx.Client",
            side_effect=lambda **kw: original(
                transport=httpx.MockTransport(handle),
                **kw,
            ),
        ):
            self.assertEqual(verify_posting(URL, NOW)["status"], "unknown")
        self.assertEqual(len(requests), 1)
        self.assertNotIn("cookie", requests[0].headers)
        for url in [
            "http://localhost/a",
            "https://www.jobkorea.co.kr/Search/",
            "https://evil.jobkorea.co.kr/Recruit/GI_Read/123",
            "https://www.wanted.co.kr/company/1",
        ]:
            self.assertEqual(detail_url(url), "")

    def test_fetch_handles_removed_blocked_oversized_and_valid_detail(self):
        original = httpx.Client
        for response, status in [
            (httpx.Response(404), "closed"),
            (httpx.Response(403), "unknown"),
            (
                httpx.Response(
                    200, text="x" * 3_000_001, headers={"content-type": "text/html"}
                ),
                "unknown",
            ),
            (
                httpx.Response(
                    200,
                    text=schema(validThrough="2026-11-30"),
                    headers={"content-type": "text/html"},
                ),
                "open",
            ),
        ]:
            with patch(
                "job_agent.core.job_status.httpx.Client",
                side_effect=lambda response=response, **kw: original(
                    transport=httpx.MockTransport(lambda _: response),
                    **kw,
                ),
            ):
                self.assertEqual(verify_posting(URL, NOW)["status"], status)


if __name__ == "__main__":
    unittest.main()
