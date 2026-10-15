"""Explicit live search audit or offline replay; never sends mail or invokes LLMs."""

import argparse
import json
import threading
from datetime import datetime
from pathlib import Path

from job_agent.core.paths import ProjectPaths, load_environment
from job_agent.core.postings import SITES
from job_agent.ui.service import WorkspaceService


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument(
        "--live",
        action="store_true",
        help="Use owner's search key; up to 3 queries per selected site",
    )
    mode.add_argument(
        "--replay", type=Path, help="Replay an audit JSON without network or keys"
    )
    parser.add_argument("--role", default="데이터 분석가")
    parser.add_argument("--location", default="서울, 경기")
    parser.add_argument("--keywords", default="Python, SQL")
    parser.add_argument("--sites", nargs="+", choices=list(SITES), default=list(SITES))
    args = parser.parse_args(argv)
    payload = {
        "source": "web",
        "role": args.role,
        "location": args.location,
        "keywords": args.keywords,
        "sites": args.sites,
        "search_consent": True,
    }
    captures = []
    lock = threading.Lock()
    if args.live:
        load_environment()

        def search(query, domains):
            rows = WorkspaceService._web_search(query, domains)
            with lock:
                captures.append({"query": query, "domains": domains, "rows": rows})
            return rows
    else:
        original = json.loads(args.replay.read_text(encoding="utf-8"))
        payload = original["payload"]
        captures = original["searches"]

        def search(query, domains):
            return next(
                record["rows"]
                for record in captures
                if record["query"] == query and record["domains"] == domains
            )

    service = WorkspaceService(searcher=search, ephemeral=True)
    # Replay deliberately avoids needing a private key; production consent gates stay unchanged.
    if args.replay:
        service.config = lambda: {"web_search": True}
    try:
        result = service._search(payload)
    finally:
        service.close()
    labels = {job["company"] for job in result["jobs"]} - {"원문 확인"}
    summary = {
        **result["coverage"],
        "distinct_company_labels": len(labels),
        "unknown_company_rows": sum(
            j["company"] == "원문 확인" for j in result["jobs"]
        ),
    }
    folder = ProjectPaths().results / "search_quality"
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"audit-{datetime.now():%Y%m%d-%H%M%S-%f}.json"
    path.write_text(
        json.dumps(
            {
                "payload": payload,
                "searches": captures,
                "result": result,
                "summary": summary,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print(json.dumps(summary, ensure_ascii=False))
    print(f"Evidence: {path}")
    return path


if __name__ == "__main__":
    main()
