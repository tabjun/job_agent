import argparse
import asyncio
import json
import os
import re
from dataclasses import asdict, dataclass
from datetime import datetime
from html.parser import HTMLParser
from typing import Dict, List, Optional
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


SITE_TARGETS: Dict[str, Dict[str, object]] = {
    "saramin": {
        "name": "Saramin",
        "aliases": ["saramin", "사람인"],
        "candidate_urls": [
            "https://www.saramin.co.kr/zf_user/resume/resume-manage",
            "https://www.saramin.co.kr/zf_user/resume/resume-write",
            "https://www.saramin.co.kr/zf_user/member/persons-main",
        ],
    },
    "wanted": {
        "name": "Wanted",
        "aliases": ["wanted", "원티드"],
        "candidate_urls": [
            "https://www.wanted.co.kr/profile",
            "https://www.wanted.co.kr/profile/resume",
            "https://www.wanted.co.kr/cv/list",
        ],
    },
    "jobplanet": {
        "name": "JobPlanet",
        "aliases": ["jobplanet", "잡플래닛"],
        "candidate_urls": [
            "https://www.jobplanet.co.kr/user-session/sign-in",
            "https://www.jobplanet.co.kr/profile/resume",
            "https://www.jobplanet.co.kr/users/resume",
        ],
    },
    "catch": {
        "name": "Catch",
        "aliases": ["catch", "캐치"],
        "candidate_urls": [
            "https://www.catch.co.kr/",
            "https://www.catch.co.kr/NCS/Resume",
            "https://www.catch.co.kr/Member/Resume",
        ],
    },
    "jobkorea": {
        "name": "JobKorea",
        "aliases": ["jobkorea", "잡코리아"],
        "candidate_urls": [
            "https://www.jobkorea.co.kr/User/Resume",
            "https://www.jobkorea.co.kr/User/Resume/Write",
            "https://www.jobkorea.co.kr/User/Resume/Manage",
        ],
    },
    "linkedin": {
        "name": "LinkedIn",
        "aliases": ["linkedin", "링크드인"],
        "candidate_urls": [
            "https://www.linkedin.com/in/",
            "https://www.linkedin.com/feed/",
            "https://www.linkedin.com/profile/edit/forms/position/new/",
        ],
    },
}


CHROME_CANDIDATES = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
]


@dataclass
class StaticFetchResult:
    site_key: str
    site_name: str
    url: str
    status: Optional[int]
    final_url: Optional[str]
    content_type: Optional[str]
    title: Optional[str]
    form_count: int
    input_count: int
    textarea_count: int
    select_count: int
    script_count: int
    likely_login_required: bool
    error: Optional[str] = None


class StaticFormParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.in_title = False
        self.title_parts: List[str] = []
        self.form_count = 0
        self.input_count = 0
        self.textarea_count = 0
        self.select_count = 0
        self.script_count = 0
        self.login_hints = 0

    def handle_starttag(self, tag, attrs):
        attrs_dict = {k.lower(): (v or "") for k, v in attrs}
        if tag == "title":
            self.in_title = True
        if tag == "form":
            self.form_count += 1
        if tag == "input":
            self.input_count += 1
        if tag == "textarea":
            self.textarea_count += 1
        if tag == "select":
            self.select_count += 1
        if tag == "script":
            self.script_count += 1
        haystack = " ".join([tag, *attrs_dict.keys(), *attrs_dict.values()]).lower()
        if any(token in haystack for token in ["login", "signin", "sign-in", "로그인"]):
            self.login_hints += 1

    def handle_endtag(self, tag):
        if tag == "title":
            self.in_title = False

    def handle_data(self, data):
        if self.in_title:
            self.title_parts.append(data.strip())
        if any(token in data.lower() for token in ["login", "sign in", "로그인"]):
            self.login_hints += 1

    @property
    def title(self) -> str:
        return " ".join(part for part in self.title_parts if part).strip()


def normalize_site(site: str) -> str:
    needle = site.strip().lower()
    for key, target in SITE_TARGETS.items():
        aliases = [str(alias).lower() for alias in target["aliases"]]
        if needle == key or needle in aliases:
            return key
    raise ValueError(f"Unknown site: {site}. Known: {', '.join(SITE_TARGETS)}")


def ensure_output_dir() -> str:
    out_dir = os.path.join("result", "site_form_maps")
    os.makedirs(out_dir, exist_ok=True)
    return out_dir


def fetch_url(url: str, timeout: int = 20) -> tuple[Optional[int], Optional[str], Optional[str], str]:
    req = Request(
        url,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/126.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
        },
    )
    with urlopen(req, timeout=timeout) as response:
        body = response.read(2_000_000).decode("utf-8", "ignore")
        return response.status, response.geturl(), response.headers.get("content-type"), body


