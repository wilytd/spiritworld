"""
Alerts API Router
Cross-protocol notification system
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import httpx
import os
from typing import List

from database import get_db
from models import AlertLog
from schemas import AlertCreate, AlertResponse

router = APIRouter()

@router.post("/send", response_model=AlertResponse)
async def send_alert(alert: AlertCreate, db: AsyncSession = Depends(get_db)):
    """Send an alert through the specified channel"""

    success = False
    error_message = None

    if alert.channel == "mesh":
        # Send via mesh bridge
        mesh_url = os.getenv("MESH_BRIDGE_URL", "http://mesh-bridge:8001")
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    f"{mesh_url}/send",
                    json={"message": alert.message}
                )
                success = response.status_code == 200
                if not success:
                    error_message = f"Mesh bridge returned {response.status_code}"
        except Exception as e:
            error_message = str(e)

    elif alert.channel == "webhook":
        webhook_url = os.getenv("WEBHOOK_URL")
        if not webhook_url:
            error_message = "WEBHOOK_URL not configured"
        else:
            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    response = await client.post(
                        webhook_url,
                        json={"text": alert.message}
                    )
                    success = response.status_code in [200, 201, 204]
                    if not success:
                        error_message = f"Webhook returned {response.status_code}"
            except Exception as e:
                error_message = str(e)

    else:
        error_message = f"Unknown channel: {alert.channel}"

    # Log the alert
    db_alert = AlertLog(
        message=alert.message,
        channel=alert.channel,
        success=success,
        error_message=error_message
    )
    db.add(db_alert)
    await db.commit()
    await db.refresh(db_alert)

    return db_alert

@router.get("/history", response_model=List[AlertResponse])
async def get_alert_history(
    limit: int = 50,
    db: AsyncSession = Depends(get_db)
):
    """Get recent alert history"""
    result = await db.execute(
        select(AlertLog)
        .order_by(AlertLog.sent_at.desc())
        .limit(limit)
    )
    return result.scalars().all()
