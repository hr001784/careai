from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from dotenv import load_dotenv
import os

load_dotenv()

# Use SQLite by default for easier local setup and deployment
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./careai.db")

engine = create_async_engine(DATABASE_URL, echo=True)
AsyncSessionLocal = sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)

Base = declarative_base()

async def get_db():
    try:
        async with AsyncSessionLocal() as session:
            yield session
    except Exception as e:
        print(f"Database connection error: {e}")
        # In case of database error, we might still want the voice handler to work for basic chat
        # but for now, we'll let it fail or handle it in the caller
        raise e
