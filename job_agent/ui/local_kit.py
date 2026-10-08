"""Distribute application code only, never operator data or browser sessions."""

import json
from io import BytesIO
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

from job_agent.ui.launcher import DEFAULT_ORIGIN
from job_agent.ui.tutorials import TUTORIAL_IMAGES


def local_kit():
    root = Path(__file__).resolve().parents[2]
    package = root / "job_agent"
    buffer = BytesIO()
    with ZipFile(buffer, "w", ZIP_DEFLATED) as archive:
        for path in sorted(package.rglob("*")):
            if not path.is_file() or not path.resolve().is_relative_to(package):
                continue
            relative = path.relative_to(root)
            tutorial = (
                path.parent == package / "ui" / "static" / "tutorials"
                and path.name in TUTORIAL_IMAGES
            )
            if (
                path.suffix != ".py"
                and path.parent != package / "ui" / "static"
                and not tutorial
            ):
                continue
            if path.is_symlink() or "__pycache__" in relative.parts:
                continue
            archive.writestr(str(relative).replace("\\", "/"), path.read_bytes())
        for name in ["pyproject.toml", "uv.lock"]:
            archive.writestr(name, (root / name).read_bytes())
        archive.writestr(
            "Start-Resume-Connector.cmd",
            (package / "ui" / "connector-start.cmd")
            .read_text(encoding="utf-8")
            .replace("\n", "\r\n")
            .encode("utf-8"),
        )
        archive.writestr("connector.json", json.dumps({"origin": DEFAULT_ORIGIN}))
        archive.writestr(
            "START-HERE.txt",
            "Windows 시작하기\n\nZIP 우클릭 → 모두 압축 풀기 → Start-Resume-Connector.cmd 더블클릭.\n첫 실행에는 인터넷이 필요합니다. uv 설치 질문은 Y/N으로 직접 선택하세요.\n준비 후 브라우저가 열리며 창에 로컬 주소가 표시됩니다. 사용 중 실행 창을 유지하세요.\n종료: Ctrl+C. 로그인·2차 인증은 전용 브라우저에서 직접 수행하세요.\n보안 경고/조직 정책을 우회하지 마세요. 실행이 막히면 README의 수동 설치 안내를 사용하세요.\n",
        )
        archive.writestr(
            "README.md",
            "# Resume Workspace Local Connector\n\nWindows: ZIP 우클릭 → 모두 압축 풀기 → Start-Resume-Connector.cmd 더블클릭. EXE가 아닌 명령 실행 파일입니다. uv가 없으면 공식 WinGet 설치를 물으며 설치 동의는 직접 선택합니다. 첫 실행은 인터넷이 필요합니다. 실행 창을 유지하고 Ctrl+C로 종료합니다. 보안 경고/관리자 정책을 우회하지 마세요.\n\n수동 실행: 압축을 푼 폴더 빈 곳에서 Shift+우클릭 → 터미널에서 열기(PowerShell). uv 설치 후 아래 명령을 한 줄씩 실행합니다.\n\n```powershell\nwinget install --id astral-sh.uv --exact\n# 설치 뒤 터미널을 다시 열기\nuv sync --locked --extra browser\nuv run --no-sync python -m job_agent.ui.launcher\n```\n\nLinux/macOS: 공식 안내로 uv를 설치하고 압축 폴더의 터미널에서 동일한 마지막 두 명령을 실행합니다. Linux 브라우저 실행에 시스템 의존성이 필요하면 관리자에게 확인합니다.\n\n공식 설치 안내: https://docs.astral.sh/uv/getting-started/installation/\n\n웹으로 돌아가 실행 창의 실제 로컬 주소를 입력하세요. 가져오기 승인·재검수 후 전용 브라우저에서 직접 로그인·2차 인증합니다. 공개 웹에 비밀번호·OTP·쿠키를 입력하지 않습니다. 로컬 자료·세션은 본인 PC result/에 저장됩니다. 공용 PC를 피하고 완료 후 전용 브라우저에서 로그아웃하세요. connector.json의 origin은 연결할 정확한 웹 출처이며 광범위 허용으로 변경하지 마세요.\n",
        )
    return buffer.getvalue()
