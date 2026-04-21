import json
import re
from typing import Dict, Any, Optional, List, Tuple
from openai import AsyncOpenAI
from dotenv import load_dotenv
import os
from datetime import datetime, date, timedelta

load_dotenv()

class LocalAgent:
    """A rule-based agent that works without an API key for testing purposes."""
    async def process(self, text: str, language: str, context: Dict[str, Any], history: List[Dict[str, str]]) -> Dict[str, Any]:
        text = text.lower()
        
        # Simple pattern matching for intents
        if any(word in text for word in ["book", "appointment", "schedule", "बुक", "முன்பதிவு"]):
            # Default to tomorrow if mentioned
            booking_date = (date.today() + timedelta(days=1)).isoformat()
            
            # Look for doctor names
            doctor_id = 1
            if "smith" in text: doctor_id = 1
            elif "priya" in text: doctor_id = 2
            elif "rajesh" in text: doctor_id = 3
            
            return {
                "action": "tool_call",
                "tool_name": "bookAppointment",
                "parameters": {
                    "doctor_id": doctor_id,
                    "user_id": context.get("user_id", 1),
                    "time": f"{booking_date}T10:00:00",
                    "notes": "Booked via local mode (No API Key)"
                },
                "language": language
            }
        
        elif any(word in text for word in ["available", "slots", "check", "उपलब्ध", "கிடைக்கும்"]):
            return {
                "action": "tool_call",
                "tool_name": "checkAvailability",
                "parameters": {
                    "doctor_id": 1,
                    "date": (date.today() + timedelta(days=1)).isoformat()
                },
                "language": language
            }
            
        messages = {
            "en": f"I understood you said: '{text}'. (Local Mode Active)",
            "hi": f"मैं समझ गया कि आपने कहा: '{text}'। (लोकल मोड सक्रिय)",
            "ta": f"நீங்கள் சொன்னது எனக்குப் புரிந்தது: '{text}'. (உள்ளூர் பயன்முறை செயலில் உள்ளது)"
        }
        return {
            "action": "respond",
            "message": messages.get(language, messages["en"]),
            "language": language
        }

SYSTEM_PROMPT = """You are a clinical appointment booking assistant. You can help users book, cancel, reschedule appointments, and check doctor availability.

Supported languages: English, Hindi, Tamil. Respond in the user's language.

Available tools:
1. checkAvailability(doctor_id, date): Check available slots for a doctor on a date
2. bookAppointment(user_id, doctor_id, time): Book an appointment
3. cancelAppointment(appointment_id): Cancel an appointment
4. rescheduleAppointment(appointment_id, new_time): Reschedule to new_time

You MUST respond in JSON format only with one of these structures:

1. If tool call needed:
{
  "action": "tool_call",
  "tool_name": "checkAvailability|bookAppointment|cancelAppointment|rescheduleAppointment",
  "parameters": {...},
  "language": "en|hi|ta"
}

2. If user needs clarification:
{
  "action": "clarify",
  "message": "Ask for missing info",
  "language": "en|hi|ta"
}

3. If response to user:
{
  "action": "respond",
  "message": "Response to user",
  "language": "en|hi|ta"
}

Always extract:
- doctor_id: integer (default to 1 if not specified)
- user_id: integer (default to 1 if not specified)
- appointment_id: integer (from context or user input)
- date: YYYY-MM-DD format
- time: YYYY-MM-DDTHH:MM:SS format

Default doctor_id=1, user_id=1 if not specified."""

class LLMAgent:
    def __init__(self):
        self.client = AsyncOpenAI(
            api_key=os.getenv("OPENAI_API_KEY", "dummy-key")
        )
        self.model = os.getenv("OPENAI_MODEL", "gpt-3.5-turbo")
    
    async def process(
        self,
        user_input: str,
        language: str = "en",
        context: Optional[Dict[str, Any]] = None,
        messages: Optional[List[Dict[str, str]]] = None
    ) -> Dict[str, Any]:
        context = context or {}
        messages = messages or []
        
        formatted_messages = [
            {"role": "system", "content": SYSTEM_PROMPT}
        ]
        
        for msg in messages:
            formatted_messages.append(msg)
        
        context_str = json.dumps(context, ensure_ascii=False)
        user_msg = f"User input: {user_input}\nLanguage: {language}\nContext: {context_str}"
        formatted_messages.append({"role": "user", "content": user_msg})
        
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=formatted_messages,
                temperature=0.3,
                max_tokens=500
            )
            
            result_text = response.choices[0].message.content.strip()
            
            try:
                result = json.loads(result_text)
                return result
            except json.JSONDecodeError:
                return {
                    "action": "respond",
                    "message": self._get_fallback_message(language),
                    "language": language
                }
        except Exception as e:
            return {
                "action": "respond",
                "message": self._get_fallback_message(language),
                "language": language
            }
    
    def _get_fallback_message(self, language: str) -> str:
        messages = {
            "en": "I'm sorry, I couldn't process that. Could you please repeat?",
            "hi": "मुझे खेद है, मैं इसे संसाधित नहीं कर सका। कृपया दोहराएं?",
            "ta": "மன்னிக்கவும், அதைச் செயல்படுத்த முடியவில்லை. மீண்டும் சொல்லலாமா?"
        }
        return messages.get(language, messages["en"])

_llm_agent: Optional[Any] = None

def get_llm_agent() -> Any:
    global _llm_agent
    if _llm_agent is None:
        api_key = os.getenv("OPENAI_API_KEY", "dummy-key")
        if not api_key or api_key == "dummy-key":
            print("--- WARNING: No OpenAI API Key found. Using Local Mock Agent ---")
            _llm_agent = LocalAgent()
        else:
            _llm_agent = LLMAgent()
    return _llm_agent
