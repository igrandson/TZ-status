import os
import asyncio
from contextlib import asynccontextmanager
from datetime import datetime, timedelta

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlmodel import Session, select

from app.database import engine, init_db
from app.models import Service, StatusCheck, OutageReport, ServiceComponent, ComponentCheck
from app.monitor import run_monitor_loop
from app.services_seed import SEED_SERVICES


COMPONENT_SEEDS = {
    "CRDB": [
        {"name": "Website", "url": "https://crdbbank.co.tz", "weight": 0.10},
        {"name": "Internet Banking", "url": "https://ib.crdbbank.com", "weight": 0.30},
        {"name": "Mobile App", "url": None, "weight": 0.15},
        {"name": "USSD", "url": None, "weight": 0.15},
        {"name": "ATM Network", "url": None, "weight": 0.15},
        {"name": "Card Payments", "url": None, "weight": 0.15},
    ],
    "NMB": [
        {"name": "Website", "url": "https://www.nmbbank.co.tz", "weight": 0.10},
        {"name": "Internet Banking", "url": None, "weight": 0.30},
        {"name": "Mobile App", "url": None, "weight": 0.15},
        {"name": "USSD", "url": None, "weight": 0.15},
        {"name": "ATM Network", "url": None, "weight": 0.15},
        {"name": "Card Payments", "url": None, "weight": 0.15},
    ],
    "Vodacom": [
        {"name": "Website", "url": "https://www.vodacom.co.tz", "weight": 0.10},
        {"name": "Voice", "url": None, "weight": 0.25},
        {"name": "SMS", "url": None, "weight": 0.15},
        {"name": "Internet", "url": None, "weight": 0.25},
        {"name": "M-Pesa", "url": "https://www.vodacom.co.tz/m-pesa", "weight": 0.25},
    ],
    "NIDA": [
        {"name": "Website", "url": "https://www.nida.go.tz", "weight": 0.30},
        {"name": "Search Service", "url": None, "weight": 0.25},
        {"name": "Verification", "url": None, "weight": 0.25},
        {"name": "API", "url": None, "weight": 0.20},
    ],
}


def seed_services():
    """Insert catalog services missing from the database (matched by URL)."""
    with Session(engine) as session:
        existing_urls = {
            (s.url or "").rstrip("/").lower()
            for s in session.exec(select(Service)).all()
        }
        existing_names = {s.name for s in session.exec(select(Service)).all()}
        added = 0
        for entry in SEED_SERVICES:
            url_key = (entry.get("url") or "").rstrip("/").lower()
            if url_key in existing_urls or entry["name"] in existing_names:
                continue
            session.add(Service(**entry))
            existing_urls.add(url_key)
            existing_names.add(entry["name"])
            added += 1
        if added:
            session.commit()


def seed_components():
    with Session(engine) as session:
        existing = session.exec(select(ServiceComponent)).first()
        if existing:
            return

        for service_name, components in COMPONENT_SEEDS.items():
            service = session.exec(
                select(Service).where(Service.name == service_name)
            ).first()
            if not service:
                continue
            for comp in components:
                component_type = comp.get("component_type")
                if not component_type:
                    name_key = (comp["name"] or "").lower()
                    if "website" in name_key:
                        component_type = "website"
                    elif "mobile app" in name_key or "app" in name_key:
                        component_type = "app"
                    elif "ussd" in name_key:
                        component_type = "ussd"
                    elif "atm" in name_key:
                        component_type = "atm"
                    elif "card" in name_key or "payment" in name_key:
                        component_type = "payment"
                    elif "api" in name_key:
                        component_type = "api"
                    elif "voice" in name_key:
                        component_type = "voice"
                    elif "sms" in name_key:
                        component_type = "sms"
                    elif "internet" in name_key:
                        component_type = "internet"
                    else:
                        component_type = "other"

                session.add(ServiceComponent(
                    service_id=service.id,
                    name=comp["name"],
                    component_type=component_type,
                    url=comp["url"],
                    weight=comp["weight"],
                ))
        session.commit()
    with Session(engine) as session:
        existing_urls = {
            (s.url or "").rstrip("/").lower()
            for s in session.exec(select(Service)).all()
        }
        existing_names = {s.name for s in session.exec(select(Service)).all()}
        added = 0
        for entry in SEED_SERVICES:
            url_key = entry["url"].rstrip("/").lower()
            if url_key in existing_urls or entry["name"] in existing_names:
                continue
            session.add(Service(**entry))
            existing_urls.add(url_key)
            existing_names.add(entry["name"])
            added += 1
        if added:
            session.commit()


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    seed_services()
    seed_components()
    monitor_task = asyncio.create_task(run_monitor_loop(interval_seconds=60))
    yield
    monitor_task.cancel()


app = FastAPI(title="TZ Status", lifespan=lifespan) 

from fastapi.middleware.cors import CORSMiddleware

app.mount("/static", StaticFiles(directory="static"), name="static")

