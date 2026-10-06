import copy
import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest

from job_agent.browser.filler import FormFiller, approved_actions
from job_agent.browser.mapper import capture_page
from job_agent.browser.session import find_local_browser
from job_agent.sites.application import ApplicationAdapter
from job_agent.sites.registry import SiteRegistry
from job_agent.cli import main


def registry():
    return SiteRegistry(
        {
            "key": "company-example",
            "name": "Example Company",
            "candidate_urls": ["https://careers.example.test/apply"],
            "allowed_origins": ["https://careers.example.test"],
        }
    )


def master():
    return {
        "package": {
            "field_values": {
                "name": "Example User",
                "summary": "Reviewed experience",
                "employment": "Regular",
            },
            "source_evidence": {
                p: [{"source_id": "fixture", "paragraph_index": 0}]
                for p in ["name", "summary", "employment"]
            },
        }
    }


def form():
    return {
        "site_key": "company-example",
        "snapshot": {
            "url": "https://careers.example.test/apply",
            "fields": [
                {
                    "tag": "input",
                    "type": "text",
                    "name": "name",
                    "labels": ["Name"],
                    "selector": "#name",
                    "selector_count": 1,
                    "required": True,
                },
                {
                    "tag": "textarea",
                    "labels": ["Summary"],
                    "selector": "#summary",
                    "selector_count": 1,
                    "max_length": "200",
                },
                {
                    "tag": "textarea",
                    "labels": ["Why this company?"],
                    "selector": "#essay",
                    "selector_count": 1,
                    "required": True,
                },
                {"tag": "input", "type": "file", "selector": "#file", "required": True},
            ],
        },
    }


class CompanyTests(unittest.TestCase):
    def test_cli_register_and_prepare_round_trip(self):
        with (
            tempfile.TemporaryDirectory() as directory,
            contextlib.redirect_stdout(io.StringIO()),
        ):
            folder = Path(directory)
            main(
                [
                    "target-register",
                    "--key",
                    "company-example",
                    "--name",
                    "Example Company",
                    "--url",
                    "https://careers.example.test/apply",
                    "--output-dir",
                    directory,
                ]
            )
            for name, data in [("master", master()), ("form", form())]:
                (folder / f"{name}.json").write_text(json.dumps(data), encoding="utf-8")
            main(
                [
                    "application-prepare",
                    "--target",
                    str(folder / "company-example.json"),
                    "--master",
                    str(folder / "master.json"),
                    "--form-map",
                    str(folder / "form.json"),
                    "--output-dir",
                    str(folder / "output"),
                ]
            )
            self.assertEqual(len(list((folder / "output").glob("*.json"))), 5)
            package = json.loads((folder / "output/package.json").read_text())
            self.assertEqual(package["site"], "company-example")

    def test_exact_origin_boundary_and_isolated_registry(self):
        target = registry()
        self.assertTrue(
            target.matches_url(target.custom_key, "https://careers.example.test/other")
        )
        for url in [
            "https://careers.example.test.attacker.test/",
            "https://other.example.test/",
            "http://careers.example.test/",
            "https://careers.example.test:8443/",
            "https://user:pass@careers.example.test/",
            "file:///resume",
        ]:
            self.assertFalse(target.matches_url(target.custom_key, url))
        with self.assertRaises(ValueError):
            SiteRegistry().normalize(target.custom_key)
        self.assertEqual(target.normalize("원티드"), "wanted")

    def test_bad_profile_rejected(self):
        profile = registry().target("company-example")
        for change in [
            {"key": "../../escape"},
            {"candidate_urls": ["file:///private"]},
            {"allowed_origins": []},
        ]:
            with self.assertRaises(ValueError):
                SiteRegistry({**profile, **change})

    def test_auto_mapping_missing_questions_and_no_approval(self):
        source = master()
        adapter = ApplicationAdapter(registry(), source, form())
        source["package"]["field_values"].clear()
        result = adapter.prepare()
        self.assertEqual(
            result["package"]["package"]["field_values"]["field_0"], "Example User"
        )
        self.assertEqual(result["review"]["missing_fields"][0]["field_id"], "field_2")
        self.assertEqual(result["review"]["unsupported_required"][0]["type"], "file")
        with self.assertRaises(ValueError):
            approved_actions(result["package"], result["mapping"])

    def test_bindings_constraints_evidence_and_stale_form(self):
        captured = form()
        captured["snapshot"]["fields"][1]["max_length"] = "3"
        adapter = ApplicationAdapter(registry(), master(), captured)
        bindings = adapter.prepare()["bindings"]
        bindings["bindings"]["field_1"] = ["summary"]
        result = adapter.prepare(bindings)
        item = next(
            m for m in result["mapping"]["mappings"] if m["package_path"] == "field_1"
        )
        self.assertIn("over_maxlength", item["review_reasons"])
        self.assertEqual(
            result["package"]["package"]["field_values"]["field_1"],
            "Reviewed experience",
        )
        bad = copy.deepcopy(bindings)
        bad["bindings"]["field_1"] = ["invented"]
        with self.assertRaises(ValueError):
            adapter.prepare(bad)
        captured["snapshot"]["fields"][0]["selector"] = "#changed"
        with self.assertRaisesRegex(ValueError, "Form changed"):
            ApplicationAdapter(registry(), master(), captured).prepare(bindings)
        source = master()
        source["package"]["source_evidence"].clear()
        with self.assertRaisesRegex(ValueError, "evidence"):
            ApplicationAdapter(registry(), source, form()).prepare()

    def test_select_labels_convert_without_guessing(self):
        captured = form()
        captured["snapshot"]["fields"][0] = {
            "tag": "select",
            "selector": "#employment",
            "selector_count": 1,
            "options": [{"value": "FULL_TIME", "label": "Regular"}],
        }
        adapter = ApplicationAdapter(registry(), master(), captured)
        bindings = adapter.prepare()["bindings"]
        bindings["bindings"]["field_0"] = ["employment"]
        result = adapter.prepare(bindings)
        self.assertEqual(
            result["package"]["package"]["field_values"]["field_0"], "FULL_TIME"
        )


