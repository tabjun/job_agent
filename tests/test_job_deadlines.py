"""Expiry regressions at the real alert collection boundary; no SMTP/network."""

import tempfile
import unittest
from datetime import datetime
from pathlib import Path

from job_agent.alerts.service import JobAlerts
from job_agent.core.job_status import detail_status
from job_agent.core.paths import ProjectPaths


class AlertDeadlineTests(unittest.TestCase):
    def collect(self, rows, html=None):
        with tempfile.TemporaryDirectory() as folder:
            alerts = JobAlerts(
                ProjectPaths(Path(folder)),
                searcher=lambda *_: rows,
                clock=lambda: datetime(2026, 10, 20, 9),
                verifier=lambda url, now: detail_status(
                    html
                    if html is not None
                    else "<p>접수기간 2026.07.01 ~ 2026.11.30</p>",
                    url,
                    now,
                ),
            )
            return alerts.collect(
                {
                    "platforms": {
                        "jobkorea": {
                            "role": "데이터",
                            "location": "서울",
                            "keywords": "SQL",
                            "exclude": "",
                        }
                    },
                    "max_results": 10,
                }
            )[0]

    def row(self, content):
        return {
            "title": "데이터 분석 SQL",
            "company_name": "가상기업",
            "url": "https://www.jobkorea.co.kr/Recruit/GI_Read/123",
            "content": content,
        }

    def test_past_recruitment_period_never_enters_mail_candidates(self):
        self.assertEqual(
            self.collect([self.row("서울 접수기간 2026.07.01 ~ 2026.07.17")]), []
        )

    def test_closed_badge_with_parenthesized_date_is_excluded(self):
        self.assertEqual(self.collect([self.row("서울 마감 (~2026.07.17)")]), [])

    def test_july_publication_is_not_a_deadline(self):
        rows = self.collect(
            [self.row("서울 등록일 2026.07.01 접수기간 2026.07.01 ~ 2026.11.30")]
        )
        self.assertEqual(len(rows), 1)

    def test_stale_snippet_cannot_override_current_closed_detail(self):
        self.assertEqual(
            self.collect(
                [self.row("서울 SQL 상시채용")],
                "<h1>SQL 분석</h1><p>마감되었습니다.</p><p>채용 시 마감</p>",
            ),
            [],
        )

    def test_unknown_detail_is_withheld_even_with_future_search_deadline(self):
        self.assertEqual(
            self.collect(
                [self.row("서울 마감일 2026.11.30")], "<p>로그인이 필요합니다</p>"
            ),
            [],
        )


if __name__ == "__main__":
    unittest.main()
