import asyncio
import json
import os
import sys
from app.agents.llm_agent import get_llm_agent
from app.models.database import AsyncSessionLocal
from app.tools.appointment_tools import check_availability, book_appointment
from datetime import date, datetime

# Fix for Windows console encoding
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

async def test_agent():
    print("--- Care.AI Agent Text Test ---")
    agent = get_llm_agent()
    
    # Test cases
    queries = [
        "I want to book an appointment with Dr. Smith for tomorrow at 10 AM",
        "Dr. Priya के साथ कल के लिए अपॉइंटमेंट बुक करें", # Hindi
        "நாளை காலை 11 மணிக்கு டாக்டர் ராஜேஷுடன் ஒரு சந்திப்பை முன்பதிவு செய்யுங்கள்" # Tamil
    ]
    
    context = {"user_id": 1, "doctor_id": 1}
    
    for query in queries:
        print(f"\nUser: {query}")
        # In a real scenario, we'd detect language first
        lang = "en"
        if "कल" in query: lang = "hi"
        if "நாளை" in query: lang = "ta"
        
        response = await agent.process(query, lang, context, [])
        print(f"Agent Action: {response['action']}")
        
        if response['action'] == 'tool_call':
            print(f"Tool: {response['tool_name']}")
            print(f"Params: {response['parameters']}")
        else:
            print(f"Message: {response.get('message', 'N/A')}")

if __name__ == "__main__":
    asyncio.run(test_agent())
