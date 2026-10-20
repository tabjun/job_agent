"""Score saved retrieval against an independently reviewed reference, offline.

Reference: {"reviewed_at": "...", "query": "...", "jobs": [
 {"url": "https://...", "site": "wanted", "eligible": true,
  "company": "...", "evidence": "source requirements/deadline"}]}.
Predictions: a retrieval audit JSON or {"jobs": [...]}.
Unknown predictions are reported separately, never silently counted as correct.
"""

import argparse
import json
from pathlib import Path

from job_agent.core.postings import SITES, canonical_url


def evaluate(reference, prediction):
    if not reference.get("reviewed_at") or not isinstance(reference.get("jobs"), list):
        raise ValueError("검수 시점과 원문 근거가 있는 기준 집합이 필요합니다.")
    truth = {}
    for row in reference["jobs"]:
        if (
            type(row.get("eligible")) is not bool
            or not row.get("evidence")
            or row.get("site") not in SITES
        ):
            raise ValueError("기준 공고는 사이트·적합 여부·검수 근거가 필요합니다.")
        key = canonical_url(row["url"])
        if key in truth and truth[key]["eligible"] != row["eligible"]:
            raise ValueError("같은 공고의 검수 결과가 충돌합니다.")
        truth[key] = row
    predicted = prediction.get("result", prediction).get("jobs", [])
    rows = {canonical_url(row["url"]): row for row in predicted}

    def metrics(site=None):
        expected = {
            k
            for k, r in truth.items()
            if r["eligible"] and (site is None or r["site"] == site)
        }
        selected = {k for k, r in rows.items() if site is None or r.get("site") == site}
        labeled = selected & truth.keys()
        correct = expected & selected
        companies = {truth[k].get("company") for k in correct} - {None, "", "원문 확인"}
        return {
            "reference_eligible": len(expected),
            "retrieved": len(selected),
            "matched_eligible": len(correct),
            "missing_urls": sorted(expected - selected),
            "recall_on_reference": len(correct) / len(expected) if expected else None,
            "precision_on_reviewed": len(correct) / len(labeled) if labeled else None,
            "unreviewed_predictions": len(selected - labeled),
            "distinct_confirmed_companies": len(companies),
        }

    return {
        "reviewed_at": reference["reviewed_at"],
        "query": reference.get("query", ""),
        "overall": metrics(),
        "platforms": {site: metrics(site) for site in SITES},
        "note": "고정 기준 집합의 관찰 결과이며 플랫폼 전체 재현율/전반적 정확도가 아닙니다.",
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reference", type=Path, required=True)
    parser.add_argument("--prediction", type=Path, required=True)
    args = parser.parse_args(argv)
    result = evaluate(
        json.loads(args.reference.read_text(encoding="utf-8")),
        json.loads(args.prediction.read_text(encoding="utf-8")),
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return result


if __name__ == "__main__":
    main()
