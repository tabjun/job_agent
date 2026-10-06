"""Extract explicitly selected DOCX sources and compile an evidence-linked draft."""

import argparse
from copy import deepcopy
import json
from pathlib import Path

from job_agent.documents.source import DocxReader
from job_agent.sites.registry import default_sites
from job_agent.core.paths import ProjectPaths
from job_agent.core.storage import ArtifactStore


class ResumeLibrary:
    """Own source evidence and revalidate it before compiling reviewed fields."""

    def __init__(self, corpus):
        self._corpus = deepcopy(corpus)

    def to_dict(self):
        return deepcopy(self._corpus)

    @classmethod
    def from_sources(cls, paths):
        sources = []
        seen = set()
        for raw in paths:
            path = Path(raw).resolve()
            if path.suffix.lower() != ".docx":
                raise ValueError("Only explicitly selected DOCX sources are supported")
            reader = DocxReader(path)
            digest = reader.sha256
            if digest in seen:
                continue
            seen.add(digest)
            sources.append(
                {
                    "id": f"source_{len(sources) + 1}",
                    "file": str(path),
                    "sha256": digest,
                    "paragraphs": reader.read(),
                }
            )
        if not sources:
            raise ValueError("Select at least one readable source")
        return cls({"sources": sources})

    def compile(self, draft):
        sources = {}
        for source in self._corpus["sources"]:
            if source["id"] in sources:
                raise ValueError("Duplicate source id")
            if DocxReader(source["file"]).sha256 != source["sha256"]:
                raise ValueError("Source changed; extract and review again")
            if DocxReader(source["file"]).read() != source["paragraphs"]:
                raise ValueError("Extracted evidence differs from source")
            sources[source["id"]] = source
        values, evidence = {}, {}
        for block in draft["blocks"]:
            key = block["field"]
            if (
                key in values
                or not isinstance(block["text"], str)
                or not block["text"].strip()
            ):
                raise ValueError("Duplicate field or empty draft text")
            if not block.get("evidence"):
                raise ValueError(f"No source evidence for {key}")
            citations = []
            for ref in block["evidence"]:
                source = sources.get(ref["source_id"])
                if source is None:
                    raise ValueError("Unknown source reference")
                rows = {row["paragraph_index"]: row for row in source["paragraphs"]}
                for index in ref["paragraph_indices"]:
                    if index not in rows:
                        raise ValueError("Unknown paragraph reference")
                    citations.append(
                        {
                            "source_id": source["id"],
                            "paragraph_index": index,
                            "text": rows[index]["text"],
                        }
                    )
            if not citations:
                raise ValueError("Empty evidence reference")
            values[key] = block["text"]
            evidence[key] = citations
        if not values:
            raise ValueError("Draft contains no blocks")
        return {
            "field_values": values,
            "source_evidence": evidence,
            "generation_method": "human_reviewed_evidence_linked_draft",
            "review_notes": draft.get("review_notes", []),
        }


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Explicit DOCX library and reviewed resume draft"
    )
    sub = parser.add_subparsers(dest="command", required=True)
    extract = sub.add_parser("extract")
    extract.add_argument("--source", action="append", required=True)
    extract.add_argument("--output-dir", default="result/resume_library")
    build = sub.add_parser("build")
    build.add_argument("--corpus", required=True)
    build.add_argument("--draft", required=True)
    build.add_argument("--output-dir", default="result/master_resume")
    args = parser.parse_args(argv)
    paths = ProjectPaths()
    output = ArtifactStore(paths.resolve(args.output_dir))
    if args.command == "extract":
        corpus = ResumeLibrary.from_sources(
            [paths.resolve(source) for source in args.source]
        ).to_dict()
        output.write_json("corpus.json", corpus)
        for source in corpus["sources"]:
            output.write_text(
                f"{source['id']}.md",
                "\n\n".join(
                    f"[{row['paragraph_index']}] {row['text']}"
                    for row in source["paragraphs"]
                )
                + "\n",
            )
        print(f"Extracted {len(corpus['sources'])} explicitly selected sources")
    else:
        corpus = json.loads(paths.resolve(args.corpus).read_text(encoding="utf-8"))
        draft = json.loads(paths.resolve(args.draft).read_text(encoding="utf-8"))
        package = ResumeLibrary(corpus).compile(draft)
        output.write_json("master_resume.json", {"package": package})
        output.write_text(
            "master_resume.md",
            "\n\n".join(
                f"## {block.get('heading', block['field'])}\n\n{block['text']}"
                for block in draft["blocks"]
            )
            + "\n",
        )
        for site in default_sites():
            output.write_json(
                f"{site}_package.json", {"site": site, "package": package}
            )
        print(
            f"Compiled {len(package['field_values'])} reviewed fields for {len(default_sites())} sites"
        )


if __name__ == "__main__":
    main()
