from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
import time
from contextlib import asynccontextmanager
from dotenv import load_dotenv
import os

from app.models.database import engine, Base
from app.models.schemas import User, Doctor, Appointment, DoctorAvailability
from app.websocket.voice_handler import voice_router
from app.memory.redis_memory import get_memory

load_dotenv()

@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        print("Database initialized.")
    except Exception as e:
        print(f"Database initialization warning: {e}")
        
    try:
        memory = await get_memory()
        # get_memory() already tries to connect and falls back to LocalMemory
        print("Memory service ready.")
    except Exception as e:
        print(f"Memory initialization warning: {e}")
        
    yield
    
    try:
        memory = await get_memory()
        await memory.disconnect()
    except Exception as e:
        print(f"Cleanup warning: {e}")

app = FastAPI(
    title="Care.AI - Clinical Appointment Booking Voice Agent",
    description="Real-time multilingual voice AI for clinical appointment booking",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files directory
static_path = os.path.join(os.path.dirname(__file__), "../static")
if not os.path.exists(static_path):
    os.makedirs(static_path)
app.mount("/static", StaticFiles(directory=static_path), name="static")

@app.middleware("http")
async def latency_middleware(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = (time.time() - start_time) * 1000
    response.headers["X-Process-Time-MS"] = str(round(process_time, 2))
    return response

app.include_router(voice_router, prefix="/api/v1")

@app.get("/test")
async def get_test_page():
    # Use relative path that works both locally and on Render
    current_dir = os.path.dirname(os.path.abspath(__file__))
    # The file was copied to static/index.html during our build/deployment process
    html_path = os.path.join(current_dir, "../static/index.html")
    
    if os.path.exists(html_path):
        return FileResponse(html_path)
    
    # Fallback to looking for test_client.html in the project root
    root_html_path = os.path.join(current_dir, "../../test_client.html")
    if os.path.exists(root_html_path):
        return FileResponse(root_html_path)
        
    return {"error": "Test client page not found. Please ensure static/index.html or test_client.html exists."}

@app.get("/")
async def root():
    return {
        "service": "Care.AI Voice Agent",
        "status": "healthy",
        "version": "1.0.0"
    }

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "version": "1.0.0",
        "timestamp": time.time()
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", 8000)),
        reload=True
    )
