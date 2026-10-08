"""Start the personal connector without exposing accounts to the public site."""

import argparse
import json
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlsplit

from job_agent.browser.session import find_local_browser

DEFAULT_ORIGIN = "https://job-agent-resume-web.vercel.app"


def connector_origin(root):
    path = Path(root) / "connector.json"
    origin = (
        json.loads(path.read_text(encoding="utf-8"))["origin"]
        if path.exists()
        else DEFAULT_ORIGIN
    )
    if not isinstance(origin, str):
        raise ValueError("연결 웹 주소가 올바르지 않습니다.")
    parsed = urlsplit(origin)
    parsed.port  # Reject malformed ports before any setup or browser launch.
    loopback = (
        parsed.scheme == "http"
        and parsed.hostname in {"localhost", "127.0.0.1"}
        and parsed.port
    )
    if (
        not parsed.hostname
        or parsed.scheme != "https"
        and not loopback
        or parsed.username
        or parsed.password
        or parsed.path
        or parsed.query
        or parsed.fragment
    ):
        raise ValueError("connector.json에는 정확한 웹 origin만 지정하세요.")
    return origin


def ensure_browser():
    if find_local_browser():
        return
    from playwright.sync_api import sync_playwright

    with sync_playwright() as playwright:
        installed = Path(playwright.chromium.executable_path).is_file()
    if not installed:
        print("Chrome/Edge가 없어 전용 Chromium을 준비합니다.", flush=True)
        subprocess.run(
            [sys.executable, "-m", "playwright", "install", "chromium"], check=True
        )


def main(argv=None):
    parser = argparse.ArgumentParser(description="Personal resume connector launcher")
    parser.add_argument("--port", type=int, default=8780)
    parser.add_argument("--no-open", action="store_true")
    args = parser.parse_args(argv)
    try:
        origin = connector_origin(Path(__file__).resolve().parents[2])
        ensure_browser()
        print(f"연결을 허용할 웹사이트: {origin}", flush=True)
        print(
            "열린 웹사이트로 돌아가 출력된 로컬 주소를 입력하세요. 종료: Ctrl+C",
            flush=True,
        )
        from job_agent.ui.server import main as start_server

        options = ["--port", str(args.port), "--handoff-origin", origin]
        if args.no_open:
            options.append("--no-open")
        start_server(options)
        return 0
    except (ValueError, KeyError, OSError, subprocess.CalledProcessError):
        print(
            "연결 도구 준비 실패. 인터넷·브라우저 설치·connector.json 주소를 확인하세요.",
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
