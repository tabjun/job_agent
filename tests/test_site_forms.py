import unittest

from job_agent.browser.connector import build_mapping, flatten_package_values
from job_agent.browser.mapper import capture_page
from job_agent.browser.session import find_local_browser
from job_agent.sites.registry import default_sites, site_matches_url
from job_agent.browser.filler import approved_actions, FormFiller


class MappingTests(unittest.TestCase):
    def test_only_explicitly_reviewed_fields_are_executable(self):
        package = {"field_values": {"summary": "Example"}}
        plan = {
            "mappings": [
                {"package_path": "summary", "best_match": {"selector": "#editor"}}
            ]
        }
        with self.assertRaises(ValueError):
            approved_actions(package, plan)
        plan["mappings"][0]["approved"] = True
        self.assertEqual(approved_actions(package, plan)[0]["value"], "Example")

    def test_targets_and_domain_boundaries(self):
        self.assertEqual(
            default_sites(), ["catch", "jobkorea", "saramin", "wanted", "incruit"]
        )
        self.assertTrue(
            site_matches_url("incruit", "https://people.incruit.com/resume")
        )
        self.assertFalse(
            site_matches_url("incruit", "https://incruit.com.example.org/")
        )

    def test_zero_is_preserved(self):
        rows = flatten_package_values({"field_values": {"experience_months": 0}})
        self.assertEqual(rows[0]["value"], "0")

    def test_ineligible_and_unrelated_fields_do_not_match(self):
        fields = [
            {"tag": "input", "type": "password", "name": "name"},
            {"tag": "input", "name": "name", "disabled": True},
            {"tag": "input", "name": "name", "visible": False},
            {"tag": "input", "name": "name", "read_only": True},
            {"tag": "input", "name": "search"},
        ]
        result = build_mapping(
            {"field_values": {"name": "Example"}}, {"fields": fields}
        )
        self.assertEqual(result["unmatched_count"], 1)

    def test_shared_editor_and_limits_require_review(self):
        result = build_mapping(
            {"field_values": {"summary": ["long text", "second text"]}},
            {
                "fields": [
                    {
                        "tag": "div",
                        "contenteditable": True,
                        "aria_label": "summary",
                        "selector": "#editor",
                        "frame_path": [0],
                        "max_length": "3",
                    }
                ]
            },
        )
        self.assertEqual(result["unmatched_count"], 0)
        for item in result["mappings"]:
            self.assertIn("shared_destination", item["review_reasons"])
            self.assertIn("over_maxlength:3", item["review_reasons"])
            self.assertEqual(item["best_match"]["frame_path"], [0])


class SnapshotTests(unittest.IsolatedAsyncioTestCase):
    async def test_real_dom_duplicate_ids_frames_shadow_and_redaction(self):
        from playwright.async_api import async_playwright

        async with async_playwright() as p:
            options = {"headless": True}
            executable = find_local_browser()
            if executable:
                options["executable_path"] = executable
            browser = await p.chromium.launch(**options)
            try:
                page = await browser.new_page()
                await page.set_content("""
                  <section><h2>Education</h2>
                    <label>School <input id="duplicate" value="PRIVATE"></label>
                    <label>School <input id="duplicate" value="SECOND"></label>
                  </section>
                  <input id="secret" type="password" value="SECRET">
                  <input id="token" type="hidden" value="TOKEN">
                  <select id="choice"><option value="one">One</option></select>
                  <div id="editor" contenteditable="true" aria-label="summary">Private summary</div>
                  <div id="shadow"></div>
                  <input placeholder="First&#10;Second">
                  <iframe srcdoc="<textarea id='child' maxlength='10'></textarea>"></iframe>
                """)
                await page.locator("#shadow").evaluate(
                    "e => { e.attachShadow({mode:'open'}).innerHTML = '<input id=inside><input><input>'; }"
                )
                await page.frame_locator("iframe").locator("#child").wait_for()
                payload = await capture_page(page, "catch")
                fields = payload["snapshot"]["fields"]
                duplicates = [field for field in fields if field["id"] == "duplicate"]
                self.assertEqual(len(duplicates), 2)
                self.assertNotEqual(
                    duplicates[0]["selector"], duplicates[1]["selector"]
                )
                self.assertTrue(all(field["selector_count"] == 1 for field in fields))
                self.assertTrue(all(field["value_preview"] == "" for field in fields))
                self.assertEqual(
                    next(f for f in fields if f["id"] == "child")["frame_path"], [0]
                )
                self.assertEqual(
                    next(f for f in fields if f["id"] == "inside")["shadow_hosts"],
                    ["#shadow"],
                )
                self.assertEqual(
                    next(f for f in fields if f["id"] == "choice")["options"][0][
                        "value"
                    ],
                    "one",
                )
                with_values = (await capture_page(page, "catch", True))["snapshot"][
                    "fields"
                ]
                self.assertEqual(
                    next(f for f in with_values if f["id"] == "duplicate")[
                        "value_preview"
                    ],
                    "PRIVATE",
                )
                self.assertEqual(
                    next(f for f in with_values if f["id"] == "secret")[
                        "value_preview"
                    ],
                    "",
                )
                self.assertEqual(
                    next(f for f in with_values if f["id"] == "token")["value_preview"],
                    "",
                )
                actions = [
                    {
                        "path": "summary",
                        "value": "Reviewed text",
                        "target": {"selector": "#editor"},
                    },
                    {
                        "path": "choice",
                        "value": "one",
                        "target": {"selector": "#choice"},
                    },
                    {
                        "path": "child",
                        "value": "Nested",
                        "target": {
                            "selector": "#child",
                            "frame_path": [0],
                            "frame_url": page.frames[1].url,
                        },
                    },
                ]
                await FormFiller(page, actions).apply()
                self.assertEqual(
                    await page.locator("#editor").inner_text(), "Reviewed text"
                )
                self.assertEqual(
                    await page.frame_locator("iframe").locator("#child").input_value(),
                    "Nested",
                )
                with self.assertRaises(ValueError):
                    await FormFiller(
                        page,
                        [
                            actions[0],
                            {
                                **actions[0],
                                "target": {"selector": "div[contenteditable]"},
                            },
                        ],
                    ).preflight()
                with self.assertRaises(ValueError):
                    await FormFiller(
                        page, [{**actions[2], "value": "x" * 11}]
                    ).preflight()
                with self.assertRaises(ValueError):
                    await FormFiller(
                        page,
                        [
                            {
                                "path": "secret",
                                "value": "no",
                                "target": {"selector": "#secret"},
                            }
                        ],
                    ).preflight()
            finally:
                await browser.close()


if __name__ == "__main__":
    unittest.main()
