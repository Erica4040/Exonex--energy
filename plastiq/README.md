# PlastiQ — Plastic Waste Detection & Pyrolysis Yield Intelligence Platform

A full-stack system that scans waste imagery, detects and classifies plastic
polymer types using computer vision, scores pyrolysis suitability, predicts
oil/gas/carbon-black/wax yield, forecasts revenue, flags operational risks,
and generates management-ready reports — built for landfills, recycling
centers, municipal waste facilities, and plastic-to-fuel plants.

## What's real vs. what you plug in

Everything in this codebase is real, working source code — there is no
mocked-out API layer or placeholder UI. The one piece that's intentionally
swappable is **computer vision detection**:

- **`SimulatedDetector`** (default, active out of the box) generates
  deterministic, realistic plastic-composition data from any uploaded image,
  so the entire pipeline — suitability scoring, yield prediction, revenue
  forecasting, risk detection, dashboards — works end-to-end today without
  any trained model or GPU.
- **`YoloDetector`** is a ready-to-use adapter for a real Ultralytics
  YOLOv11/YOLOv12 model trained on a plastic-polymer dataset. Drop in your
  `.pt` weights, set `DETECTOR_BACKEND=yolo` in `.env`, and the rest of the
  system — database, API, frontend — needs no changes.

This split exists because training or sourcing a production-grade plastic
classifier is its own multi-week project (data collection/labeling, training,
validation) — it isn't something that can be fabricated. Everything around
it (the business logic, the math, the UI, the auth, the reporting) is
complete and correct now.

## Architecture

```
plastiq/
├── backend/                 FastAPI + SQLAlchemy + SQLite (swappable to Postgres)
│   ├── app/
│   │   ├── ml/               polymer reference data + detector interface
│   │   ├── services/         pure prediction engine (suitability/yield/revenue/risk)
│   │   ├── models/           SQLAlchemy ORM models
│   │   ├── schemas/          Pydantic request/response contracts
│   │   ├── routers/          FastAPI route handlers
│   │   ├── core/             config, DB session, JWT auth, permissions
│   │   ├── seed/             demo data loader
│   │   └── main.py           app entrypoint
│   └── tests/                 pytest suite for the prediction engine
└── frontend/                 React + Vite SPA
    └── src/
        ├── pages/             Dashboard, Batches, Batch Detail, Facilities, Settings
        ├── components/        AppLayout (sidebar), Widgets (KPI cards, flow bars, pills)
        ├── context/           Auth context (JWT session)
        └── api/               typed API client
```

### How a waste batch flows through the system

1. **Create a batch** — `POST /waste/batches` (Step 1: Receive waste)
2. **Upload an image** — `POST /waste/batches/{id}/upload-image`
3. **Run detection** — `POST /waste/detect` (Module 2/3: CV detection + classification)
4. **View composition** — `GET /waste/batches/{id}/composition` (aggregated per-polymer weights)
5. **Generate prediction report** — `POST /reports/generate` runs the full
   engine: suitability → feedstock estimate → oil/gas/char/wax yield →
   revenue forecast → risk flags → recommendations → executive summary, and
   persists it.
6. **Dashboard** — `GET /dashboard` aggregates KPIs, plastic-type breakdown,
   and trends across recent reports.

### Prediction engine (the core logic)

`app/services/prediction_engine.py` is pure Python — no FastAPI, no
database — so it's trivially unit-testable. It was verified against the
worked example in the original spec:

- Total waste 10t, with HDPE 2.1t / LDPE 1.8t / PP 1.5t suitable and PVC 0.8t
  rejected → **5.4t suitable feedstock**, **8% PVC contamination** ✓
- Yield: HDPE 2.1×80% + LDPE 1.8×85% + PP 1.5×75% → **4.335t oil** (spec
  rounds to 4.34t) ✓
- Revenue: oil at $600/ton → **$2,601** (spec: $2,604, rounding) ✓
- PVC is excluded entirely from yield calculations (not just down-weighted),
  and flagged as a CRITICAL risk above the contamination threshold ✓