class CompanyBrowserTests(unittest.IsolatedAsyncioTestCase):
    async def test_unknown_company_capture_adapt_and_fill_without_submission(self):
        from playwright.async_api import async_playwright

        target = registry()
        html = '<label>Name<input id="name" required></label><label>Summary<textarea id="summary" maxlength="200"></textarea></label><label>Why this company?<textarea id="essay" required></textarea></label><input type="file" required><button onclick="window.submitted=true">Submit</button><iframe srcdoc="&lt;input id=child&gt;"></iframe><iframe src="https://unapproved.test/frame"></iframe>'
        async with async_playwright() as p:
            options = {"headless": True}
            executable = find_local_browser()
            if executable:
                options["executable_path"] = executable
            browser = await p.chromium.launch(**options)
            try:
                page = await browser.new_page()
                await page.route(
                    "**/*",
                    lambda route: route.fulfill(
                        body=html
                        if route.request.url.endswith("/apply")
                        else '<input id="foreign">',
                        content_type="text/html",
                    ),
                )
                await page.goto("https://careers.example.test/apply")
                await page.frame_locator("iframe").first.locator("#child").wait_for()
                captured = await capture_page(page, target.custom_key, registry=target)
                self.assertNotIn(
                    "foreign", [f["id"] for f in captured["snapshot"]["fields"]]
                )
                self.assertTrue(
                    any(
                        f.get("error") == "unapproved_origin"
                        for f in captured["snapshot"]["frames"]
                    )
                )
                result = ApplicationAdapter(target, master(), captured).prepare()
                for item in result["mapping"]["mappings"]:
                    item["approved"] = True
                actions = approved_actions(result["package"], result["mapping"])
                filler = FormFiller(
                    page,
                    actions,
                    allowed_url=lambda url: target.matches_url(target.custom_key, url),
                )
                await filler.apply()
                self.assertEqual(
                    await page.locator("#name").input_value(), "Example User"
                )
                self.assertEqual(
                    await page.locator("#summary").input_value(), "Reviewed experience"
                )
                self.assertEqual(await page.locator("#essay").input_value(), "")
                self.assertFalse(await page.evaluate("!!window.submitted"))
                await page.goto("https://unapproved.test/apply")
                with self.assertRaisesRegex(ValueError, "allowed origins"):
                    await filler.preflight()
            finally:
                await browser.close()
