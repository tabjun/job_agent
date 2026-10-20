"""Compact, escaped email tables; never guess missing company names or dates."""

from html import escape

from job_agent.core.postings import posting_fields, text
from job_agent.ui.service import safe_url


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
        link = (
            f'<a href="{escape(url, quote=True)}" style="color:#165c9c;text-decoration:underline">{escape(role)}</a>'
            if url
            else escape(role)
        )
        rows.append(
            "<tr>"
            f'<td style="padding:10px 8px;border-bottom:1px solid #ddd;vertical-align:top;overflow-wrap:anywhere">{escape(company)}<br><small style="color:#666">{escape(name)}</small></td>'
            f'<td style="padding:10px 8px;border-bottom:1px solid #ddd;vertical-align:top;overflow-wrap:anywhere">{link}</td>'
            f'<td style="padding:10px 8px;border-bottom:1px solid #ddd;vertical-align:top;overflow-wrap:anywhere">{escape(period)}</td>'
            "</tr>"
        )
    footer = "발송 전 원문 접수상태 확인 · 이후 변경될 수 있으므로 지원 전 원문에서 확인하세요."
    if alert.get("collection"):
        info = alert["collection"]
        footer = (
            f"수집 {info.get('fetched', 0)}건 · 조건 통과 {info.get('eligible', 0)}건 · 마감 제외 {info.get('closed', 0) + info.get('detail_closed', 0)}건 · 상태 미확인 보류 {info.get('status_unverified', 0)}건 · 이번 메일 {len(jobs)}건 (설정 상한 {info.get('limit', 10)}건). "
            + footer
        )
    plain += ["", footer]
    html = (
        '<!doctype html><html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head>'
        "<body style=\"margin:0;padding:16px;font-family:Arial,'Malgun Gothic',sans-serif;color:#202628;font-size:14px\">"
        f'<h1 style="font-size:18px;margin:0 0 16px">{escape(heading)}</h1>'
        '<table aria-label="새 채용 공고" style="width:100%;max-width:760px;border-collapse:collapse;table-layout:fixed;text-align:left">'
        '<thead><tr style="background:#edf2f4">'
        '<th scope="col" style="width:24%;padding:10px 8px">회사명</th>'
        '<th scope="col" style="width:48%;padding:10px 8px">직무</th>'
        '<th scope="col" style="width:28%;padding:10px 8px">공고 기간</th>'
        "</tr></thead><tbody>" + "".join(rows) + "</tbody></table>"
        f'<p style="font-size:12px;color:#666;margin-top:16px">{escape(footer)}</p></body></html>'
    )
    return (
        f"[공고 알림] {text(alert['name'], 60)} 새 공고 {len(jobs)}건",
        "\n".join(plain),
        html,
    )
