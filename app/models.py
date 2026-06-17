from sqlmodel import SQLModel, Field
from typing import Optional
from datetime import datetime


class Service(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    category: str  # "government", "bank", "mobile_money", "telecom"
    url: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


class StatusCheck(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    service_id: int = Field(foreign_key="service.id")
    is_up: bool
    response_time_ms: Optional[int] = None
    status_code: Optional[int] = None
    checked_at: datetime = Field(default_factory=datetime.utcnow)


class OutageReport(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    service_id: int = Field(foreign_key="service.id")
    reported_at: datetime = Field(default_factory=datetime.utcnow)
    region: Optional[str] = None  # e.g. "Mwanza", "Dar es Salaam"