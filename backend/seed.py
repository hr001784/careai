import asyncio
import sys
import os

# Add the current directory to sys.path so 'app' can be found
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from datetime import time
from app.models.database import AsyncSessionLocal, engine, Base
from app.models.schemas import User, Doctor, DoctorAvailability

async def seed_database():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    
    async with AsyncSessionLocal() as db:
        try:
            # Create a default user
            user = User(
                name="Test User",
                email="test@example.com",
                phone="1234567890"
            )
            db.add(user)
            
            # Create doctors
            doctors = [
                Doctor(name="Dr. Smith", specialization="General Physician", email="smith@clinic.com"),
                Doctor(name="Dr. Priya", specialization="Pediatrician", email="priya@clinic.com"),
                Doctor(name="Dr. Rajesh", specialization="Cardiologist", email="rajesh@clinic.com")
            ]
            db.add_all(doctors)
            await db.commit()
            
            # Add availability for doctors
            for doctor in doctors:
                for day in range(0, 5):  # Monday to Friday
                    availability = DoctorAvailability(
                        doctor_id=doctor.id,
                        day_of_week=day,
                        start_time=time(9, 0),
                        end_time=time(17, 0)
                    )
                    db.add(availability)
            
            await db.commit()
            print("Database seeded successfully!")
            
        except Exception as e:
            print(f"Error seeding database: {e}")
            await db.rollback()

if __name__ == "__main__":
    asyncio.run(seed_database())
