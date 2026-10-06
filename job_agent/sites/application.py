"""Adapt reviewed master facts to a captured company's application form."""

import argparse
from copy import deepcopy
import hashlib
import json

from job_agent.browser.connector import (
    build_mapping,
    candidate_fields,
    flatten_package_values,
    load_json,
)
from job_agent.core.paths import ProjectPaths
from job_agent.core.storage import ArtifactStore
from job_agent.sites.registry import SiteRegistry


def destination(field):
    return (
        tuple(field.get("frame_path") or []),
        tuple(field.get("shadow_hosts") or []),
        field.get("selector"),
    )


class ApplicationAdapter:
    """Keep observations, source facts and unapproved input plans separate."""

    def __init__(self, registry, master, form_map):
        self._master = deepcopy(master)
        self._form = deepcopy(form_map)
        self._site = registry.custom_key
        if not self._site or form_map.get("site_key") != self._site:
            raise ValueError("Capture must belong to the registered company target")
        if not registry.matches_url(
            self._site, form_map.get("snapshot", {}).get("url", "")
        ):
            raise ValueError("Capture URL is outside the registered target")
        self._company = registry.target(self._site)["name"]

    def prepare(self, bindings=None):
        snapshot = self._form["snapshot"]
        fields = candidate_fields(self._form)
        schema = [
            {
                "field_id": f"field_{i}",
                **{
                    k: deepcopy(field.get(k))
                    for k in (
                        "selector",
                        "tag",
                        "type",
                        "labels",
                        "aria_label",
                        "placeholder",
                        "section",
                        "required",
                        "max_length",
                        "pattern",
                        "options",
                        "frame_path",
                        "frame_url",
                        "shadow_hosts",
                        "selector_count",
                        "role",
                        "contenteditable",
                    )
                },
            }
            for i, field in enumerate(fields)
        ]
        for field in schema:
            for key in ("frame_path", "shadow_hosts", "labels", "options"):
                field[key] = field[key] or []
        digest = hashlib.sha256(
            json.dumps(schema, sort_keys=True, ensure_ascii=False).encode()
        ).hexdigest()
        rows = {row["path"]: row for row in flatten_package_values(self._master)}
        master_package = self._master.get("package", self._master)
        evidence = master_package.get("source_evidence", {})
        suggestions = build_mapping(self._master, self._form)
        auto = {}
        for item in suggestions["mappings"]:
            if item["best_match"] and not item["review_reasons"]:
                auto[destination(item["best_match"])] = [item["package_path"]]
        if bindings is not None:
            if bindings.get("schema_digest") != digest:
                raise ValueError("Form changed; regenerate and review bindings")
            selected = bindings.get("bindings", {})
            if not isinstance(selected, dict) or set(selected) - {
                f["field_id"] for f in schema
            }:
                raise ValueError("Bindings contain unknown form fields")
        else:
            selected = {f["field_id"]: auto.get(destination(f), []) for f in schema}

        values, citations, mappings, missing = {}, {}, [], []
        for field in schema:
            key = field["field_id"]
            paths = selected.get(key, [])
            if not isinstance(paths, list) or any(
                not isinstance(p, str) or p not in rows for p in paths
            ):
                raise ValueError(f"Unknown master source path for {key}")
            if not paths:
                missing.append(
                    {
                        "field_id": key,
                        "labels": field["labels"],
                        "required": field["required"],
                        "reason": "needs_reviewed_answer",
                    }
                )
                continue
            if any(not evidence.get(p) for p in paths):
                raise ValueError(f"Source evidence is required for {key}")
            value = "\n\n".join(rows[p]["value"] for p in paths)
            reasons = []
            if field.get("selector_count") != 1:
                reasons.append("non_unique_selector")
            if field.get("tag") == "select":
                options = [
                    o for o in field.get("options") or [] if not o.get("disabled")
                ]
                if not any(o["value"] == value for o in options):
                    matching = [o for o in options if o.get("label") == value]
                    if len(matching) == 1:
                        value = matching[0]["value"]
                    else:
                        reasons.append("invalid_select_option")
            limit = str(field.get("max_length") or "")
            # Browser maxlength counts UTF-16 code units, including emoji pairs.
            if limit.isdigit() and len(value.encode("utf-16-le")) // 2 > int(limit):
                reasons.append("over_maxlength")
            if field.get("role") == "combobox" and field.get("tag") != "select":
                reasons.append("custom_control_manual")
            values[key] = value
            citations[key] = {p: deepcopy(evidence[p]) for p in paths}
            mappings.append(
                {
                    "package_path": key,
                    "source_paths": paths,
                    "package_label": field["labels"],
                    "value_preview": value[:160],
                    "best_match": deepcopy(field),
                    "approved": False,
                    "review_reasons": reasons,
                }
            )
        eligible = {destination(f) for f in fields}
        unsupported = [
            {
                "selector": f.get("selector"),
                "labels": f.get("labels"),
                "type": f.get("type"),
            }
            for f in snapshot.get("fields", [])
            if f.get("required")
            and f.get("visible", True)
            and destination(f) not in eligible
            and f.get("type") not in {"hidden", "password"}
        ]
        return {
            "schema": {
                "site": self._site,
                "url": snapshot["url"],
                "schema_digest": digest,
                "fields": schema,
                "unsupported_required": unsupported,
                "frame_warnings": [
                    f for f in snapshot.get("frames", []) if f.get("error")
                ],
            },
            "bindings": {"schema_digest": digest, "bindings": selected},
            "package": {
                "site": self._site,
                "company": self._company,
                "package": {"field_values": values, "source_evidence": citations},
                "automation_status": "draft_only_no_browser_save",
            },
            "mapping": {
                "package_site": self._site,
                "form_site": self._company,
                "form_url": snapshot["url"],
                "mapping_status": "review_required",
                "schema_digest": digest,
                "mappings": mappings,
            },
            "review": {
                "missing_fields": missing,
                "unsupported_required": unsupported,
                "source_fields": list(rows),
                "notes": [
                    "No answers invented or truncated. All mappings require individual approval.",
                    "New company essays must first be authored and reviewed in the master resume.",
                    "Capture each wizard step separately. Save and submit remain manual.",
                ],
            },
        }


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Adapt a reviewed master to a captured company form"
    )
    parser.add_argument("--target", required=True)
    parser.add_argument("--master", required=True)
    parser.add_argument("--form-map", required=True)
    parser.add_argument("--bindings", help="Reviewed field_id to source_paths JSON")
    parser.add_argument("--output-dir", default="result/company_applications")
    args = parser.parse_args(argv)
    adapter = ApplicationAdapter(
        SiteRegistry.from_file(args.target),
        load_json(args.master),
        load_json(args.form_map),
    )
    result = adapter.prepare(load_json(args.bindings) if args.bindings else None)
    store = ArtifactStore(ProjectPaths().resolve(args.output_dir))
    for name, payload in result.items():
        store.write_json(f"{name}.json", payload)
    print(f"Application draft saved: {ProjectPaths().resolve(args.output_dir)}")
    print(
        f"Mapped: {len(result['mapping']['mappings'])}; missing: {len(result['review']['missing_fields'])}. Review before filling."
    )
