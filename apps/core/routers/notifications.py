"""
Notification Preferences API Router
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List

from database import get_db
from models import NotificationPreference, AlertLog
from schemas import (
    NotificationPreferenceCreate,
    NotificationPreferenceUpdate,
    NotificationPreferenceResponse,
    TestNotificationRequest,
)
from notifications import notification_service

router = APIRouter()


@router.get("/preferences", response_model=List[NotificationPreferenceResponse])
async def list_preferences(db: AsyncSession = Depends(get_db)):
    """List all notification preferences"""
    result = await db.execute(
        select(NotificationPreference).order_by(NotificationPreference.id)
    )
    return result.scalars().all()


@router.post("/preferences", response_model=NotificationPreferenceResponse)
async def create_preference(
    preference: NotificationPreferenceCreate,
    db: AsyncSession = Depends(get_db)
):
    """Create a new notification preference"""
    db_pref = NotificationPreference(**preference.model_dump())
    db.add(db_pref)
    await db.commit()
    await db.refresh(db_pref)
    return db_pref


@router.get("/preferences/{pref_id}", response_model=NotificationPreferenceResponse)
async def get_preference(pref_id: int, db: AsyncSession = Depends(get_db)):
    """Get a specific notification preference"""
    result = await db.execute(
        select(NotificationPreference).where(NotificationPreference.id == pref_id)
    )
    pref = result.scalar_one_or_none()
    if not pref:
        raise HTTPException(status_code=404, detail="Preference not found")
    return pref


@router.patch("/preferences/{pref_id}", response_model=NotificationPreferenceResponse)
async def update_preference(
    pref_id: int,
    preference: NotificationPreferenceUpdate,
    db: AsyncSession = Depends(get_db)
):
    """Update a notification preference"""
    result = await db.execute(
        select(NotificationPreference).where(NotificationPreference.id == pref_id)
    )
    pref = result.scalar_one_or_none()
    if not pref:
        raise HTTPException(status_code=404, detail="Preference not found")

    update_data = preference.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(pref, field, value)

    await db.commit()
    await db.refresh(pref)
    return pref


@router.delete("/preferences/{pref_id}")
async def delete_preference(pref_id: int, db: AsyncSession = Depends(get_db)):
    """Delete a notification preference"""
    result = await db.execute(
        select(NotificationPreference).where(NotificationPreference.id == pref_id)
    )
    pref = result.scalar_one_or_none()
    if not pref:
        raise HTTPException(status_code=404, detail="Preference not found")

    await db.delete(pref)
    await db.commit()
    return {"deleted": True}


@router.post("/test/{pref_id}")
async def test_notification(
    pref_id: int,
    request: TestNotificationRequest = None,
    db: AsyncSession = Depends(get_db)
):
    """Test a notification channel by sending a test message"""
    result = await db.execute(
        select(NotificationPreference).where(NotificationPreference.id == pref_id)
    )
    pref = result.scalar_one_or_none()
    if not pref:
        raise HTTPException(status_code=404, detail="Preference not found")

    message = request.message if request else "Test notification from Aegis Mesh"
    success, error = await notification_service.test_channel(pref, message)

    # Log the test
    db_alert = AlertLog(
        message=f"[TEST] {message}",
        channel=pref.channel.value,
        success=success,
        error_message=error
    )
    db.add(db_alert)
    await db.commit()

    if success:
        return {"success": True, "message": "Test notification sent successfully"}
    else:
        return {"success": False, "error": error}
