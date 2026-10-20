import unittest

from job_agent.core.job_match import (
    DEFAULT_EXPERIENCE,
    experience,
    merge_cross_platform,
    requirements,
)


class RequirementTests(unittest.TestCase):
    def test_year_bounds_entry_and_unspecified_are_distinct(self):
        for raw, kind, low in [
            ("신입", "entry", None),
            ("경력무관", "any", None),
            ("경력 3~10년", "years", 3),
            ("경력 7년 이상", "years", 7),
            ("경력", "unknown", None),
            ("복지 3년 장기근속", "unknown", None),
        ]:
            got = experience(raw)
            self.assertEqual(got["kind"], kind)
            self.assertEqual(got.get("min_years"), low)

    def test_actual_requirements_hold_unknown_and_reject_outside_scope(self):
        rule = {
            "role": "데이터 분석가",
            "location": "서울, 경기",
            "experience": DEFAULT_EXPERIENCE,
        }
        base = {
            "job_title": "데이터 분석가",
            "job_location": "서울 영등포",
            "application_available": True,
            "experience": experience("경력 3년 이상"),
        }
        self.assertEqual(requirements(base, rule)["decision"], "pass")
        for change, reason in [
            ({"experience": experience("7년 이상")}, "experience_mismatch"),
            ({"experience": experience("")}, "experience_unknown"),
            ({"job_location": ""}, "location_unknown"),
            ({"job_location": "부산 해운대"}, "location_mismatch"),
            ({"job_title": "백엔드 엔지니어 SQL Python"}, "role_mismatch"),
        ]:
            self.assertEqual(requirements({**base, **change}, rule)["reason"], reason)
        self.assertEqual(
            requirements({**base, "experience": experience("4~10년")}, rule)[
                "decision"
            ],
            "pass",
        )

    def test_cross_platform_dedup_keeps_teams_and_weak_evidence_separate(self):
        base = {
            "company": "㈜가상기업",
            "role": "데이터 분석가",
            "status_check": {"deadline": "2026-11-30", "job_location": "서울"},
        }
        rows = [
            {**base, "url": "https://www.wanted.co.kr/wd/1"},
            {
                **base,
                "company": "가상기업",
                "url": "https://www.jobkorea.co.kr/Recruit/GI_Read/1",
            },
            {
                **base,
                "role": "마케팅팀 데이터 분석가",
                "url": "https://www.wanted.co.kr/wd/2",
            },
        ]
        merged = merge_cross_platform(rows)
        self.assertEqual(len(merged), 2)
        self.assertEqual(merged[0]["alternate_urls"], [rows[1]["url"]])
        self.assertEqual(
            len(merge_cross_platform([{**r, "status_check": {}} for r in rows])), 3
        )
