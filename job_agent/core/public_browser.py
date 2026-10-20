"""Read-only anonymous DOM fallback; never opens an owner's portal profile."""

import threading
from pathlib import Path
from urllib.parse import urlsplit

from job_agent.core.job_status import detail_url

_SLOTS = threading.BoundedSemaphore(2)
PLATFORMS = ("jobkorea.co.kr", "saramin.co.kr", "wanted.co.kr", "catch.co.kr", "incruit.com")


def render_public(url):
    target = detail_url(url)
    if not target:
        return ""
    try:
        from playwright.sync_api import sync_playwright
        from job_agent.browser.session import find_local_browser

        source = (Path(__file__).parents[1]/"browser/public_snapshot.js").read_text(encoding="utf-8")
        with _SLOTS, sync_playwright() as p:
            browser = p.chromium.launch(headless=True,executable_path=find_local_browser(),timeout=12000)
            try:
                context = browser.new_context(service_workers="block")
                def route(request):
                    u = urlsplit(request.request.url)
                    allowed = u.scheme=="https" and any(u.hostname==d or (u.hostname or "").endswith("."+d) for d in PLATFORMS)
                    if not allowed or request.request.resource_type in {"image","font","media"}:
                        request.abort();return
                    headers = request.request.headers.copy();headers.pop("cookie",None)
                    request.continue_(headers=headers)
                context.route("**/*",route)
                page = context.new_page()
                page.goto(target,wait_until="domcontentloaded",timeout=18000)
                try:page.wait_for_load_state("networkidle",timeout=5000)
                except Exception:pass  # noqa: BLE001, S110 - snapshot the visible page; do not bypass blocks
                if detail_url(page.url)!=target:
                    return ""
                html = page.evaluate(source)
                return html if len(html.encode())<=3_000_000 else ""
            finally:
                browser.close()
    except Exception:  # noqa: BLE001 - absent browser, login wall or blocked rendering is unknown
        return ""
