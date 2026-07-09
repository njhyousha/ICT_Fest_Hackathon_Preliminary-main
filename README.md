# CoWork — Coworking Space Booking API

A production-style multi-tenant REST API for managing bookable rooms inside a coworking space. Built for the **IUT ICT Fest Hackathon (Preliminary Round)**, this project implements a fully-specified booking system with strict business rules around concurrency, refunds, quotas, and multi-tenant data isolation.

> Grading was black-box — every rule below had to hold under real concurrent load, not just on the happy path.

---

## ✨ Highlights

- **Multi-tenant architecture** — every organization's rooms, staff, and bookings are fully isolated; cross-org access returns `404` instead of leaking existence
- **Concurrency-safe booking engine** — no double-booking, no quota bypass, and unique reference codes even under simultaneous requests
- **JWT auth system** — access + refresh tokens (HS256), single-use refresh token rotation, and immediate token invalidation on logout
- **Automated refund calculator** — tiered cancellation policy (100% / 50% / 0%) with precise half-cent rounding
- **Rate limiting** — rolling 60-second window per user on booking creation
- **Live admin reporting** — per-room usage reports, availability, and stats computed on demand, always consistent with underlying data
- **Dockerized** — one command (`docker compose up --build`) spins up the full stack with zero manual DB setup

---

## 🛠 Tech Stack

| Layer | Technology |
|---|---|
| Language | Python 3.11 |
| Framework | FastAPI |
| ORM / DB | SQLAlchemy + SQLite |
| Auth | JWT (HS256), access + refresh tokens |
| Testing | Pytest |
| Deployment | Docker / Docker Compose |

---

## 🚀 Getting Started

```bash
docker compose up --build
```

The API will be live at `http://localhost:8000`. No manual migrations or seeding needed — schema is created automatically on first run.

### Running Tests

```bash
pip install -r requirements.txt
pytest
```

---

## 📐 Business Rules Implemented

- **Booking pricing:** `price_cents = hourly_rate_cents × duration_hours` (1–8 whole hours, must start in the future)
- **No double-booking:** interval-overlap check per room, safe under concurrent writes
- **Booking quota:** max 3 confirmed bookings per member within any rolling 24-hour window
- **Rate limiting:** 20 requests / 60 seconds per user on `POST /bookings`
- **Refund policy:** 100% (≥48h notice) / 50% (24–48h) / 0% (<24h), rounded to the nearest cent
- **Pagination:** stable, gap-free ordering by `start_time`, ties broken by `id`

---

## 📡 API Overview

| Method | Path | Description |
|---|---|---|
| POST | `/auth/register` | Register org admin or join as member |
| POST | `/auth/login` | Get access + refresh tokens |
| POST | `/auth/refresh` | Rotate tokens |
| POST | `/auth/logout` | Invalidate current access token |
| GET / POST | `/rooms` | List / create rooms |
| GET | `/rooms/{id}/availability` | Busy time slots for a date |
| GET | `/rooms/{id}/stats` | Live booking count & revenue |
| GET / POST | `/bookings` | List / create bookings |
| POST | `/bookings/{id}/cancel` | Cancel with refund calculation |
| GET | `/admin/usage-report` | Org-wide revenue report |
| GET | `/admin/export` | Bookings as CSV |
| GET | `/health` | Health check |

Full request/response schemas and error codes are documented in the API contract used for grading.

---

## 📂 Project Structure

```
app/
├── routers/       # API route handlers (auth, bookings, rooms, admin, health)
├── services/       # Business logic (refunds, rate limiting, notifications, stats...)
├── models.py        # SQLAlchemy models
├── schemas.py        # Pydantic request/response schemas
├── auth.py          # JWT auth logic
├── database.py        # DB session/engine setup
├── config.py         # App configuration
├── cache.py          # Caching layer
├── errors.py          # Custom error handling
└── main.py           # FastAPI app entrypoint
tests/
├── test_smoke.py       # Smoke tests
└── test_bug_hunt.py      # Edge-case & bug-hunt tests
```

---

## 🏆 About This Project

Built as part of the **IUT ICT Fest Hackathon** preliminary round, where the challenge was to debug and harden an existing FastAPI codebase against a strict, fully-specified business contract — with grading done entirely through black-box API testing against concurrent, adversarial test cases.
