from pathlib import Path
import tempfile
import unittest

from job_agent.core.paths import ProjectPaths
from job_agent.documents.profile import FORMAT, ResumeProfile
from job_agent.ui.service import WorkspaceService


def sample():
    return {
        "format": FORMAT,
        "fields": [
            {
                "id": "experience_description",
                "label": "경력",
                "value": "운영 경험\nSQL 분석 경험",
                "reviewed": True,
                "evidence": [
                    {
                        "source_id": "fixture",
                        "paragraph_index": 0,
                        "text": "SQL 분석 경험",
                    }
                ],
            }
        ],
    }


class ProfileTests(unittest.TestCase):
    def test_strict_version_types_duplicate_and_review_gate(self):
        for transform in [
            lambda d: d.update(format="future"),
            lambda d: d["fields"].append(d["fields"][0]),
            lambda d: d["fields"][0].update(reviewed="true"),
            lambda d: d["fields"][0].update(evidence=[]),
        ]:
            data = sample()
            transform(data)
            with self.assertRaises(ValueError):
                ResumeProfile(data)
        data = sample()
        data["fields"][0]["reviewed"] = False
        with self.assertRaises(ValueError):
            ResumeProfile(data).package()
        self.assertEqual(ResumeProfile.template().to_dict()["format"], FORMAT)

    def test_round_trip_and_verbatim_source_mapping(self):
        profile = ResumeProfile(sample())
        imported = ResumeProfile.from_package(profile.package())
        self.assertFalse(imported.to_dict()["fields"][0]["reviewed"])
        self.assertEqual(profile.paragraphs()[1]["text"], "SQL 분석 경험")
        self.assertEqual(profile.paragraphs()[1]["field_id"], "experience_description")
        self.assertEqual(
            profile.package()["package"]["source_evidence"]["experience_description"],
            sample()["fields"][0]["evidence"],
        )

    def test_profile_persistence_change_invalidates_review_and_reapproval(self):
        with tempfile.TemporaryDirectory() as folder:
            service = WorkspaceService(ProjectPaths(Path(folder)))
            data = sample()
            data = service.save_profile({"profile": data})
            self.assertFalse(data["fields"][0]["reviewed"])
            data["fields"][0]["reviewed"] = True
            service.save_profile({"profile": data})
            self.assertTrue(service.profile()["fields"][0]["reviewed"])
            result = service.run(
                {"task": "resume", "profile": service.profile(), "keywords": "SQL"}
            )
            self.assertEqual(result["result"]["paragraphs"][0]["text"], "SQL 분석 경험")
            data["fields"][0]["value"] = "수정된 원문"
            self.assertFalse(
                service.save_profile({"profile": data})["fields"][0]["reviewed"]
            )
            self.assertFalse(
                service.import_profile({"document": sample()})["fields"][0]["reviewed"]
            )

    def test_shared_profile_company_conversion(self):
        from test_company_applications import form, master, registry

        with tempfile.TemporaryDirectory() as folder:
            service = WorkspaceService(ProjectPaths(Path(folder)))
            original = master()
            for key, refs in original["package"]["source_evidence"].items():
                for ref in refs:
                    ref["text"] = original["package"]["field_values"][key]
            profile = ResumeProfile.from_package(original, reviewed=True).to_dict()
            one = service.run(
                {
                    "task": "prepare",
                    "master": original,
                    "target": registry().target("company-example"),
                    "form_map": form(),
                }
            )
            two = service.run(
                {
                    "task": "prepare",
                    "profile": profile,
                    "target": registry().target("company-example"),
                    "form_map": form(),
                }
            )
            self.assertEqual(
                one["result"]["package"]["package"]["field_values"],
                two["result"]["package"]["package"]["field_values"],
            )


if __name__ == "__main__":
    unittest.main()