def static_probe_site(site_key: str) -> List[StaticFetchResult]:
    target = SITE_TARGETS[site_key]
    rows: List[StaticFetchResult] = []
    for url in target["candidate_urls"]:
        try:
            status, final_url, content_type, body = fetch_url(str(url))
            parser = StaticFormParser()
            parser.feed(body)
            likely_login = (
                parser.login_hints > 0
                or "login" in (final_url or "").lower()
                or "sign" in (final_url or "").lower()
                or "로그인" in body[:5000]
            )
            rows.append(
                StaticFetchResult(
                    site_key=site_key,
                    site_name=str(target["name"]),
                    url=str(url),
                    status=status,
                    final_url=final_url,
                    content_type=content_type,
                    title=parser.title,
                    form_count=parser.form_count,
                    input_count=parser.input_count,
                    textarea_count=parser.textarea_count,
                    select_count=parser.select_count,
                    script_count=parser.script_count,
                    likely_login_required=likely_login,
                )
            )
        except HTTPError as exc:
            rows.append(
                StaticFetchResult(
                    site_key=site_key,
                    site_name=str(target["name"]),
                    url=str(url),
                    status=exc.code,
                    final_url=exc.geturl(),
                    content_type=exc.headers.get("content-type") if exc.headers else None,
                    title=None,
                    form_count=0,
                    input_count=0,
                    textarea_count=0,
                    select_count=0,
                    script_count=0,
                    likely_login_required=exc.code in {401, 403, 404},
                    error=f"HTTPError: {exc.code}",
                )
            )
        except (URLError, TimeoutError, OSError) as exc:
            rows.append(
                StaticFetchResult(
                    site_key=site_key,
                    site_name=str(target["name"]),
                    url=str(url),
                    status=None,
                    final_url=None,
                    content_type=None,
                    title=None,
                    form_count=0,
                    input_count=0,
                    textarea_count=0,
                    select_count=0,
                    script_count=0,
                    likely_login_required=True,
                    error=f"{type(exc).__name__}: {exc}",
                )
            )
    return rows


def find_local_browser() -> Optional[str]:
    for path in CHROME_CANDIDATES:
        if os.path.exists(path):
            return path
    return None


async def playwright_extract(site_key: str, headed: bool, wait_seconds: int, browser_path: Optional[str]) -> Dict[str, object]:
    try:
        from playwright.async_api import async_playwright
    except ImportError as exc:
        raise SystemExit(
            "Playwright is not installed. Run:\n"
            "  uv add playwright\n"
            "  uv run playwright install chromium\n"
            "Then rerun this command."
        ) from exc

    target = SITE_TARGETS[site_key]
    start_url = str(target["candidate_urls"][0])

    async with async_playwright() as p:
        launch_options = {"headless": not headed}
        executable_path = browser_path or find_local_browser()
        if executable_path:
            launch_options["executable_path"] = executable_path
        browser = await p.chromium.launch(**launch_options)
        context = await browser.new_context(
            viewport={"width": 1440, "height": 1100},
            locale="ko-KR",
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/126.0 Safari/537.36"
            ),
        )
        page = await context.new_page()
        await page.goto(start_url, wait_until="domcontentloaded", timeout=60_000)

        if headed:
            print("\n브라우저가 열렸습니다.")
            print("로그인이 필요하면 직접 로그인하고 이력서 작성/수정 화면까지 이동하세요.")
            print(f"{wait_seconds}초 후 현재 화면의 폼 요소를 추출합니다.\n")
            await page.wait_for_timeout(wait_seconds * 1000)
        else:
            await page.wait_for_timeout(5000)

        snapshot = await page.evaluate(
            """
            () => {
              const labelTextFor = (el) => {
                const id = el.getAttribute('id');
                const labels = [];
                if (id) {
                  document.querySelectorAll(`label[for="${CSS.escape(id)}"]`).forEach(l => labels.push(l.innerText.trim()));
                }
                if (el.labels) Array.from(el.labels).forEach(l => labels.push(l.innerText.trim()));
                let p = el.parentElement;
                for (let i = 0; p && i < 4; i++, p = p.parentElement) {
                  const ownText = Array.from(p.childNodes)
                    .filter(n => n.nodeType === Node.TEXT_NODE)
                    .map(n => n.textContent.trim())
                    .filter(Boolean)
                    .join(' ');
                  if (ownText) labels.push(ownText);
                  const label = p.querySelector('label');
                  if (label) labels.push(label.innerText.trim());
                }
                return Array.from(new Set(labels.filter(Boolean))).slice(0, 5);
              };
              const cssPath = (el) => {
                if (el.id) return `#${CSS.escape(el.id)}`;
                const parts = [];
                let cur = el;
                while (cur && cur.nodeType === Node.ELEMENT_NODE && parts.length < 6) {
                  let part = cur.nodeName.toLowerCase();
                  if (cur.classList && cur.classList.length) {
                    part += '.' + Array.from(cur.classList).slice(0, 3).map(c => CSS.escape(c)).join('.');
                  }
                  const parent = cur.parentElement;
                  if (parent) {
                    const same = Array.from(parent.children).filter(x => x.nodeName === cur.nodeName);
                    if (same.length > 1) part += `:nth-of-type(${same.indexOf(cur) + 1})`;
                  }
                  parts.unshift(part);
                  cur = parent;
                }
                return parts.join(' > ');
              };
              const visible = (el) => {
                const s = window.getComputedStyle(el);
                const r = el.getBoundingClientRect();
                return s && s.visibility !== 'hidden' && s.display !== 'none' && r.width > 0 && r.height > 0;
              };
              const fields = Array.from(document.querySelectorAll('input, textarea, select, [contenteditable="true"]')).map((el, idx) => ({
                index: idx,
                tag: el.tagName.toLowerCase(),
                type: el.getAttribute('type') || '',
                name: el.getAttribute('name') || '',
                id: el.getAttribute('id') || '',
                placeholder: el.getAttribute('placeholder') || '',
                autocomplete: el.getAttribute('autocomplete') || '',
                aria_label: el.getAttribute('aria-label') || '',
                role: el.getAttribute('role') || '',
                required: el.hasAttribute('required') || el.getAttribute('aria-required') === 'true',
                disabled: el.disabled || el.getAttribute('aria-disabled') === 'true',
                read_only: el.readOnly || el.getAttribute('aria-readonly') === 'true',
                max_length: el.getAttribute('maxlength') || '',
                labels: labelTextFor(el),
                value_preview: (el.value || el.innerText || '').slice(0, 80),
                selector: cssPath(el),
                visible: visible(el)
              }));
              const buttons = Array.from(document.querySelectorAll('button, input[type="button"], input[type="submit"], a')).map((el, idx) => ({
                index: idx,
                tag: el.tagName.toLowerCase(),
                type: el.getAttribute('type') || '',
                text: (el.innerText || el.value || el.getAttribute('aria-label') || '').trim().slice(0, 100),
                href: el.getAttribute('href') || '',
                selector: cssPath(el),
                visible: visible(el)
              })).filter(x => x.text || x.href);
              return {
                url: location.href,
                title: document.title,
                extracted_at: new Date().toISOString(),
                fields,
                buttons
              };
            }
            """
        )
        await browser.close()
        return {
            "site_key": site_key,
            "site_name": target["name"],
            "start_url": start_url,
            "snapshot": snapshot,
        }


