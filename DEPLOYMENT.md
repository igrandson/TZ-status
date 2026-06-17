# TZ Status — Deployment Plan (for when you're ready)

This is not urgent. Keep developing and collecting data locally for now.

This document exists so the path forward is clear whenever you decide to go live.

## Current state (Phase 1 — where you are now)

- Running locally via `uvicorn app.main:app --reload`

- Data stored in local SQLite `tz_status.db`)

- Frontend opened directly as a file `static/index.html`)

- Zero cost, but requires your PC to be on and the terminal running to collect data

This is the right setup for now. Keep building features and accumulating

historical data. No rush to deploy until the core experience feels solid.

## Phase 2 — Going live (when ready, still $0)

**Goal:** A real public URL anyone can visit, without paying anything.

### Backend + Frontend hosting: Render (free tier)

- Connect your GitHub repo to Render, it auto-deploys on every push

- Free tier limitations to expect:

  - Spins down after 15 minutes of no traffic

  - First request after sleep takes 30-60 seconds to "wake up" (cold start)

  - ~750 free hours/month (plenty for one small service running continuously,

    since a month only has ~720 hours total)

- This is fine for a side project / portfolio piece. Not fine yet for something

  you'd want instantly responsive 24/7 — that's a future paid-tier upgrade if

  this ever needs to feel production-grade.

### Database: Neon or Supabase (free tier) — NOT Render's free Postgres

Render's free PostgreSQL deletes itself after 90 days. Since the entire point

of this project is multi-year historical data, that's a dealbreaker. Use one

of these instead:

- **Neon** — scales to zero when idle, wakes on next request, no fixed deletion

  date. Free tier: 1 project, 3 GiB per branch, shared compute.

- **Supabase** — pauses after 7 days of no activity, wakes on next visit. Free

  tier: 500MB database, 2 projects max.

Either works. Since your monitor will be pinging the database every 60 seconds

once live, it should rarely (if ever) actually go idle long enough to pause.

**Recommendation: start with Neon** — slightly more generous on the "scale to

zero vs hard pause" mechanics for a constantly-active workload like this.

## Phase 3 — Migration steps (when you reach this point)

1. Update `app/database.py` to point at a PostgreSQL connection string instead

   of SQLite (swap `sqlite:///tz_status.db` for the Neon/Supabase connection

   URL — they each give you this after creating a free project)

2. Install `psycopg2-binary` (the PostgreSQL driver for Python)

3. Test locally against the cloud database before deploying

4. Push to GitHub, connect Render, set environment variables (database URL,

   etc.) in Render's dashboard — never commit secrets directly into the repo

5. Update the frontend's `API_BASE` constant from `http://127.0.0.1:8000` to

   your new Render URL

## Phase 4 — Backup safety net (do this regardless of hosting choice)

Even with a "permanent" free database, things can go wrong (account issues,

policy changes, accidental deletion). Write a simple script that periodically

exports your data to a local file or GitHub as a backup. This can be as

simple as a scheduled `pg_dump` or a Python script hitting your own API and

saving the JSON locally. Worth building once the cloud database is live.

## Summary

| Phase | Cost | What happens |

|---|---|---|

| 1 (now) | $0 | Local only, your PC must be on |

| 2 | $0 | Public URL via Render, free tier limits apply |

| 3 | $0 | Real persistent database via Neon/Supabase |

| 4 | $0 | Backup script for peace of mind |

| Future | $7+/mo | Only if you outgrow free tiers (real traffic, need instant response) |

No step here requires payment. Revisit this when the local version feels done

and you're ready for other people to actually use it.