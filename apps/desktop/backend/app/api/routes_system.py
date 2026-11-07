"""
System monitor and network diagnostics REST API.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List

from app.database.connection import get_db
from app.database.models import EventLog
from app.services.system_monitor import system_monitor
from app.services.network_service import NetworkService

router = APIRouter(prefix="/api/system", tags=["system"])

@router.get("/metrics")
def get_metrics():
    """
    Returns CPU, RAM, and network throughput metrics.
    """
    return system_monitor.get_metrics()

@router.get("/network")
def get_network_interfaces():
    """
    Returns all active network interfaces (Wi-Fi, USB Tethering, Ethernet).
    """
    return {
        "local_ip": NetworkService.get_local_ip(),
        "interfaces": NetworkService.get_all_interfaces()
    }

@router.get("/logs")
def get_recent_logs(limit: int = 50, db: Session = Depends(get_db)):
    """
    Returns recent system and connection event logs.
    """
    logs = db.query(EventLog).order_by(EventLog.timestamp.desc()).limit(limit).all()
    return {
        "logs": [
            {
                "id": l.id,
                "level": l.level,
                "source": l.source,
                "message": l.message,
                "details": l.details,
                "timestamp": l.timestamp.isoformat() if l.timestamp else None
            }
            for l in reversed(logs)
        ]
    }