def write_json(name: str, payload: object) -> str:
    out_dir = ensure_output_dir()
    path = os.path.join(out_dir, name)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    return path


def static_probe(sites: List[str]) -> List[Dict[str, object]]:
    payload = []
    for site in sites:
        site_key = normalize_site(site)
        payload.extend(asdict(row) for row in static_probe_site(site_key))
    return payload


def default_sites() -> List[str]:
    return ["saramin", "wanted", "jobplanet", "catch", "jobkorea", "linkedin"]


async def main() -> None:
    parser = argparse.ArgumentParser(description="채용 사이트 이력서 폼 요소 수집기")
    parser.add_argument("--sites", nargs="*", default=default_sites(), help="saramin wanted jobplanet catch jobkorea linkedin")
    parser.add_argument("--mode", choices=["static", "playwright"], default="static")
    parser.add_argument("--headed", action="store_true", help="Playwright 브라우저를 보이게 열고 수동 로그인 후 추출")
    parser.add_argument("--wait-seconds", type=int, default=90, help="headed 모드에서 수동 로그인/이동 대기 시간")
    parser.add_argument("--browser-path", default=None, help="Chrome/Edge 실행 파일 경로. 생략하면 로컬 Chrome/Edge 자동 탐색")
    args = parser.parse_args()

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    sites = [normalize_site(site) for site in args.sites]

    if args.mode == "static":
        payload = static_probe(sites)
        path = write_json(f"static_probe_{timestamp}.json", payload)
        print(f"정적 접근 결과 저장: {path}")
        for row in payload:
            status = row.get("status")
            print(
                f"- {row['site_name']} {status} {row['url']} -> {row.get('final_url')} "
                f"inputs={row['input_count']} textareas={row['textarea_count']} selects={row['select_count']} "
                f"login={row['likely_login_required']}"
            )
        return

    for site in sites:
        payload = await playwright_extract(
            site,
            headed=args.headed,
            wait_seconds=args.wait_seconds,
            browser_path=args.browser_path,
        )
        safe_url = re.sub(r"[^a-z0-9]+", "_", site.lower()).strip("_")
        path = write_json(f"{safe_url}_playwright_{timestamp}.json", payload)
        print(f"Playwright 추출 결과 저장: {path}")


if __name__ == "__main__":
    asyncio.run(main())
