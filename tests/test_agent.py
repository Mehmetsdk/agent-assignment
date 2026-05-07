import json
import unittest
from unittest.mock import MagicMock

from src.agent.orchestrator import TaskAgent


def _text_response(content: str):
    msg = MagicMock()
    msg.content = content
    msg.tool_calls = None
    choice = MagicMock()
    choice.message = msg
    resp = MagicMock()
    resp.choices = [choice]
    return resp


def _tool_call_response(tool_calls: list):
    msg = MagicMock()
    msg.content = None
    msg.tool_calls = tool_calls
    choice = MagicMock()
    choice.message = msg
    resp = MagicMock()
    resp.choices = [choice]
    return resp


def _make_tool_call(name: str, args: dict, call_id: str = "tc_001"):
    tc = MagicMock()
    tc.id = call_id
    tc.function.name = name
    tc.function.arguments = json.dumps(args)
    return tc


def _build_agent(responses: list) -> TaskAgent:
    agent = TaskAgent.__new__(TaskAgent)
    agent.model = "llama-3.3-70b-versatile"
    agent.base_system_instruction = "stub"
    agent.conversation_history = [{"role": "system", "content": "stub"}]
    client = MagicMock()
    client.chat.completions.create.side_effect = responses
    agent.client = client
    return agent


class AgentTest(unittest.TestCase):
    def test_no_summary_when_no_tools_called(self):
        """Conversational reply (no tool use) must not include a summary block."""
        agent = _build_agent([_text_response("Hello! How can I help?")])
        response = agent.process_input("hi")
        self.assertIn("Hello! How can I help?", response)
        self.assertNotIn("FINAL SUMMARY", response)

    def test_summary_appended_after_tool_use(self):
        """A task that triggers tool use must include FINAL SUMMARY in the output."""
        tool_call = _make_tool_call("calendar_check", {"date_range": "next Tuesday"})
        agent = _build_agent([
            _tool_call_response([tool_call]),
            _text_response("Your calendar is free next Tuesday."),
            _text_response("Summary: calendar checked, no conflicts found."),
        ])
        response = agent.process_input("Check my calendar for next Tuesday")
        self.assertIn("Your calendar is free next Tuesday.", response)
        self.assertIn("FINAL SUMMARY", response)

    def test_turkish_input_uses_turkish_language(self):
        """Turkish input must inject a Turkish language instruction into the LLM call."""
        agent = _build_agent([_text_response("Merhaba!")])
        agent.process_input("Merhaba")
        first_call_messages = str(agent.client.chat.completions.create.call_args_list[0])
        self.assertIn("Respond in Turkish.", first_call_messages)

    def test_english_input_uses_english_language(self):
        """English input must inject an English language instruction into the LLM call."""
        agent = _build_agent([_text_response("Hello!")])
        agent.process_input("hello")
        first_call_messages = str(agent.client.chat.completions.create.call_args_list[0])
        self.assertIn("Respond in English.", first_call_messages)

    def test_conversation_history_grows_correctly(self):
        """Each process_input call appends user + assistant messages to history."""
        agent = _build_agent([
            _text_response("Response 1"),
            _text_response("Response 2"),
        ])
        agent.process_input("first message")
        agent.process_input("second message")
        roles = [m["role"] for m in agent.conversation_history if isinstance(m, dict)]
        self.assertEqual(roles.count("user"), 2)
        self.assertEqual(roles.count("assistant"), 2)


if __name__ == "__main__":
    unittest.main()
