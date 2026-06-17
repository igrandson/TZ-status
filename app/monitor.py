import httpx
import asyncio
from datetime import datetime
from sqlmodel import Session, select
from app.database import engine
from app.models import Service, StatusCheck

TIMEOUT_SECONDS = 10

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
}


async def check_service(client: httpx.AsyncClient, service: Service) -> StatusCheck:
    start = datetime.utcnow()
    is_up = False
    status_code = None
    response_time_ms = None

    try:
        response = await client.get(
            service.url,
            timeout=TIMEOUT_SECONDS,
            follow_redirects=True,
            headers=HEADERS,
        )
        status_code = response.status_code
        response_time_ms = int((datetime.utcnow() - start).total_seconds() * 1000)
        is_up = status_code < 500

    except httpx.ConnectError as e:
        # SSL/cert misconfig means the server IS reachable, just broken cert.
        # Don't report a misconfigured cert as a full outage.
        if "CERTIFICATE_VERIFY_FAILED" in str(e) or "SSL" in str(e).upper():
            is_up = True
            status_code = 0  # 0 = special marker for "SSL issue, but alive"
        else:
            is_up = False
    except (httpx.ConnectTimeout, httpx.ReadTimeout):
        is_up = False
    except httpx.RequestError:
        is_up = False

    return StatusCheck(
        service_id=service.id,
        is_up=is_up,
        response_time_ms=response_time_ms,
        status_code=status_code,
    )


async def check_all_services():
    with Session(engine) as session:
        services = session.exec(select(Service)).all()

        async with httpx.AsyncClient() as client:
            tasks = [check_service(client, s) for s in services]
            results = await asyncio.gather(*tasks)

        for result in results:
            session.add(result)
        session.commit()

        for service, result in zip(services, results):
            status = "UP" if result.is_up else "DOWN"
            if result.status_code == 0:
                code_label = "SSL issue"
            elif result.status_code:
                code_label = result.status_code
            else:
                code_label = "no response"
            print(f"[{datetime.utcnow()}] {service.name}: {status} ({code_label})")


async def run_monitor_loop(interval_seconds: int = 60):
    while True:
        await check_all_services()
        await asyncio.sleep(interval_seconds)