Run the test suite yourself:
```bash
cd backend
pytest tests/ -v
```

## User roles

Adapted from a generic manufacturing role matrix into this domain:

| Role | Can do |
|---|---|
| **Administrator** | Manage users, facilities, scan sources, AI/pricing settings, view all reports |
| **Plant Manager** | Create batches, view forecasts, monitor operations, approve schedules |
| **Feedstock Manager** | Manage waste intake, monitor suitable-feedstock inventory |
| **Operator** | Trigger scans/detection, log production, submit reports |
| **Executive** | View dashboards, KPIs, BI reports — read-only oversight |

## Setup

### Option A — Docker Compose (easiest)

```bash
docker compose up --build
```
- Backend: http://localhost:8000 (docs at `/docs`)
- Frontend: http://localhost:80

### Option B — Run locally

**Backend** (requires Python 3.10+):
```bash
cd backend
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env            # adjust if needed; defaults work as-is
uvicorn app.main:app --reload --port 8000
```
First boot auto-creates the SQLite DB and seeds demo data (set
`SEED_DEMO_DATA=false` in `.env` to skip).

**Frontend** (requires Node 18+):
```bash
cd frontend
npm install
npm run dev
```
Visit http://localhost:5173 — Vite proxies `/api` to the backend automatically.

### Demo login

| Email | Role | Password |
|---|---|---|
| `admin@plastiq.demo` | Administrator | `ChangeMe123!` |
| `manager@plastiq.demo` | Plant Manager | `ChangeMe123!` |
| `operator@plastiq.demo` | Operator | `ChangeMe123!` |
| `exec@plastiq.demo` | Executive | `ChangeMe123!` |

**Change these before any real deployment** — also rotate `SECRET_KEY` in
`.env`, which signs JWT auth tokens.

## Plugging in a real YOLO model

1. Train or source a YOLOv11/v12 model with classes matching `PlasticType`
   (PET, HDPE, LDPE, PP, PS, PVC, MIXED) — order matters, it must match
   `YOLO_CLASS_MAP` in `app/core/config.py`.
2. `pip install ultralytics`
3. Place weights at the path set in `YOLO_MODEL_PATH`.
4. Set `DETECTOR_BACKEND=yolo` in `.env`.
5. Restart the backend. No other code changes needed — `app/ml/detector.py`'s
   `get_detector()` factory handles the swap.

Note: real bounding-box weight estimation needs either a calibrated
area-to-mass regression or sensor fusion (a scale, volumetric/depth camera,
or conveyor load cell) — `YoloDetector` currently returns `estimated_weight_kg=0.0`
as a flagged TODO since that calibration is plant-specific and can't be
fabricated generically. Wire your weighbridge/scale data into the batch's
`total_weight_tons` field as an interim measure (already supported — see
`WasteBatchCreate.total_weight_tons`).

## Calibrating yield coefficients

Default yield percentages (`app/ml/polymer_reference.py`) are literature
midpoint estimates. As you accumulate real pyrolysis run data, override them
per-facility via `AISettings.yield_overrides_json` (exposed through
`PATCH /facilities/{id}/ai-settings` — extend the settings page UI to edit
this JSON, or call the API directly) so predictions converge to your plant's
actual performance over time.

## What to build next

- Live camera/RTSP ingestion for CCTV/conveyor feeds (currently file-upload based)
- Drone flight-path integration for yard-level surveys
- Calibration job that fits yield coefficients from historical `pyrolysis_reports` data
- Bounding-box overlay viewer on the uploaded image (data is already stored — `DetectedItem.bbox_*` — just needs an `<img>` + absolutely-positioned `<div>` overlay component)
- Postgres migration for multi-facility production use (swap `DATABASE_URL`; SQLAlchemy models are already portable)
- Alembic migrations (currently using `create_all` for simplicity)