allowed_origins_raw = os.getenv("ALLOWED_ORIGINS", "*")
allowed_origins = [origin.strip() for origin in allowed_origins_raw.split(",") if origin.strip()]
allow_credentials = allowed_origins != ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=allow_credentials,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root():
    return FileResponse("static/index.html")


@app.get("/services")
def list_services():
    with Session(engine) as session:
        return session.exec(select(Service)).all()


DEGRADED_THRESHOLD_MS = 3000  # responses slower than this count as degraded


@app.get("/status")
def current_status():
    with Session(engine) as session:
        services = session.exec(select(Service)).all()
        result = []
        for service in services:
            latest = session.exec(
                select(StatusCheck)
                .where(StatusCheck.service_id == service.id)
                .order_by(StatusCheck.checked_at.desc())
            ).first()

            if not latest:
                status = None
            elif not latest.is_up:
                status = "down"
            elif latest.response_time_ms and latest.response_time_ms > DEGRADED_THRESHOLD_MS:
                status = "degraded"
            else:
                status = "up"

            result.append({
                "id": service.id,
                "service": service.name,
                "category": service.category,
                "is_up": latest.is_up if latest else None,
                "status": status,
                "response_time_ms": latest.response_time_ms if latest else None,
                "last_checked": latest.checked_at if latest else None,
            })
        return result


@app.post("/report/{service_id}")
def report_outage(service_id: int, region: str = None):
    with Session(engine) as session:
        service = session.get(Service, service_id)
        if not service:
            return {"error": "Service not found"}

        report = OutageReport(service_id=service_id, region=region)
        session.add(report)
        session.commit()
        session.refresh(report)
        return {"message": f"Report received for {service.name}", "report_id": report.id}


@app.get("/reports/{service_id}")
def get_reports(service_id: int, last_hours: int = 24):
    with Session(engine) as session:
        cutoff = datetime.utcnow() - timedelta(hours=last_hours)
        reports = session.exec(
            select(OutageReport)
            .where(OutageReport.service_id == service_id)
            .where(OutageReport.reported_at >= cutoff)
        ).all()
        return {
            "service_id": service_id,
            "report_count": len(reports),
            "last_hours": last_hours,
            "reports": reports,
        }
        from sqlalchemy import func


@app.get("/analytics/{service_id}/hourly")
def hourly_analytics(service_id: int, days: int = 7):
    """
    Average response time and uptime % grouped by hour of day,
    over the last N days. Helps spot peak congestion hours
    (e.g. Vodacom slowing down at night).
    """
    with Session(engine) as session:
        cutoff = datetime.utcnow() - timedelta(days=days)
        checks = session.exec(
            select(StatusCheck)
            .where(StatusCheck.service_id == service_id)
            .where(StatusCheck.checked_at >= cutoff)
        ).all()

        if not checks:
            return {"service_id": service_id, "hourly": []}

        buckets = {}
        for check in checks:
            hour = check.checked_at.hour
            if hour not in buckets:
                buckets[hour] = {"total": 0, "up": 0, "response_times": []}
            buckets[hour]["total"] += 1
            if check.is_up:
                buckets[hour]["up"] += 1
            if check.response_time_ms:
                buckets[hour]["response_times"].append(check.response_time_ms)

        hourly = []
        for hour in sorted(buckets.keys()):
            b = buckets[hour]
            avg_response = (
                sum(b["response_times"]) / len(b["response_times"])
                if b["response_times"] else None
            )
            hourly.append({
                "hour": hour,
                "uptime_pct": round((b["up"] / b["total"]) * 100, 1),
                "avg_response_ms": round(avg_response, 1) if avg_response else None,
                "sample_count": b["total"],
            })

        return {"service_id": service_id, "days_analyzed": days, "hourly": hourly}


@app.get("/analytics/{service_id}/daily")
def daily_analytics(service_id: int, days: int = 30):
    """
    Day-by-day uptime % and avg response time.
    This is the foundation for yearly trend views.
    """
    with Session(engine) as session:
        cutoff = datetime.utcnow() - timedelta(days=days)
        checks = session.exec(
            select(StatusCheck)
            .where(StatusCheck.service_id == service_id)
            .where(StatusCheck.checked_at >= cutoff)
        ).all()

        if not checks:
            return {"service_id": service_id, "daily": []}

        buckets = {}
        for check in checks:
            day = check.checked_at.date().isoformat()
            if day not in buckets:
                buckets[day] = {"total": 0, "up": 0, "response_times": []}
            buckets[day]["total"] += 1
            if check.is_up:
                buckets[day]["up"] += 1
            if check.response_time_ms:
                buckets[day]["response_times"].append(check.response_time_ms)

        daily = []
        for day in sorted(buckets.keys()):
            b = buckets[day]
            avg_response = (
                sum(b["response_times"]) / len(b["response_times"])
                if b["response_times"] else None
            )
            daily.append({
                "date": day,
                "uptime_pct": round((b["up"] / b["total"]) * 100, 1),
                "avg_response_ms": round(avg_response, 1) if avg_response else None,
                "sample_count": b["total"],
            })

        return {"service_id": service_id, "days_analyzed": days, "daily": daily}