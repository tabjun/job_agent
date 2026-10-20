import unittest

from job_agent.core.job_match import (
    DEFAULT_EXPERIENCE,
    experience,
    merge_cross_platform,
    requested_experience,
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

    def test_role_families_cover_korean_suffixes_and_adjacent_titles(self):
        rule = {"role": "데이터 분석 데이터 사이언티스트 머신러닝 AI"}
        base = {"job_location": "", "application_available": True}
        for title in [
            "AI엔지니어",
            "ML엔지니어 (추천)",
            "LLM개발자",
            "MLOps엔지니어",
            "Ai영상처리 개발자",
            "데이터 엔지니어",
            "Data Engineer",
            "Product Analyst",
            "그로스 분석가",
            "BI 담당자",
            "Research Scientist",
            "통계 분석 연구원",
            "영업 데이터 분석가",
        ]:
            with self.subTest(title=title):
                got = requirements({**base, "job_title": title}, rule)
                self.assertEqual(got["decision"], "pass", got)
        for title in ["백엔드 엔지니어", "Email 마케터", "AIoT 펌웨어", "PAID 광고"]:
            with self.subTest(title=title):
                self.assertEqual(
                    requirements({**base, "job_title": title}, rule)["reason"],
                    "role_mismatch",
                )

    def test_training_sales_and_licensed_roles_are_not_data_jobs(self):
        rule = {"role": "데이터 분석 데이터 사이언티스트 머신러닝 AI"}
        for title in [
            "IT프로그래밍 분야 강사님 모집",
            "영상데이터 분석가(방사선사)",
            "AI 솔루션 영업",
            "국비지원 데이터 분석 교육생 모집",
            "AI 부트캠프 수강생 모집",
            "피지컬 AI 데이터 수집 직원 채용",
            "AI 학습데이터 라벨링 알바",
        ]:
            with self.subTest(title=title):
                got = requirements(
                    {"job_title": title, "application_available": True}, rule
                )
                self.assertEqual(got["reason"], "role_excluded")

    def test_open_posting_without_visible_apply_button_is_kept_with_a_label(self):
        rule = {"role": "데이터 분석가", "experience": DEFAULT_EXPERIENCE}
        base = {"job_title": "데이터 분석가", "experience": experience("신입")}
        got = requirements(base, rule)
        self.assertEqual(got["decision"], "pass")
        self.assertFalse(got["application_confirmed"])
        got = requirements({**base, "application_available": True}, rule)
        self.assertTrue(got["application_confirmed"])
        got = requirements({**base, "application_blocked": True}, rule)
        self.assertEqual(
            (got["decision"], got["reason"]), ("hold", "application_blocked")
        )

    def test_any_experience_posting_is_open_to_every_request(self):
        rule = {
            "role": "데이터 분석가",
            "experience": {"entry": True, "any": False, "min_years": 0, "max_years": 0},
        }
        posting = {"job_title": "데이터 분석가", "experience": experience("경력무관")}
        self.assertEqual(requirements(posting, rule)["decision"], "pass")

    def test_requested_experience_reads_each_comma_separated_part(self):
        self.assertEqual(
            requested_experience("신입, 경력무관, 1~5년"),
            {"entry": True, "any": True, "min_years": 1, "max_years": 5},
        )
        self.assertEqual(
            requested_experience("3년차 이하"),
            {"entry": False, "any": False, "min_years": 0, "max_years": 3},
        )
        self.assertEqual(
            requested_experience("신입")["max_years"], 0
        )
        with self.assertRaises(ValueError):
            requested_experience("아무 조건")

    def test_more_experience_wordings_and_overlap_policy(self):
        for raw, kind, low, high in [
            ("경력 4년~10년", "years", 4, 10),
            ("3+ years of experience", "years", 3, None),
            ("Junior", "years", 0, 3),
            ("경력 3년차 이상", "years", 3, None),
            ("3년 이상 7년 이하", "years", 3, 7),
            ("경력:신입/경력", "any", None, None),
        ]:
            with self.subTest(raw=raw):
                got = experience(raw)
                self.assertEqual(
                    (got["kind"], got.get("min_years"), got.get("max_years")),
                    (kind, low, high),
                )
        rule = {"role": "데이터 분석가", "experience": DEFAULT_EXPERIENCE}
        for raw, decision in [
            ("경력 4~10년", "pass"),
            ("5년 이상", "pass"),
            ("7년 이상", "reject"),
        ]:
            got = requirements(
                {"job_title": "데이터 분석가", "experience": experience(raw)}, rule
            )
            self.assertEqual(got["decision"], decision, raw)

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
