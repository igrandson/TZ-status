from sqlmodel import SQLModel, Field
from typing import Optional
from datetime import datetime


# =====================
# EXISTING TABLES
# =====================

class Service(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)

    name: str
    category: str

    url: Optional[str] = None

    created_at: datetime = Field(
        default_factory=datetime.utcnow
    )


class StatusCheck(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)

    service_id: int = Field(
        foreign_key="service.id"
    )

    is_up: bool

    response_time_ms: Optional[int] = None

    status_code: Optional[int] = None

    checked_at: datetime = Field(
        default_factory=datetime.utcnow
    )


class OutageReport(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)

    service_id: int = Field(
        foreign_key="service.id"
    )

    reported_at: datetime = Field(
        default_factory=datetime.utcnow
    )

    region: Optional[str] = None


# =====================
# V2 TABLES
# =====================

class ServiceComponent(SQLModel, table=True):
    id: Optional[int] = Field(
        default=None,
        primary_key=True
    )

    service_id: int = Field(
        foreign_key="service.id"
    )

    name: str

    component_type: str
    # website
    # app
    # api
    # ussd
    # payment
    # voice
    # sms
    # internet
    # atm

    url: Optional[str] = None

    weight: int = 10

    created_at: datetime = Field(
        default_factory=datetime.utcnow
    )


class ComponentCheck(SQLModel, table=True):
    id: Optional[int] = Field(
        default=None,
        primary_key=True
    )

    component_id: int = Field(
        foreign_key="servicecomponent.id"
    )

    is_up: bool

    response_time_ms: Optional[int] = None

    status_code: Optional[int] = None

    checked_at: datetime = Field(
        default_factory=datetime.utcnow
    )


class Incident(SQLModel, table=True):
    id: Optional[int] = Field(
        default=None,
        primary_key=True
    )

    service_id: int = Field(
        foreign_key="service.id"
    )

    component_id: Optional[int] = Field(
        default=None,
        foreign_key="servicecomponent.id"
    )

    started_at: datetime = Field(
        default_factory=datetime.utcnow
    )

    ended_at: Optional[datetime] = None

    severity: str = "minor"
    status: str = "active"

    description: Optional[str] = None


class CrowdReport(SQLModel, table=True):
    id: Optional[int] = Field(
        default=None,
        primary_key=True
    )

    service_id: int = Field(
        foreign_key="service.id"
    )

    component_id: Optional[int] = Field(
        default=None,
        foreign_key="servicecomponent.id"
    )

    region: str

    issue_type: str

    description: Optional[str] = None

    reported_at: datetime = Field(
        default_factory=datetime.utcnow
    )


class Region(SQLModel, table=True):
    id: Optional[int] = Field(
        default=None,
        primary_key=True
    )

    name: str

    latitude: float
    longitude: float

