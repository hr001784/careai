import uuid
import json
import time
from datetime import datetime
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.database import get_db
from app.memory.redis_memory import get_memory
from app.services.stt_service import get_stt_service
from app.services.tts_service import get_tts_service
from app.services.language_service import get_language_detector
from app.agents.llm_agent import get_llm_agent
from app.tools.appointment_tools import (
    check_availability, book_appointment, cancel_appointment, reschedule_appointment
)

voice_router = APIRouter()

@voice_router.websocket("/ws/voice")
async def voice_endpoint(
    websocket: WebSocket, 
    lang: str = "en",
    db: AsyncSession = Depends(get_db)
):
    await websocket.accept()
    
    session_id = str(uuid.uuid4())
    memory = await get_memory()
    stt_service = get_stt_service()
    tts_service = get_tts_service()
    language_detector = get_language_detector()
    llm_agent = get_llm_agent()
    
    # Store preferred language in session
    try:
        await memory.connect()
        try:
            await stt_service.load_model()
        except Exception as stt_err:
            print(f"Non-fatal STT load error: {stt_err}")
    except Exception as e:
        print(f"Memory connection error: {e}")
        await websocket.send_json({
            "type": "error",
            "message": f"Initialization error: {str(e)}"
        })
        await websocket.close()
        return

    await memory.set_session(session_id, {
        "messages": [],
        "context": {"user_id": 1, "doctor_id": 1, "language": lang}
    })
    
    try:
        while True:
            data = await websocket.receive_bytes()
            start_time = time.time()
            
            await websocket.send_json({
                "type": "status",
                "status": "processing",
                "session_id": session_id
            })
            
            text, detected_lang = await stt_service.transcribe(data)
            stt_time = time.time() - start_time
            
            if not text or len(text.strip()) < 2:
                continue
            
            # Use detected language but respect session preference if it's not English
            # or if detected language seems wrong
            session_data = await memory.get_session(session_id)
            context = session_data.get("context", {})
            pref_lang = context.get("language", "en")
            
            # Simple logic: if user explicitly chose a language, use it for processing
            lang = pref_lang if pref_lang in ["hi", "ta"] else language_detector.detect(text)
            
            await memory.add_message(session_id, "user", text)
            
            messages = await memory.get_messages(session_id)
            
            llm_start = time.time()
            llm_response = await llm_agent.process(text, lang, context, messages[:-1])
            llm_time = time.time() - llm_start
            
            tool_result = None
            response_text = ""
            
            if llm_response["action"] == "tool_call":
                tool_name = llm_response["tool_name"]
                params = llm_response["parameters"]
                
                try:
                    print(f"Executing tool: {tool_name} with params: {params}")
                    if tool_name == "checkAvailability":
                        doctor_id = params.get("doctor_id", 1)
                        date_str = params.get("date")
                        if date_str:
                            check_date = datetime.strptime(date_str, "%Y-%m-%d").date()
                            tool_result = await check_availability(db, doctor_id, check_date)
                    
                    elif tool_name == "bookAppointment":
                        user_id = params.get("user_id", 1)
                        doctor_id = params.get("doctor_id", 1)
                        time_str = params.get("time")
                        notes = params.get("notes")
                        if time_str:
                            try:
                                appt_time = datetime.fromisoformat(time_str)
                                tool_result = await book_appointment(db, user_id, doctor_id, appt_time, notes)
                            except ValueError as ve:
                                print(f"Invalid date format: {time_str}")
                                response_text = "Invalid date format provided."
                        else:
                            print("Missing time parameter for booking")
                    
                    elif tool_name == "cancelAppointment":
                        appt_id = params.get("appointment_id")
                        if appt_id:
                            tool_result = await cancel_appointment(db, appt_id)
                    
                    elif tool_name == "rescheduleAppointment":
                        appt_id = params.get("appointment_id")
                        new_time_str = params.get("new_time")
                        if appt_id and new_time_str:
                            try:
                                new_time = datetime.fromisoformat(new_time_str)
                                tool_result = await reschedule_appointment(db, appt_id, new_time)
                            except ValueError:
                                response_text = "Invalid date format provided."
                    
                    if tool_result:
                        response_text = await _format_tool_response(tool_result, lang)
                    elif not response_text:
                        response_text = _get_error_message(lang)
                
                except Exception as e:
                    print(f"Tool execution error: {e}")
                    import traceback
                    traceback.print_exc()
                    response_text = _get_error_message(lang)
            
            elif llm_response["action"] == "clarify":
                response_text = llm_response["message"]
            
            else:
                response_text = llm_response["message"]
            
            await memory.add_message(session_id, "assistant", response_text)
            
            tts_start = time.time()
            audio_response = await tts_service.synthesize(response_text, lang)
            tts_time = time.time() - tts_start
            
            total_time = time.time() - start_time
            
            await websocket.send_json({
                "type": "latency",
                "stt_ms": round(stt_time * 1000, 2),
                "llm_ms": round(llm_time * 1000, 2),
                "tts_ms": round(tts_time * 1000, 2),
                "total_ms": round(total_time * 1000, 2)
            })
            
            await websocket.send_json({
                "type": "text",
                "transcript": text,
                "response": response_text,
                "language": lang,
                "session_id": session_id
            })
            
            await websocket.send_bytes(audio_response)
    
    except WebSocketDisconnect:
        await memory.clear_session(session_id)
        await memory.disconnect()
    except Exception as e:
        await websocket.send_json({
            "type": "error",
            "message": str(e)
        })

async def _format_tool_response(result, lang: str) -> str:
    if not result:
        return _get_error_message(lang)
    
    if lang == "hi":
        if result.get("success"):
            if "available_slots" in result:
                slots = result["available_slots"][:5]
                return f"उपलब्ध स्लॉट: {', '.join(slots)}"
            elif "appointment" in result:
                return "अपॉइंटमेंट सफलतापूर्वक बुक हो गया!"
            elif "appointment_id" in result:
                return "अपॉइंटमेंट सफलतापूर्वक रद्द/पुनर्निर्धारित हो गया!"
        else:
            return result.get("error", "कोई त्रुटि हुई")
    
    elif lang == "ta":
        if result.get("success"):
            if "available_slots" in result:
                slots = result["available_slots"][:5]
                return f"கிடைக்கக்கூடிய ஸ்லாட்டுகள்: {', '.join(slots)}"
            elif "appointment" in result:
                return "அபாய்ட்மெண்ட் வெற்றிகரமாக பதிவு செய்யப்பட்டது!"
            elif "appointment_id" in result:
                return "அபாய்ட்மெண்ட் வெற்றிகரமாக ரத்து/மறுஏர்டமை செய்யப்பட்டது!"
        else:
            return result.get("error", "ஏதோ பிழை ஏற்பட்டது")
    
    else:
        if result.get("success"):
            if "available_slots" in result:
                slots = result["available_slots"][:5]
                return f"Available slots: {', '.join(slots)}"
            elif "appointment" in result:
                return "Appointment booked successfully!"
            elif "appointment_id" in result:
                return "Appointment cancelled/rescheduled successfully!"
        else:
            return result.get("error", "An error occurred")

def _get_error_message(lang: str) -> str:
    errors = {
        "en": "I'm sorry, there was an error processing your request.",
        "hi": "मुझे खेद है, आपके अनुरोध को संसाधित करने में त्रुटि हुई।",
        "ta": "மன்னிக்கவும், உங்கள் கோரிக்கையை செயல்படுத்துவதில் பிழை ஏற்பட்டது."
    }
    return errors.get(lang, errors["en"])
