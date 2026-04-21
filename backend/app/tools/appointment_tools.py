from typing import Dict, Any, List, Optional
from datetime import datetime, date, time, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_
from app.models.schemas import (
    Appointment, Doctor, DoctorAvailability, User
)

async def check_availability(db: AsyncSession, doctor_id: int, check_date: date) -> Dict[str, Any]:
    stmt = select(Doctor).filter(Doctor.id == doctor_id)
    result = await db.execute(stmt)
    doctor = result.scalar_one_or_none()
    
    if not doctor:
        return {
            "success": False,
            "error": "Doctor not found",
            "available_slots": []
        }
    
    day_of_week = check_date.weekday()
    
    stmt = select(DoctorAvailability).filter(
        and_(
            DoctorAvailability.doctor_id == doctor_id,
            DoctorAvailability.day_of_week == day_of_week,
            DoctorAvailability.is_active == True
        )
    )
    result = await db.execute(stmt)
    availabilities = result.scalars().all()
    
    if not availabilities:
        return {
            "success": True,
            "doctor_name": doctor.name,
            "date": check_date.isoformat(),
            "available_slots": [],
            "message": "No availability found for this date"
        }
    
    start_datetime = datetime.combine(check_date, time.min)
    end_datetime = datetime.combine(check_date, time.max)
    
    stmt = select(Appointment).filter(
        and_(
            Appointment.doctor_id == doctor_id,
            Appointment.appointment_time >= start_datetime,
            Appointment.appointment_time < end_datetime,
            Appointment.status == "confirmed"
        )
    )
    result = await db.execute(stmt)
    booked_appointments = result.scalars().all()
    
    booked_times = set()
    for appt in booked_appointments:
        booked_times.add(appt.appointment_time.replace(tzinfo=None))
    
    available_slots = []
    for availability in availabilities:
        current_time = datetime.combine(check_date, availability.start_time)
        end_time = datetime.combine(check_date, availability.end_time)
        
        while current_time < end_time:
            if current_time >= datetime.now().replace(tzinfo=None, minute=0, second=0, microsecond=0):
                if current_time not in booked_times:
                    available_slots.append(current_time.isoformat())
            
            current_time += timedelta(minutes=30)
    
    return {
        "success": True,
        "doctor_name": doctor.name,
        "date": check_date.isoformat(),
        "available_slots": available_slots,
        "message": f"Found {len(available_slots)} available slots"
    }

async def book_appointment(
    db: AsyncSession, 
    user_id: int, 
    doctor_id: int, 
    appointment_time: datetime,
    notes: Optional[str] = None
) -> Dict[str, Any]:
    stmt = select(User).filter(User.id == user_id)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    
    if not user:
        return {
            "success": False,
            "error": "User not found"
        }
    
    stmt = select(Doctor).filter(Doctor.id == doctor_id)
    result = await db.execute(stmt)
    doctor = result.scalar_one_or_none()
    
    if not doctor:
        return {
            "success": False,
            "error": "Doctor not found"
        }
    
    # Ensure appointment_time is naive for comparison with datetime.now()
    if appointment_time.tzinfo is not None:
        appointment_time = appointment_time.replace(tzinfo=None)
    
    now = datetime.now()
    if appointment_time < now:
        return {
            "success": False,
            "error": "Cannot book appointments in the past"
        }
    
    stmt = select(Appointment).filter(
        and_(
            Appointment.doctor_id == doctor_id,
            Appointment.appointment_time == appointment_time,
            Appointment.status == "confirmed"
        )
    )
    result = await db.execute(stmt)
    existing = result.scalar_one_or_none()
    
    if existing:
        check_date = appointment_time.date()
        availability = await check_availability(db, doctor_id, check_date)
        return {
            "success": False,
            "error": "Time slot already booked",
            "alternative_slots": availability.get("available_slots", [])
        }
    
    new_appointment = Appointment(
        user_id=user_id,
        doctor_id=doctor_id,
        appointment_time=appointment_time,
        notes=notes,
        status="confirmed"
    )
    
    db.add(new_appointment)
    await db.commit()
    await db.refresh(new_appointment)
    
    return {
        "success": True,
        "appointment_id": new_appointment.id,
        "message": "Appointment booked successfully",
        "appointment": {
            "id": new_appointment.id,
            "doctor_name": doctor.name,
            "user_name": user.name,
            "appointment_time": new_appointment.appointment_time.isoformat(),
            "status": new_appointment.status
        }
    }

async def cancel_appointment(db: AsyncSession, appointment_id: int) -> Dict[str, Any]:
    stmt = select(Appointment).filter(Appointment.id == appointment_id)
    result = await db.execute(stmt)
    appointment = result.scalar_one_or_none()
    
    if not appointment:
        return {
            "success": False,
            "error": "Appointment not found"
        }
    
    appointment.status = "cancelled"
    await db.commit()
    
    return {
        "success": True,
        "message": "Appointment cancelled successfully",
        "appointment_id": appointment_id
    }

async def reschedule_appointment(
    db: AsyncSession, 
    appointment_id: int, 
    new_time: datetime
) -> Dict[str, Any]:
    stmt = select(Appointment).filter(Appointment.id == appointment_id)
    result = await db.execute(stmt)
    appointment = result.scalar_one_or_none()
    
    if not appointment:
        return {
            "success": False,
            "error": "Appointment not found"
        }
    
    if appointment.status != "confirmed":
        return {
            "success": False,
            "error": "Cannot reschedule a non-confirmed appointment"
        }
    
    if new_time < datetime.now().astimezone():
        return {
            "success": False,
            "error": "Cannot reschedule to a past time"
        }
    
    stmt = select(Appointment).filter(
        and_(
            Appointment.doctor_id == appointment.doctor_id,
            Appointment.appointment_time == new_time,
            Appointment.status == "confirmed",
            Appointment.id != appointment_id
        )
    )
    result = await db.execute(stmt)
    existing = result.scalar_one_or_none()
    
    if existing:
        check_date = new_time.date()
        availability = await check_availability(db, appointment.doctor_id, check_date)
        return {
            "success": False,
            "error": "New time slot already booked",
            "alternative_slots": availability.get("available_slots", [])
        }
    
    old_time = appointment.appointment_time
    appointment.appointment_time = new_time
    await db.commit()
    
    return {
        "success": True,
        "message": "Appointment rescheduled successfully",
        "appointment_id": appointment_id,
        "old_time": old_time.isoformat(),
        "new_time": new_time.isoformat()
    }
