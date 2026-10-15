"""Public card layouts and provider fallback; no network or account sessions."""

import unittest
from unittest.mock import patch

import httpx

from job_agent.core.native_jobs import native_search, parse_cards
from job_agent.ui.service import WorkspaceService


class NativeJobTests(unittest.TestCase):
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
        self.assertEqual(len(requests), 1)
        self.assertNotIn("cookie", requests[0].headers)
        self.assertEqual(requests[0].url.params["stext"], "데이터 분석")

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
            client.assert_not_called()
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
