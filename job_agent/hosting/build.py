"""Create a new code-only deploy directory; keep the existing app untouched."""

import argparse
import hashlib
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

from job_agent.documents.profile import ResumeProfile
from job_agent.documents.sections import SECTIONS
from job_agent.ui.local_kit import local_kit
from job_agent.ui.page import remote_page
from job_agent.ui.tutorials import TUTORIAL_IMAGES

ROOT = Path(__file__).resolve().parents[2]
RUNTIME = [
    "__init__.py",
    "core/__init__.py",
    "core/paths.py",
    "core/storage.py",
    "documents/__init__.py",
    "documents/source.py",
    "documents/profile.py",
    "documents/sections.py",
    "browser/__init__.py",
    "browser/connector.py",
    "sites/__init__.py",
    "sites/registry.py",
    "sites/application.py",
    "ui/__init__.py",
    "ui/models.py",
    "ui/service.py",
    "hosting/__init__.py",
    "hosting/handler.py",
]


def stamp():
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")


def private_backup():
    folder = ROOT / "result" / "hosting" / "backups"
    folder.mkdir(parents=True, exist_ok=True)
    target = folder / f"local-environment-{stamp()}.zip"
    selected = [
        ROOT / name
        for name in [
            "AGENTS.md",
            "skills.md",
            "process.md",
            "history.md",
            "conversation_l2_cache.md",
            "README.md",
            "pyproject.toml",
            "uv.lock",
            "requirements.txt",
            ".gitignore",
            ".env",
        ]
    ]
    for name in ["job_agent", "tests", "docs", "deploy"]:
        selected.extend((ROOT / name).rglob("*"))
    with ZipFile(target, "x", ZIP_DEFLATED) as archive:
        for path in sorted(set(selected)):
            if (
                path.is_file()
                and not path.is_symlink()
                and path.resolve().is_relative_to(ROOT)
                and "__pycache__" not in path.parts
            ):
                archive.write(path, path.relative_to(ROOT).as_posix())
        archive.writestr(
            "BACKUP-NOTICE.txt",
            "PRIVATE local snapshot: may contain .env secrets. Never upload.\n"
            "Existing personal documents/results/browser profiles stay in place.\n"
            "Virtualenv is not copied: restore dependencies with uv sync --locked --extra browser.\n",
        )
    return target


def build(output=None, privacy_contact=""):
    output = Path(output or ROOT / "result" / "hosting" / f"vercel-{stamp()}").resolve()
    if output.exists() and any(output.iterdir()):
        raise ValueError(
            "Output must be new or empty; existing files are not overwritten"
        )
    if output == ROOT or output in ROOT.parents:
        raise ValueError("Cannot export over the original workspace")
    output.mkdir(parents=True, exist_ok=True)
    public = output / "public"
    public.mkdir()
    static = ROOT / "job_agent" / "ui" / "static"
    for name in [
        "style.css",
        "lucide.min.js",
        "app.js",
        "handoff.js",
        "portals.js",
        "resume-forms.js",
        "resume-files.js",
        "fflate.min.js",
        "fflate.LICENSE.txt",
        "tutorials.js",
    ]:
        shutil.copy2(static / name, public / name)
    (public / "tutorials").mkdir()
    for name in TUTORIAL_IMAGES:
        shutil.copy2(static / "tutorials" / name, public / "tutorials" / name)
    page = remote_page(
        (static / "index.html").read_text(encoding="utf-8"), ["none"]
    ).decode()
    page = page.replace(
        '<script defer src="/app.js">',
        '<script defer src="/cloud.js"></script><script defer src="/app.js">',
    )
    (public / "index.html").write_text(page, encoding="utf-8")
    shutil.copy2(ROOT / "deploy" / "vercel" / "cloud.js", public / "cloud.js")
    (public / "workspace-config.json").write_text(
        json.dumps(
            {
                "template": ResumeProfile.template().to_dict(),
                "schema": SECTIONS,
                "privacy_contact": privacy_contact,
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    (public / "resume-local-connector.zip").write_bytes(local_kit())
    for name in RUNTIME:
        source = ROOT / "job_agent" / name
        if source.is_symlink() or not source.resolve().is_relative_to(
            ROOT / "job_agent"
        ):
            raise ValueError("Runtime sources must be local code files")
        target = output / "job_agent" / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
    api = output / "api"
    api.mkdir()
    (api / "run.py").write_text(
        "from job_agent.hosting.handler import handler as PublicHandler\n\n"
        "class handler(PublicHandler):\n    pass\n",
        encoding="utf-8",
    )
    for name in ["vercel.json", "requirements.txt", "environment.example"]:
        shutil.copy2(ROOT / "deploy" / "vercel" / name, output / name)
    (output / ".python-version").write_text("3.12\n", encoding="utf-8")
    (output / ".vercelignore").write_text(
        ".env*\n.venv\n.git\n.vercel\n__pycache__\nresult\nknowledge\nmore_info\n",
        encoding="utf-8",
    )
    files = {
        path.relative_to(output).as_posix(): hashlib.sha256(
            path.read_bytes()
        ).hexdigest()
        for path in output.rglob("*")
        if path.is_file()
    }
    (output / "export-manifest.json").write_text(
        json.dumps(
            {
                "format": "job-agent.public-export/v1",
                "data_policy": "browser_session_memory_and_stateless_request",
                "files": files,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    return output


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Export a code-only public Vercel bundle"
    )
    parser.add_argument("--output")
    parser.add_argument("--privacy-contact", default="")
    parser.add_argument(
        "--backup",
        action="store_true",
        help="Also create a private local environment snapshot",
    )
    args = parser.parse_args(argv)
    if args.backup:
        print(f"PRIVATE backup (never upload): {private_backup()}")
    print(f"Public code-only export: {build(args.output, args.privacy_contact)}")


if __name__ == "__main__":
    main()
