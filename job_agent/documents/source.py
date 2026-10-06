"""Extract DOCX evidence and build source-only browser test packages."""

import argparse
import hashlib
from pathlib import Path
from xml.etree import ElementTree as ET
from zipfile import ZipFile

from job_agent.sites.registry import default_sites
from job_agent.core.paths import ProjectPaths
from job_agent.core.storage import ArtifactStore


WORD_NS = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}


class DocxReader:
    def __init__(self, source):
        self.path = Path(source).resolve()

    @property
    def sha256(self):
        return hashlib.sha256(self.path.read_bytes()).hexdigest()

    def read(self):
        with ZipFile(self.path) as archive:
            root = ET.fromstring(archive.read("word/document.xml"))
        body = root.find("w:body", WORD_NS)
        if body is None:
            raise ValueError("DOCX has no document body")
        paragraphs = []
        for index, paragraph in enumerate(body.findall(".//w:p", WORD_NS)):
            # Deleted revision text uses w:delText, not w:t.
            text = "".join(
                node.text or "" for node in paragraph.findall(".//w:t", WORD_NS)
            ).strip()
            if text:
                paragraphs.append({"paragraph_index": index, "text": text})
        if not paragraphs:
            raise ValueError("DOCX contains no readable body paragraphs")
        return paragraphs


def career_evidence(paragraphs):
    starts = [i for i, row in enumerate(paragraphs) if row["text"] == "경력사항"]
    if len(starts) != 1:
        raise ValueError(
            "Expected one explicit career section; review extracted Markdown"
        )
    start = starts[0] + 1
    end = next(
        (
            i
            for i in range(start, len(paragraphs))
            if paragraphs[i]["text"] == "핵심역량"
        ),
        None,
    )
    if end is None:
        raise ValueError("Career section end is missing; review extracted Markdown")
    rows = paragraphs[start:end]
    roles = [i for i, row in enumerate(rows) if row["text"] == "역할"]
    if len(roles) != 1:
        raise ValueError("Expected one role block; review extracted Markdown")
    description_rows = rows[roles[0] + 1 :]
    if not description_rows:
        raise ValueError("Career description is empty")
    return description_rows


def summary_evidence(paragraphs):
    starts = [
        i
        for i, row in enumerate(paragraphs)
        if row["text"] == "Github / Notion portfolio"
    ]
    if len(starts) != 1:
        raise ValueError("Expected one summary boundary; review extracted Markdown")
    start = starts[0] + 1
    end = next(
        (
            i
            for i in range(start, len(paragraphs))
            if paragraphs[i]["text"] == "Profile"
        ),
        None,
    )
    if end is None or end == start:
        raise ValueError("Summary section is missing; review extracted Markdown")
    return paragraphs[start:end]


def build_source_package(source, paragraphs, site):
    evidence = career_evidence(paragraphs)
    summary = summary_evidence(paragraphs)
    return {
        "site": site,
        "company": "source_resume_test",
        "source": {"file": Path(source).name, "sha256": DocxReader(source).sha256},
        "package": {
            "field_values": {
                "experience": {
                    "description": "\n".join(row["text"] for row in evidence)
                },
                "summary": "\n".join(row["text"] for row in summary),
            },
            "source_evidence": {"experience.description": evidence, "summary": summary},
            "generation_method": "verbatim_docx_extraction",
        },
    }


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="DOCX 원문 추출 및 사실 그대로의 경력 입력 테스트 패키지"
    )
    parser.add_argument("--source", required=True)
    parser.add_argument("--output-dir", default="result/source_resume_test")
    args = parser.parse_args(argv)
    paths = ProjectPaths()
    source = paths.resolve(args.source)
    paragraphs = DocxReader(source).read()
    output = paths.resolve(args.output_dir)
    store = ArtifactStore(output)
    store.write_text(
        "resume_source.md", "\n\n".join(row["text"] for row in paragraphs) + "\n"
    )
    store.write_json("resume_evidence.json", paragraphs)
    for site in default_sites():
        package = build_source_package(source, paragraphs, site)
        store.write_json(f"{site}_package.json", package)
    description = build_source_package(source, paragraphs, "catch")["package"][
        "field_values"
    ]["experience"]["description"]
    print(
        f"Extracted {len(paragraphs)} paragraphs; career description {len(description)} chars; {len(default_sites())} site packages"
    )
    print(f"Local output: {output.resolve()}")


if __name__ == "__main__":
    main()
