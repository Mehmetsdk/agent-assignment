import json
import os

from dotenv import load_dotenv
from groq import Groq

from src.tools import AVAILABLE_TOOLS, TOOL_DEFINITIONS

load_dotenv()


class TaskAgent:
    def __init__(self, api_key: str | None = None):
        api_key = api_key or os.getenv("GROQ_API_KEY")
        if not api_key:
            raise ValueError("Missing GROQ_API_KEY in environment")
        self.client = Groq(api_key=api_key)
        self.model = "llama-3.3-70b-versatile"
        self.base_system_instruction = (
            "You are a helpful, reliable, and agentic executive assistant. "
            "Your primary goal is to execute user requests by breaking them down into logical steps. "
            "CRITICAL RULES — follow these without exception: "
            "1. Always answer in the same language as the user's most recent message. "
            "2. CLARIFY BEFORE ACTING: Before calling ANY tool you must have all required details. "
            "   - For booking_service: you need the exact date, time, and specific option to book. "
            "   - For search_service: you need the city/location and any budget or preference. "
            "   - For calendar_check: you need a specific date or date range. "
            "   - For reminder_create: you need the event details and the date/time. "
            "   If ANY of these details are missing, ask the user ONE concise clarifying question "
            "   listing exactly what is missing. Never guess or invent details. "
            "3. Use the provided tools to check calendars, search for options, book items, and set reminders. "
            "4. If a tool fails or finds no results, apologize and ask the user how they would like to proceed. "
            "5. Answer directly and concisely — do not self-summarize at the end of your reply."
        )
        self.conversation_history: list = [
            {"role": "system", "content": self.base_system_instruction},
        ]

    def _detect_language(self, user_input: str) -> str:
        text = user_input.lower()
        turkish_markers = [
            "ı", "ş", "ğ", "ç", "ö", "ü",
            "merhaba", "nasılsın", "randevu", "saat",
            "yardım", "bana", "lütfen", "çünkü",
        ]
        if any(marker in text for marker in turkish_markers):
            return "Turkish"
        return "English"

    def _language_instruction(self, language: str) -> str:
        if language == "Turkish":
            return "Respond in Turkish."
        return "Respond in English."

    def _generate_with_tools(self, language: str) -> tuple[str, bool]:
        """Run the LLM tool-use loop. Returns (response_text, tools_were_called)."""
        language_instruction = {"role": "system", "content": self._language_instruction(language)}
        tools_called = False

        while True:
            messages = self.conversation_history + [language_instruction]
            try:
                response = self.client.chat.completions.create(
                    model=self.model, messages=messages, tools=TOOL_DEFINITIONS, tool_choice="auto"
                )
            except Exception:
                # Groq sometimes generates a malformed tool-call (400 tool_use_failed).
                # Fall back to a plain text reply without tool bindings.
                fallback = self.client.chat.completions.create(
                    model=self.model, messages=messages
                )
                return fallback.choices[0].message.content or "", tools_called
            message = response.choices[0].message
            if hasattr(message, "tool_calls") and message.tool_calls:
                tools_called = True
                self.conversation_history.append(message)
                for tool_call in message.tool_calls:
                    function_name = tool_call.function.name
                    try:
                        function_args = json.loads(tool_call.function.arguments)
                    except json.JSONDecodeError:
                        function_args = {}
                    if function_name in AVAILABLE_TOOLS:
                        tool_result = AVAILABLE_TOOLS[function_name](**function_args)
                    else:
                        tool_result = json.dumps({"error": f"Unknown tool: {function_name}"})
                    self.conversation_history.append(
                        {
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "name": function_name,
                            "content": tool_result,
                        }
                    )
            else:
                return message.content or "", tools_called

    def _generate_summary(self, language: str) -> str:
        summary_request = {
            "role": "user",
            "content": (
                f"Provide a clear final summary strictly in {language}. "
                "CRITICAL RULE: Never mix languages. "
                "Include: 1) What was done, 2) What was booked/found, 3) Remaining blockers. "
                "Keep it concise and structured."
            ),
        }
        response = self.client.chat.completions.create(
            model=self.model,
            messages=self.conversation_history + [summary_request],
        )
        return response.choices[0].message.content or ""

    def process_input(self, user_input: str) -> str:
        language = self._detect_language(user_input)
        self.conversation_history.append({"role": "user", "content": user_input})

        base_response, tools_called = self._generate_with_tools(language)
        self.conversation_history.append({"role": "assistant", "content": base_response})

        if not tools_called:
            return base_response

        summary_content = self._generate_summary(language)
        return f"{base_response}\n\n{'='*60}\n📋 FINAL SUMMARY:\n{'='*60}\n{summary_content}"
