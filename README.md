# EMS - Employee Management System

Employee self-service + admin management. Two parts, deployed as **two Vercel projects**:

| Folder | What | Stack |
| --- | --- | --- |
| `ems-frontend/` | The website people use | React + Vite |
| `ems-backend/`  | The API | FastAPI (Python), data stored in a Google Sheet |

Setup and deployment details live in each folder's README:
[`ems-backend/README.md`](ems-backend/README.md) and [`ems-frontend/README.md`](ems-frontend/README.md).

## Go-live checklist (Vercel)

1. **Backend project** - Root Directory `ems-backend`. Environment variables: `SPREADSHEET_ID`, `GOOGLE_SERVICE_ACCOUNT_JSON`, `JWT_SECRET`, `CORS_ORIGINS`, **`EMS_START_DATE`** (your go-live date, `YYYY-MM-DD`), `APP_TIMEZONE`, `SHEET_CACHE_TTL_SECONDS=15`.
2. Open `https://<backend>/health` -> `{"status":"ok"}`.
3. **Frontend project** - Root Directory `ems-frontend`. Environment variable `VITE_API_BASE_URL=https://<backend>`.
4. Put the frontend URL into the backend's `CORS_ORIGINS` and redeploy the backend.
5. From your computer, once: `cd ems-backend && python setup_sheets.py && python check_sheets.py`.
6. Log in as admin, add your employees (use their real joining date), and add the company holidays.

## How attendance statuses work

| Status | Meaning |
| --- | --- |
| Present / Late / Half Day / Short Hours | The person checked in (Late/Half Day/Short Hours only if you switch those rules on) |
| Missing Check-out | A past day with a check-in but no check-out - an admin can fix it |
| On Leave | Approved full-day leave |
| Holiday / Weekly Off | Not a working day |
| **Absent** | A working day, EMS was tracking that person, and there is no check-in and no approved leave |
| **Not Tracked** | A working day **before** the person could use EMS (before `EMS_START_DATE`, or before their login was created). It is **not** an absence. Admins can back-fill real times with Edit |

So an employee who joined on 24 Sep at a company that started using EMS on 8 Oct shows **Not Tracked** for 24 Sep - 7 Oct and is only marked Absent for working days from 8 Oct onwards.

## Running the tests

```bash
cd ems-backend
pip install -r requirements.txt pytest httpx
pytest tests
```

The tests use an in-memory fake of the spreadsheet; no Google access is needed.
