# TZ Status

Real-time outage tracking for Tanzania's essential services — government portals, banks, mobile money, and telecom networks.

Inspired by Downdetector, built specifically for Tanzania, where no equivalent tool currently exists.

## Features

- **Active monitoring** — pings 30+ Tanzanian services every 60 seconds (NIDA, TRA, CRDB, NMB, Vodacom, Airtel, M-Pesa, and more)

- **Crowdsourced reports** — users can report a service as down, layered on top of automated checks

- **Hourly analytics** — tracks average response time and uptime % by hour of day, surfacing peak congestion patterns (e.g. network slowdowns during peak evening hours)

- **Live dashboard** — dark, Tanzania-themed UI showing real-time status grouped by category

## Tech Stack

- **Backend:** Python, FastAPI, SQLModel

- **Database:** SQLite (local), with a path to PostgreSQL/TimescaleDB for production scale

- **Monitoring:** httpx (async HTTP checks)

- **Frontend:** Vanilla HTML/CSS/JS (no build step)

## Running locally

1. Clone the repo and create a virtual environment: