import unittest

from job_agent.examples.retrieval_eval import evaluate


class RetrievalEvalTests(unittest.TestCase):
    def test_missing_wrong_and_unreviewed_are_not_confused_with_recall(self):
        truth = {
            "reviewed_at": "2026-10-20",
            "query": "SQL",
            "jobs": [
                {
                    "url": f"https://www.wanted.co.kr/wd/{i}",
                    "site": "wanted",
                    "eligible": eligible,
                    "company": str(i),
                    "evidence": "public detail manually reviewed",
                }
                for i, eligible in [(1, True), (2, True), (3, False)]
            ],
        }
        predictions = {
            "jobs": [
                {"url": f"https://www.wanted.co.kr/wd/{i}", "site": "wanted"}
                for i in [1, 3, 4]
            ]
        }
        result = evaluate(truth, predictions)["overall"]
        self.assertEqual(result["recall_on_reference"], 0.5)
        self.assertEqual(result["precision_on_reviewed"], 0.5)
        self.assertEqual(result["unreviewed_predictions"], 1)
        self.assertEqual(len(result["missing_urls"]), 1)

    def test_unreviewed_reference_is_rejected(self):
        with self.assertRaises(ValueError):
            evaluate({"jobs": []}, {"jobs": []})
