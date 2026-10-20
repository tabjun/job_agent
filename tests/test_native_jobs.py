"""Public card layouts and provider fallback; no network or account sessions."""

import unittest
from unittest.mock import patch

import httpx

from job_agent.core.native_jobs import native_search, parse_cards
from job_agent.ui.service import WorkspaceService


class NativeJobTests(unittest.TestCase):
    def test_pagination_adds_distinct_postings_and_does_not_send_response_cookies(self):
        requests = []

        def handle(request):
            requests.append(request)
            page = request.url.params["Page_No"]
            return httpx.Response(
                200,
                text=f'<article><a href="/Recruit/GI_Read/{page}">데이터 분석가</a><a href="/Recruit/GI_Read/{page}">기업 {page}</a></article>',
                headers={"set-cookie": "session=discard"},
            )

        original = httpx.Client
        with patch(
            "job_agent.core.native_jobs.httpx.Client",
            side_effect=lambda **kw: original(
                transport=httpx.MockTransport(handle), **kw
            ),
        ):
            rows = native_search("데이터 분석", "jobkorea.co.kr")
        self.assertEqual(len(rows), 3)
        self.assertEqual([r["retrieval_page"] for r in rows], [1, 2, 3])
        self.assertTrue(all("cookie" not in r.headers for r in requests))

    def test_incruit_public_card_pairs_employer_and_role(self):
        html = '<ul class="c_row"><li><div><a class="cpname">가상기업</a></div><div class="cell_mid"><a href="https://job.incruit.com/jobdb_info/jobpost.asp?job=123">데이터 분석가</a><span>서울 경력 3년↑</span></div></li></ul>'
        rows = parse_cards("incruit", html)
        self.assertEqual(rows[0]["company_name"], "가상기업")
        self.assertIn("경력 3년", rows[0]["content"])

    def test_jobkorea_pairs_title_and_company_by_posting_id_not_position(self):
        html = '<div><article><a href="/Recruit/GI_Read/1">SQL 분석가</a><a href="/Recruit/GI_Read/1">기업 A</a><p>서울 경력무관</p></article><article><a href="/Recruit/GI_Read/2"><img alt="로고"></a><a href="/Recruit/GI_Read/2">ML 엔지니어</a><a href="/Recruit/GI_Read/2">기업 B</a><p>경기 1년</p></article></div>'
        jobs = parse_cards("jobkorea", html)
        self.assertEqual(
            [(j["title"], j["company_name"]) for j in jobs],
            [("SQL 분석가", "기업 A"), ("ML 엔지니어", "기업 B")],
        )
        self.assertNotIn("기업 B", jobs[0]["content"])
        self.assertNotIn("기업 A", jobs[1]["content"])

    def test_saramin_reads_company_from_its_card_instead_of_bracketed_department(self):
        html = '<div class="item_recruit"><h2 class="job_tit"><a href="/zf_user/jobs/relay/view?rec_idx=3">[분석팀] 데이터 분석가</a></h2><strong class="corp_name"><a href="/company">기업 C</a></strong><p>서울 SQL</p></div><script>fake job</script>'
        jobs = parse_cards("saramin", html)
        self.assertEqual(jobs[0]["company_name"], "기업 C")
        self.assertEqual(jobs[0]["retrieval_source"], "native_search")
        self.assertNotIn("fake job", jobs[0]["content"])

    def test_native_search_filters_unrelated_ads_without_loading_scripts_or_cookies(
        self,
    ):
        html = '<article><a href="/Recruit/GI_Read/1">보험 영업</a><a href="/Recruit/GI_Read/1">광고기업</a></article><article><a href="/Recruit/GI_Read/2">데이터 분석가</a><a href="/Recruit/GI_Read/2">기업 B</a></article>'
        requests = []

        def handle(request):
            requests.append(request)
            return httpx.Response(200, text=html)

        original = httpx.Client
        with patch(
            "job_agent.core.native_jobs.httpx.Client",
            side_effect=lambda **kw: original(
                transport=httpx.MockTransport(handle), **kw
            ),
        ):
            jobs = native_search("데이터 분석가 서울 채용", "jobkorea.co.kr")
        self.assertEqual([j["company_name"] for j in jobs], ["기업 B"])
        self.assertEqual(len(requests), 2)  # stop when the next page repeats IDs
        self.assertNotIn("cookie", requests[0].headers)
        self.assertEqual(requests[0].url.params["stext"], "데이터 분석")

    def test_incruit_card_carries_location_experience_and_apply_button(self):
        # Shape of the public Incruit search card (highlight spans split words).
        html = (
            '<ul class="c_row"><li class="c_col"><div class="cell_first"><a class="cpname">가상기업</a></div>'
            '<div class="cell_mid"><div class="cl_top"><a href="https://job.incruit.com/jobdb_info/jobpost.asp?job=2610160003272&src=etc">'
            '마이<span class="highlight">데이터</span>사업팀원 (<span class="highlight">데이터</span><span class="highlight">분석</span>가)</a>'
            '<button class="btns_scraps">스크랩</button></div>'
            '<div class="cl_md"><span>서울 강남구</span><span>경력 2~5년</span><span>대졸↑</span></div></div>'
            '<div class="cell_last"><div class="cl_btm"><span>~11.15 (일)</span></div>'
            "<div class=\"cl_top\"><button class='btns_job_submit'>바로지원</button></div></div></li></ul>"
        )
        row = parse_cards("incruit", html)[0]
        self.assertEqual(row["title"], "마이데이터사업팀원 (데이터분석가)")
        card = row["requirements_card"]
        self.assertEqual(card["job_location"], "서울 강남구")
        self.assertEqual(
            (card["experience"]["min_years"], card["experience"]["max_years"]), (2, 5)
        )
        self.assertTrue(card["application_available"])

    def test_jobkorea_card_carries_location_experience_and_apply_button(self):
        link = '<a href="https://www.jobkorea.co.kr/Recruit/GI_Read/50120666?Oem_Code=C1">'
        html = (
            '<div data-sentry-component="CardJob"><div>'
            f'{link}<span>데이터 과학자 경력직 모집</span></a>'
            f'<span>{link}<span>메디리타</span></a></span>'
            '<div data-sentry-component="GrayChip"><div><span class="emoji--basicemoji-place2"></span></div><span>서울 마포구</span></div>'
            '<div data-sentry-component="GrayChip"><div><span class="emoji--basicemoji-briefcase"></span></div><span>IT, 데이터분석가</span></div>'
            '<button type="button">즉시 지원</button>'
            '<span class="text-gray700">경력1년↑</span>'
            "</div></div>"
        )
        row = parse_cards("jobkorea", html)[0]
        card = row["requirements_card"]
        self.assertEqual(card["job_location"], "서울 마포구")
        self.assertEqual(card["experience"]["min_years"], 1)
        self.assertTrue(card["application_available"])
        self.assertEqual(card["job_title"], "데이터 과학자 경력직 모집")

    def test_or_alternatives_are_separate_site_searches(self):
        words = []

        def handle(request):
            words.append(request.url.params["stext"])
            return httpx.Response(200, text="<html></html>")

        original = httpx.Client
        with patch(
            "job_agent.core.native_jobs.httpx.Client",
            side_effect=lambda **kw: original(
                transport=httpx.MockTransport(handle), **kw
            ),
        ):
            native_search("머신러닝 OR AI 채용", "jobkorea.co.kr")
        self.assertEqual(words, ["머신러닝", "AI"])

    def test_unsupported_layout_does_not_fabricate_cards(self):
        self.assertEqual(
            parse_cards("jobkorea", "<html>로그인 또는 화면 변경</html>"), []
        )
        self.assertEqual(
            parse_cards("saramin", '<a href="/company">기업 이름만 있음</a>'), []
        )

    def test_provider_uses_native_when_available_and_index_on_failure(self):
        row = {"title": "분석가", "url": "https://www.jobkorea.co.kr/Recruit/GI_Read/1"}
        with (
            patch("job_agent.core.native_jobs.native_search", return_value=[row]),
            patch("tavily.TavilyClient") as client,
        ):
            self.assertEqual(
                WorkspaceService._web_search("분석가 채용", ["jobkorea.co.kr"]), [row]
            )
            client.assert_called_once()  # native matches no longer suppress index coverage
        with (
            patch("job_agent.core.native_jobs.native_search", side_effect=TimeoutError),
            patch("tavily.TavilyClient") as client,
        ):
            client.return_value.search.return_value = {"results": [row]}
            self.assertEqual(
                WorkspaceService._web_search("분석가 채용", ["jobkorea.co.kr"])[0][
                    "retrieval_source"
                ],
                "search_index",
            )


if __name__ == "__main__":
    unittest.main()
