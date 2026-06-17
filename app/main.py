from fastapi import FastAPI
from contextlib import asynccontextmanager
from sqlmodel import Session, select
from datetime import datetime, timedelta
import asyncio

from app.database import engine, init_db
from app.models import Service, StatusCheck, OutageReport
from app.monitor import run_monitor_loop

SEED_SERVICES = [
    # Government
    {"name": "NIDA", "category": "government", "url": "https://www.nida.go.tz"},
    {"name": "TRA", "category": "government", "url": "https://www.tra.go.tz"},
    {"name": "BRELA", "category": "government", "url": "https://www.brela.go.tz"},
    {"name": "HESLB", "category": "government", "url": "https://www.heslb.go.tz"},
    {"name": "eGA / Government Portal", "category": "government", "url": "https://www.ega.go.tz"},
    {"name": "NHIF", "category": "government", "url": "https://www.nhif.or.tz"},
    {"name": "NSSF", "category": "government", "url": "https://www.nssf.or.tz"},
    {"name": "NSSF", "category": "government", "url": "https://www.nssf.go.tz"},
    {"name": "TCRA", "category": "government", "url": "https://www.tcra.go.tz"},
    {"name": "Tanzania Railways Corporation", "category": "government", "url": "https://www.trc.co.tz"},
    {"name": "Ajira Portal", "category": "government", "url": "https://ajira.go.tz"},

    # Banks
    {"name": "CRDB Bank", "category": "bank", "url": "https://crdbbank.co.tz"},
    {"name": "NMB Bank", "category": "bank", "url": "https://www.nmbbank.co.tz"},
    {"name": "NBC Bank", "category": "bank", "url": "https://www.nbc.co.tz"},
    {"name": "Equity Bank Tanzania", "category": "bank", "url": "https://equitygroupholdings.com/tz"},
    {"name": "Stanbic Bank Tanzania", "category": "bank", "url": "https://www.stanbicbank.co.tz"},
    {"name": "DTB Tanzania", "category": "bank", "url": "https://www.dtbtanzania.com"},
    {"name": "Exim Bank Tanzania", "category": "bank", "url": "https://www.eximbank-tz.com"},
    {"name": "Akiba Commercial Bank", "category": "bank", "url": "https://www.akibabank.com"},
    {"name": "Absa Bank Tanzania", "category": "bank", "url": "https://www.absa.co.tz"},

    # Telecom
    {"name": "Vodacom Tanzania", "category": "telecom", "url": "https://www.vodacom.co.tz"},
    {"name": "Airtel Tanzania", "category": "telecom", "url": "https://www.airtel.co.tz"},
    {"name": "TTCL", "category": "telecom", "url": "https://www.ttcl.co.tz"},
    {"name": "Yas (Tigo)", "category": "telecom", "url": "https://www.yas.co.tz"},
    {"name": "Halotel", "category": "telecom", "url": "https://www.halotel.co.tz"},
    {"name": "Zantel", "category": "telecom", "url": "https://www.zantel.co.tz"},

    # Mobile Money / Fintech
    {"name": "M-Pesa Tanzania", "category": "mobile_money", "url": "https://www.vodacom.co.tz/m-pesa"},
    {"name": "Mixx by Yas (Tigo Pesa)", "category": "mobile_money", "url": "https://www.yas.co.tz/mixx-by-yas"},
    {"name": "Airtel Money", "category": "mobile_money", "url": "https://www.airtel.co.tz/airtel-money"},
    {"name": "Halopesa", "category": "mobile_money", "url": "https://www.halotel.co.tz/halopesa"},
    {"name": "Selcom", "category": "mobile_money", "url": "https://selcommobile.com"},

    # Popular apps / e-commerce
    {"name": "Jumia Tanzania", "category": "app", "url": "https://www.jumia.co.tz"},
    {"name": "Kilimall Tanzania", "category": "app", "url": "https://www.kilimall.co.tz"},
]


def seed_services():
    with Session(engine) as session:
        existing = session.exec(select(Service)).first()
        if existing:
            return
        for s in SEED_SERVICES:
            session.add(Service(**s))
        session.commit()


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    seed_services()
    monitor_task = asyncio.create_task(run_monitor_loop(interval_seconds=60))
    yield
    monitor_task.cancel()


app = FastAPI(title="TZ Status", lifespan=lifespan) 

from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root():
    return {"message": "TZ Status API running"}


@app.get("/services")
def list_services():
    with Session(engine) as session:
        return session.exec(select(Service)).all()


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
            result.append({
                "id": service.id,
                "service": service.name,
                "category": service.category,
                "is_up": latest.is_up if latest else None,
                "last_checked": latest.checked_at if latest else None,
            })
        return result


@app.post("/report/{service_id}")


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