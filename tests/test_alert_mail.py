import os
import unittest
from unittest.mock import MagicMock, patch

from job_agent.alerts.mail import compose, posting_fields
from job_agent.alerts.service import NAMES, Mailer


class AlertMailTests(unittest.TestCase):
    def test_invalid_smtp_security_rejected_before_network_connection(self):
        for value in ("starttl", "plain", ""):
            with (
                self.subTest(value=value),
                patch.dict(os.environ, {"ALERT_SMTP_SECURITY": value}),
                patch("job_agent.alerts.service.smtplib.SMTP") as smtp,
                patch("job_agent.alerts.service.smtplib.SMTP_SSL") as smtp_ssl,
            ):
                with self.assertRaisesRegex(ValueError, "ssl 또는 starttls"):
                    Mailer().send("verified@example.com", "제목", "내용")
                smtp.assert_not_called()
                smtp_ssl.assert_not_called()

    def test_smtp_security_normalized_and_tls_precedes_login(self):
        client = MagicMock()
        client.__enter__.return_value = client
        settings = {
            "ALERT_SMTP_HOST": "smtp.example.com",
            "ALERT_SMTP_USER": "owner@example.com",
            "ALERT_SMTP_SECURITY": " STARTTLS ",
        }
        with (
            patch.dict(os.environ, settings),
            patch("job_agent.alerts.service.smtplib.SMTP", return_value=client),
        ):
            Mailer().send("verified@example.com", "제목", "내용")
        methods = [call[0] for call in client.method_calls]
        self.assertLess(methods.index("starttls"), methods.index("login"))
        self.assertLess(methods.index("login"), methods.index("send_message"))

    def test_ssl_mode_uses_encrypted_connection(self):
        client = MagicMock()
        client.__enter__.return_value = client
        with (
            patch.dict(
                os.environ,
                {
                    "ALERT_SMTP_HOST": "smtp.example.com",
                    "ALERT_SMTP_FROM": "owner@example.com",
                    "ALERT_SMTP_SECURITY": "ssl",
                },
            ),
            patch(
                "job_agent.alerts.service.smtplib.SMTP_SSL", return_value=client
            ) as smtp_ssl,
            patch("job_agent.alerts.service.smtplib.SMTP") as smtp,
        ):
            Mailer().send("verified@example.com", "제목", "내용")
            smtp_ssl.assert_called_once()
            smtp.assert_not_called()
            client.starttls.assert_not_called()

    def test_evidence_only_columns_and_round_trip(self):
        row = {
            "title": "[예시기업] 데이터 분석가 - 원티드",
            "content": "접수기간: 2026.10.15 ~ 2026.10.31 상세 설명 "
            + "긴 소개 " * 200,
        }
        fields = posting_fields(row)
        self.assertEqual(
            fields,
            {
                "company": "예시기업",
                "role": "데이터 분석가",
                "period": "2026.10.15 ~ 2026.10.31",
            },
        )
        self.assertEqual(posting_fields({**row, **fields}), fields)
        self.assertEqual(
            posting_fields(
                {
                    "title": "다른 직무",
                    "company_name": "명시된 기업",
                    "job_title": "통계",
                    "start_date": "2026-10-01",
                    "end_date": "2026-10-20",
                }
            ),
            {
                "company": "명시된 기업",
                "role": "통계",
                "period": "2026-10-01 ~ 2026-10-20",
            },
        )

    def test_unknown_company_dates_and_job_level_are_not_guessed(self):
        for title in (
            "데이터 분석가",
            "[경력] 데이터 분석가",
            "[2026 하반기] 데이터 분석가",
        ):
            fields = posting_fields(
                {"title": title, "content": "교육기간 10.01 ~ 10.31, 등록일 2026.10.01"}
            )
            self.assertEqual(fields["company"], "원문 확인")
            self.assertEqual(fields["period"], "원문 확인")
        self.assertEqual(
            posting_fields(
                {"title": "기업 채용 - ML", "content": "마감일: 2026-10-31"}
            )["period"],
            "~ 2026-10-31",
        )

    def test_compact_html_table_no_excerpts_and_safe_links(self):
        jobs = [
            {
                "title": "[예시기업] ML 엔지니어",
                "site": "wanted",
                "url": "https://www.wanted.co.kr/wd/1?a=1&b=2",
                "excerpt": "긴 소개 " * 200,
                "matched_keywords": ["Python"],
            }
        ]
        subject, plain, html = compose({"name": "데이터·AI"}, jobs, NAMES)
        self.assertIn("새 공고 1건", subject)
        self.assertIn("회사명 | 직무 | 공고 기간", plain)
        self.assertEqual(html.count('<th scope="col"'), 3)
        self.assertIn("ML 엔지니어</a>", html)
        self.assertIn("a=1&amp;b=2", html)
        self.assertNotIn("긴 소개", html + plain)
        self.assertNotIn("일치 키워드", html + plain)
        self.assertLess(len(plain.splitlines()), 10)

    def test_escape_all_untrusted_fields_and_reject_script_urls(self):
        jobs = [
            {
                "company": '<img src=x onerror="x">',
                "role": "<script>x</script>",
                "period": "<b>기간</b>",
                "site": "wanted",
                "url": "javascript:alert(1)",
            }
        ]
        _, _, html = compose({"name": "<script>title</script>"}, jobs, NAMES)
        self.assertNotIn("<script>", html)
        self.assertNotIn("<img", html)
        self.assertNotIn("javascript:", html)
        self.assertNotIn("<a ", html)

    def test_smtp_html_alternative_and_plain_verification_mail(self):
        client = MagicMock()
        client.__enter__.return_value = client
        with (
            patch.object(
                Mailer,
                "settings",
                return_value=(
                    "smtp.example.com",
                    587,
                    "",
                    "owner@example.com",
                    "starttls",
                ),
            ),
            patch("job_agent.alerts.service.smtplib.SMTP", return_value=client),
        ):
            mailer = Mailer()
            mailer.send("verified@example.com", "제목", "텍스트", "<table></table>")
            message = client.send_message.call_args.args[0]
            self.assertEqual(message.get_content_type(), "multipart/alternative")
            self.assertEqual(
                [p.get_content_type() for p in message.iter_parts()],
                ["text/plain", "text/html"],
            )
            self.assertIn(
                "<table>", message.get_body(preferencelist=("html",)).get_content()
            )
            mailer.send("verified@example.com", "인증", "인증 코드: 123456")
            self.assertEqual(
                client.send_message.call_args.args[0].get_content_type(), "text/plain"
            )
