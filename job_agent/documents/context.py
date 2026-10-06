"""Read factual source context without coupling it to an LLM workflow."""

import subprocess

from job_agent.core.paths import ProjectPaths
from job_agent.documents.source import DocxReader


class UserContextLoader:
    def __init__(self, paths=None, converter=None):
        self.paths = paths or ProjectPaths()
        self._converter = converter or self._convert

    @staticmethod
    def _convert(path):
        return subprocess.run(
            ["npx", "kordoc", str(path)],
            capture_output=True,
            text=True,
            check=True,
            encoding="utf-8",
        ).stdout

    def load(self):
        parts = ["=== [사용자 원본 이력 및 경력 (knowledge)] ===\n"]
        for pattern in ["*.txt", "*.hwp", "*.hwpx", "*.pdf", "*.docx"]:
            for path in sorted(self.paths.knowledge.glob(pattern)):
                try:
                    if path.suffix == ".txt":
                        content = path.read_text(encoding="utf-8")
                    elif path.suffix == ".docx":
                        content = "\n".join(
                            row["text"] for row in DocxReader(path).read()
                        )
                    else:
                        content = self._converter(path)
                except Exception as exc:
                    content = f"(문서 파싱 실패: {exc})"
                parts.append(f"\n--- 파일: {path.name} ---\n{content}\n")
        parts.append("\n=== [자소서 작성 가이드라인 및 개인 철학 (more_info)] ===\n")
        for path in sorted(self.paths.guidelines.glob("*.txt")):
            parts.append(path.read_text(encoding="utf-8") + "\n\n")
        return "".join(parts)
