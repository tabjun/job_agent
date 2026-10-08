import json
import os
import unittest
from unittest.mock import Mock, patch

import httpx
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI

from job_agent.core.engine import LangGraphAgentEngine


class ModelConfigurationTests(unittest.TestCase):
    def test_default_luna_uses_responses_without_sampling_or_storage(self):
        with (
            patch.dict(os.environ, {}, clear=True),
            patch("job_agent.core.engine.ChatOpenAI") as client,
        ):
            LangGraphAgentEngine(use_model="gpt")
            options = client.call_args.kwargs
            self.assertEqual(options["model"], "gpt-6-luna")
            self.assertTrue(options["use_responses_api"])
            self.assertEqual(options["reasoning"], {"effort": "medium"})
            self.assertEqual(options["output_version"], "responses/v1")
            self.assertIs(options["store"], False)
            self.assertIn("reasoning.encrypted_content", options["include"])
            self.assertNotIn("temperature", options)
            client.return_value.bind_tools.assert_called_once_with([])

    def test_model_override_and_gemini_remain_separate(self):
        with (
            patch.dict(
                os.environ,
                {"OPENAI_MODEL": "gpt-6.1-sol", "GEMINI_MODEL": "gemini-fixture"},
            ),
            patch("job_agent.core.engine.ChatOpenAI") as openai,
            patch("job_agent.core.engine.ChatGoogleGenerativeAI") as gemini,
        ):
            LangGraphAgentEngine(use_model="gpt")
            self.assertEqual(openai.call_args.kwargs["model"], "gpt-6.1-sol")
            LangGraphAgentEngine(use_model="gemini")
            self.assertEqual(gemini.call_args.kwargs["model"], "gemini-fixture")
            self.assertEqual(openai.call_count, 1)

    def test_request_scoped_model_and_retry_policy_do_not_change_environment(self):
        with (
            patch.dict(os.environ, {"OPENAI_MODEL": "configured-default"}),
            patch("job_agent.core.engine.ChatOpenAI") as client,
        ):
            LangGraphAgentEngine(
                use_model="gpt", model_name="ui-selected", max_retries=0
            )
            self.assertEqual(client.call_args.kwargs["model"], "ui-selected")
            self.assertEqual(client.call_args.kwargs["max_retries"], 0)
            self.assertEqual(os.environ["OPENAI_MODEL"], "configured-default")


class ResponsesRoundTripTests(unittest.IsolatedAsyncioTestCase):
    async def test_real_sdk_serialization_tool_round_trip_and_text_contract(self):
        requests = []
        executed = Mock()

        @tool
        async def echo_fact(value: str) -> str:
            """Echo a local fixture fact without accessing external services."""
            executed(value)
            return value

        def reply(request):
            self.assertEqual(request.url.path, "/v1/responses")
            payload = json.loads(request.content)
            requests.append(payload)
            output = (
                [
                    {
                        "type": "reasoning",
                        "id": "rs_fixture",
                        "summary": [],
                        "encrypted_content": "encrypted-fixture",
                    },
                    {
                        "type": "function_call",
                        "id": "fc_fixture",
                        "call_id": "call_fixture",
                        "name": "echo_fact",
                        "arguments": '{"value":"source fact"}',
                        "status": "completed",
                    },
                ]
                if len(requests) == 1
                else [
                    {
                        "type": "message",
                        "id": "msg_fixture",
                        "role": "assistant",
                        "status": "completed",
                        "content": [
                            {
                                "type": "output_text",
                                "text": "Reviewed source fact",
                                "annotations": [],
                            }
                        ],
                    }
                ]
            )
            return httpx.Response(
                200,
                json={
                    "id": f"resp_fixture_{len(requests)}",
                    "object": "response",
                    "created_at": 1,
                    "status": "completed",
                    "error": None,
                    "incomplete_details": None,
                    "model": "gpt-6-luna",
                    "output": output,
                    "parallel_tool_calls": True,
                    "tool_choice": "auto",
                    "tools": [],
                    "usage": None,
                    "text": {"format": {"type": "text"}},
                },
            )

        transport = httpx.MockTransport(reply)
        with httpx.Client(transport=transport) as sync_client:
            async with httpx.AsyncClient(transport=transport) as async_client:

                def create_model(**options):
                    options["max_retries"] = 0
                    return ChatOpenAI(
                        api_key="test-only-not-a-secret",
                        base_url="https://fixture.invalid/v1",
                        http_client=sync_client,
                        http_async_client=async_client,
                        **options,
                    )

                with (
                    patch.dict(os.environ, {"OPENAI_MODEL": "gpt-6-luna"}),
                    patch("job_agent.core.engine.ChatOpenAI", side_effect=create_model),
                ):
                    agent = LangGraphAgentEngine(
                        use_model="gpt",
                        tools=[echo_fact],
                        system_prompt="Use only fixture facts.",
                    )
                    events = [event async for event in agent.run("Review the fixture.")]

        executed.assert_called_once_with("source fact")
        self.assertEqual(len(requests), 2)
        for request in requests:
            self.assertEqual(request["model"], "gpt-6-luna")
            self.assertEqual(request["reasoning"], {"effort": "medium"})
            self.assertIs(request["store"], False)
            self.assertNotIn("temperature", request)
            self.assertNotIn("previous_response_id", request)
            self.assertEqual(request["tools"][0]["name"], "echo_fact")
        replay = requests[1]["input"]
        reasoning = next(item for item in replay if item.get("type") == "reasoning")
        self.assertEqual(reasoning["encrypted_content"], "encrypted-fixture")
        output = next(
            item for item in replay if item.get("type") == "function_call_output"
        )
        self.assertEqual(output["call_id"], "call_fixture")
        self.assertEqual(output["output"], "source fact")
        final = events[-1]["llm_think"]["messages"][0]
        self.assertEqual(final.text, "Reviewed source fact")
        self.assertEqual(final.tool_calls, [])


if __name__ == "__main__":
    unittest.main()
