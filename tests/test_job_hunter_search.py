import unittest
from unittest.mock import patch

from job_agent.agents.job_hunter import search_jobs
from job_agent.ui.service import SITES, WorkspaceService


class HunterSearchTests(unittest.IsolatedAsyncioTestCase):
    async def test_tool_uses_requested_role_and_same_five_platform_collector(self):
        with patch.object(
            WorkspaceService,
            "_search",
            return_value={
                "jobs": [{"title": "통계 분석가", "content": "마감일은 원문 확인"}]
            },
        ) as collect:
            rows = await search_jobs.ainvoke(
                {
                    "role": "통계 분석가",
                    "experience": "신입 또는 1~5년",
                    "location": "서울 경기",
                    "keywords": "R SQL",
                }
            )
        payload = collect.call_args.args[0]
        self.assertEqual(payload["role"], "통계 분석가")
        self.assertEqual(payload["sites"], list(SITES))
        self.assertNotIn("2026년 5월", str(payload))
        self.assertEqual(len(rows), 1)  # A deadline label is not a closed posting.
        self.assertEqual(rows[0]["experience_requested"], "신입 또는 1~5년")
        self.assertIs(rows[0]["experience_verified"], False)
