# gym-tracker

Local strength training journal. I log sessions, bodyweight/sleep/kcal, look at 1RM trends, and occasionally run models (goal forecast, anomalies, a rough weight suggestion).

Stack: FastAPI + SQLAlchemy/SQLite + Alembic, Streamlit on the frontend. The UI talks to the API only — no direct ORM access.

## Requirements

- Python 3.11–3.12
- [uv](https://github.com/astral-sh/uv)

## Setup

```bash
make install
cp .env.example .env
make db-up
```

Two processes:

```bash
make run-api
make run-frontend
```

## How I use it

1. Add exercises.
2. (Optional) daily metrics — bodyweight, sleep, kcal.
3. Training — session + sets. 1RM is computed on the backend; you don't type it in.
4. Analytics — charts.
5. Goals & models — 1RM goal, manual Prophet / Isolation Forest training, alert feedback.
6. Data — backup / export / import.

Session splits: PUSH, PULL, LEGS, UPPER, LOWER, OTHER.

## Models (minimums)

Without enough history nothing useful comes out:

| What | Minimum |
| --- | --- |
| 1RM forecast (Prophet) | ≥ 8 training days, span ≥ 28 days, 1RM can't be almost flat |
| Anomalies (Isolation Forest) | ≥ 8 sessions; alert only on outlier **and** drop ≥ ~5% vs trend |
| Weight suggestion (Ridge) | ≥ 12 complete feature rows (sleep/bodyweight/RPE help) |

Model training is manual — a normal forecast GET does not train anything. Old models aren't deleted; if data changes they just show as stale.

A 1RM goal is required to **read** the crossing date. Training Prophet itself only needs the exercise history.

## Useful commands

```bash
make test
make lint
make db-up
```

Reset local DB:

```bash
rm -f data/gym_tracker.db
make db-up
```

## Notes

- Single-user localhost tool, not a SaaS.
- Anomaly alerts aren't medical advice — just a signal that a session looks weaker than the recent trend.
- Data files (`*.db`, backups, joblib) are gitignored.
