import os
import unittest
from unittest.mock import Mock, patch

from job_agent.ui.service import WorkspaceService


class VerifiedSearchTests(unittest.TestCase):
    def test_ui_and_alerts_use_detail_requirements_not_snippet_keywords(self):
        rows = [
            {
                "title": "데이터 분석 SQL",
                "url": f"https://www.wanted.co.kr/wd/{i}",
                "content": "서울 SQL",
            }
            for i in range(1, 5)
        ]
        base = {
            "status": "open",
            "deadline": "2099-11-30",
            "job_location": "서울",
            "application_available": True,
            "job_title": "데이터 분석가",
        }

        def verify(url, now):
            i = url.rsplit("/", 1)[1]
            return {
                **base,
                "experience": {
                    "kind": "years",
                    "min_years": 7 if i == "2" else 3,
                    "max_years": None,
                },
                "job_location": "" if i == "3" else "서울",
                "job_title": "백엔드 개발자" if i == "4" else base["job_title"],
            }

        service = WorkspaceService(
            searcher=Mock(return_value=rows), verifier=verify, ephemeral=True
        )
        with patch.dict(os.environ, {"TAVILY_API_KEY": "fixture"}):
            result = service._search(
                {
                    "source": "web",
                    "search_consent": True,
                    "sites": ["wanted"],
                    "role": "데이터 분석가",
                    "location": "서울, 경기",
                    "verify_requirements": True,
                }
            )
        self.assertEqual(
            [j["url"] for j in result["jobs"]], ["https://www.wanted.co.kr/wd/1"]
        )
        self.assertEqual(result["coverage"]["experience_mismatch"], 1)
        self.assertEqual(result["coverage"]["location_unknown"], 1)
        self.assertEqual(result["coverage"]["role_mismatch"], 1)
