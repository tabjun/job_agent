"""Compact, escaped email tables; never guess missing company names or dates."""

import re
from html import escape

from job_agent.ui.service import safe_url


def text(value, limit=180):
    return " ".join(str(value or "").split())[:limit]


def posting_fields(row):
    company = row.get("company_name") or row.get("company") or row.get("hiringOrganization")
    if isinstance(company, dict):
        company = company.get("name")
    title = text(row.get("title"), 300)
    role = text(row.get("role") or row.get("position") or row.get("job_title"))
    # Explicit company markers only: generic hyphens can be part of a job title.
    match = re.match(r"^\[([^\[\]]{2,80})\]\s*(.+)$", title)
    if match is None:
        match = re.match(r"^(.{2,80}?)\s+채용\s*[-:|]\s*(.+)$", title)
    if match and not re.fullmatch(r"신입|경력|신입[·/ ]경력|정규직|계약직|인턴|상시|채용|서울|경기|\d{4}.*", match[1]):
        company = company or re.sub(r"\s+채용$", "", match[1])
        role = role or match[2]
    role = re.sub(r"\s*[-|]\s*(캐치|잡코리아|사람인|원티드|인크루트)\s*$", "", role or title)
    period = text(row.get("period") or row.get("recruitment_period"), 100)
    start, end = text(row.get("start_date"), 40), text(row.get("end_date") or row.get("validThrough") or row.get("deadline"), 40)
    if not period and end:
        period = f"{start} ~ {end}" if start else f"~ {end}"
    if not period:
        source = title + " " + text(row.get("content") or row.get("excerpt"), 2000)
        date = r"(?:\d{4}[./-])?\d{1,2}[./-]\d{1,2}(?:\s*\([월화수목금토일]\))?"
        match = re.search(rf"(?:접수|모집|채용|공고)\s*기간\s*[:：]?\s*({date}\s*[~∼～]\s*{date})", source)
        if match:
            period = match[1]
        else:
            match = re.search(rf"마감(?:일|날짜)?\s*[:：]?\s*({date})", source)
            if match:
                period = f"~ {match[1]}"
    return {"company": text(company, 100) or "원문 확인", "role": text(role) or "원문 확인", "period": period or "원문 확인"}


def compose(alert, jobs, names):
    heading = f"{text(alert['name'], 60)} · 새 공고 {len(jobs)}건"
    plain = [heading, "", "회사명 | 직무 | 공고 기간"]
    rows = []
    for job in jobs:
        fields = posting_fields(job)
        name = names.get(job.get("site"), "")
        url = safe_url(job.get("url", ""))
        company, role, period = (fields[key] for key in ("company", "role", "period"))
        plain += [f"{company} ({name}) | {role} | {period}"]
        if url:
            plain.append(url)
        link = f'<a href="{escape(url, quote=True)}" style="color:#165c9c;text-decoration:underline">{escape(role)}</a>' if url else escape(role)
        rows.append(
            '<tr>'
            f'<td style="padding:10px 8px;border-bottom:1px solid #ddd;vertical-align:top;overflow-wrap:anywhere">{escape(company)}<br><small style="color:#666">{escape(name)}</small></td>'
            f'<td style="padding:10px 8px;border-bottom:1px solid #ddd;vertical-align:top;overflow-wrap:anywhere">{link}</td>'
            f'<td style="padding:10px 8px;border-bottom:1px solid #ddd;vertical-align:top;overflow-wrap:anywhere">{escape(period)}</td>'
            '</tr>'
        )
    footer = "검색 요약 기반 · 공고 기간 등 미확인 정보는 원문에서 확인하세요."
    plain += ["", footer]
    html = (
        '<!doctype html><html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head>'
        '<body style="margin:0;padding:16px;font-family:Arial,\'Malgun Gothic\',sans-serif;color:#202628;font-size:14px">'
        f'<h1 style="font-size:18px;margin:0 0 16px">{escape(heading)}</h1>'
        '<table aria-label="새 채용 공고" style="width:100%;max-width:760px;border-collapse:collapse;table-layout:fixed;text-align:left">'
        '<thead><tr style="background:#edf2f4">'
        '<th scope="col" style="width:24%;padding:10px 8px">회사명</th>'
        '<th scope="col" style="width:48%;padding:10px 8px">직무</th>'
        '<th scope="col" style="width:28%;padding:10px 8px">공고 기간</th>'
        '</tr></thead><tbody>' + ''.join(rows) + '</tbody></table>'
        f'<p style="font-size:12px;color:#666;margin-top:16px">{escape(footer)}</p></body></html>'
    )
    return f"[공고 알림] {text(alert['name'], 60)} 새 공고 {len(jobs)}건", "\n".join(plain), html
