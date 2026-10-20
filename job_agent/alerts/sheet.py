"""Append every matching posting to the owner's Google Sheet.

The sheet is reached through the owner's own Apps Script web app
(``deploy/sheets/job_alerts.gs``): ``ALERT_SHEET_URL`` is its /exec address and
``ALERT_SHEET_TOKEN`` must equal the script's SHEET_TOKEN property. No Google
credentials live in this project; only the Apps Script result redirect is
followed.
"""

import os
import re
from urllib.parse import urlsplit

import httpx

from job_agent.core.postings import NAMES

WEB_APP = re.compile(r"https://script\.google\.com/macros/s/[A-Za-z0-9_-]+/exec")
COLUMNS = [
    "checked_at",
    "alert",
    "platform",
    "company",
    "role",
    "location",
    "experience",
    "period",
    "apply_button",
    "mailed",
    "url",
]


def sheet_rows(alert_name, jobs, mailed_urls, today):
    """One flat row per posting; 'mailed' is the date it went out, else ''."""
    rows = []
    for job in jobs:
        check = job.get("status_check") or {}
        rows.append(
            {
                "checked_at": str(check.get("checked_at", "")),
                "alert": str(alert_name)[:60],
                "platform": NAMES.get(job.get("site"), str(job.get("site", ""))),
                "company": str(job.get("company", ""))[:100],
                "role": str(job.get("role", ""))[:200],
                "location": str(check.get("job_location", ""))[:120],
                "experience": str((check.get("experience") or {}).get("evidence", ""))[:120],
                "period": str(job.get("period", ""))[:100],
                "apply_button": "확인"
                if (job.get("requirements_check") or {}).get("application_confirmed")
                else "미확인",
                "mailed": today if job.get("url") in mailed_urls else "",
                "url": str(job.get("url", "")),
            }
        )
    return rows


class SheetExporter:
    def __init__(self, url=None, token=None, client=None):
        self.url = (os.getenv("ALERT_SHEET_URL", "") if url is None else url).strip()
        self.token = (
            os.getenv("ALERT_SHEET_TOKEN", "") if token is None else token
        ).strip()
        self.client = client

    def configured(self):
        return bool(WEB_APP.fullmatch(self.url)) and len(self.token) >= 32

    def export(self, rows):
        if not self.configured():
            raise ValueError("구글 시트 주소·토큰 설정이 없습니다.")
        client = self.client or httpx.Client(
            timeout=30, follow_redirects=False, trust_env=False
        )
        try:
            response = client.post(
                self.url, json={"token": self.token, "columns": COLUMNS, "rows": rows}
            )
            # Apps Script answers a POST with a redirect to its result page.
            if response.status_code in {301, 302, 303, 307, 308}:
                location = response.headers.get("location", "")
                target = urlsplit(location)
                if (
                    target.scheme != "https"
                    or target.hostname != "script.googleusercontent.com"
                ):
                    raise ValueError("예상하지 못한 시트 응답 주소입니다.")
                response = client.get(location)
            response.raise_for_status()
            result = response.json()
        finally:
            if self.client is None:
                client.close()
        if not isinstance(result, dict) or result.get("ok") is not True:
            raise ValueError("시트가 저장을 거부했습니다.")
        return result
