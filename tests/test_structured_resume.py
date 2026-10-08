from copy import deepcopy
from pathlib import Path
import tempfile
import unittest

from job_agent.core.paths import ProjectPaths
from job_agent.documents.profile import ResumeProfile
from job_agent.documents.sections import SECTIONS, render_items
from job_agent.ui.service import WorkspaceService


def item(key, **values):
    return {
        **{
            f["key"]: False if f["type"] == "checkbox" else ""
            for f in SECTIONS[key]["fields"]
        },
        **values,
    }


def profile():
    data = ResumeProfile.template().to_dict()
    facts = {
        "experience_description": [
            item(
                "experience_description",
                company="Fixture Corp",
                start="2024-02",
                current=True,
                description="SQL report\nsecond line",
            )
        ],
        "skills": [item("skills", name="Python"), item("skills", name="SQL")],
        "certifications": [
            item(
                "certifications",
                name="Fixture Certificate",
                number="TEST-001",
                issuer="Fixture",
                acquired="2024-02-29",
            )
        ],
        "awards": [item("awards", name="Fixture Award")],
    }
    for row in data["fields"]:
        if row["id"] in facts:
            row["items"] = facts[row["id"]]
            row["value"] = render_items(row["id"], row["items"])
            row["reviewed"] = True
            row["evidence"] = [
                {"source_id": "fixture", "paragraph_index": 0, "text": row["value"]}
            ]
    return data


class StructuredProfileTests(unittest.TestCase):
    def test_package_and_atomic_records(self):
        data = profile()
        parsed = ResumeProfile(data)
        self.assertEqual(parsed.to_dict(), data)
        values = parsed.package()["package"]["field_values"]
        self.assertIn("TEST-001", values["award_certification_description"])
        self.assertIn("Fixture Award", values["award_certification_description"])
        self.assertEqual(
            len(
                [
                    p
                    for p in parsed.paragraphs()
                    if p["field_id"] == "experience_description"
                ]
            ),
            1,
        )

    def test_invalid_schema_dates_current_and_text_mismatch(self):
        for update in (
            {"start": "2024-99"},
            {"end": "2023-01", "current": False},
            {"end": "2025-01"},
            {"current": "true"},
            {"employment": "invented"},
        ):
            data = profile()
            row = next(r for r in data["fields"] if r["id"] == "experience_description")
            row["items"][0].update(update)
            row["value"] = render_items(row["id"], row["items"])
            with self.assertRaises(ValueError):
                ResumeProfile(data)
        data = profile()
        data["fields"][2]["value"] = "forged"
        with self.assertRaises(ValueError):
            ResumeProfile(data)
        data = profile()
        row = next(r for r in data["fields"] if r["id"] == "certifications")
        row["items"][0]["acquired"] = "2023-02-29"
        row["value"] = render_items(row["id"], row["items"])
        with self.assertRaises(ValueError):
            ResumeProfile(data)

    def test_draft_identity_and_change_review_gate(self):
        with tempfile.TemporaryDirectory() as folder:
            service = WorkspaceService(ProjectPaths(Path(folder)), ephemeral=True)
            data = service.save_profile({"profile": profile()})
            for row in data["fields"]:
                row["reviewed"] = bool(row["value"])
            data = service.save_profile({"profile": data})
            next(r for r in data["fields"] if r["id"] == "skills")["items"][0][
                "name"
            ] = ""
            row = next(r for r in data["fields"] if r["id"] == "skills")
            row["items"][0]["description"] = "draft"
            row["value"] = render_items("skills", row["items"])
            changed = service.save_profile({"profile": data})
            self.assertFalse(
                next(r for r in changed["fields"] if r["id"] == "skills")["reviewed"]
            )
            with self.assertRaises(ValueError):
                ResumeProfile(changed).package()

    def test_organized_profile_keeps_entities_and_original(self):
        data = profile()
        original = deepcopy(data)
        result = WorkspaceService._resume({"profile": data, "keywords": "SQL"})
        self.assertEqual(data, original)
        ordered = next(
            r for r in result["organized_profile"]["fields"] if r["id"] == "skills"
        )
        self.assertEqual(ordered["items"][0]["name"], "SQL")
        ResumeProfile(result["organized_profile"]).package()
