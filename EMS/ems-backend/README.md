# EMS Backend (FastAPI + Google Sheets)

## 1. Spreadsheet setup
1. Reuse your existing Google Sheet (or a copy). Confirm these tabs and headers exist **exactly** as spelled (case-sensitive) — order of columns doesn't matter, spelling does:
   - `Users`: ID, Email, PasswordHash, Role, EmployeeID, IsActive, CreatedAt
   - `Employees`: ID, EmployeeCode, Name, Email, Phone, DOB, Designation, DepartmentID, RoleTitle, Address, JoinedDate, IsActive
   - `Departments`: ID, Name, Description, IsActive (feeds the Department dropdown in Add/Edit Employee)
   - `Attendance`: ID, EmployeeID, AttendanceDate, CheckIn, CheckOut, Status
   - `Tasks`: ID, EmployeeID, ClientName, ProjectName, Description, Status, Priority, Remarks, TaskDate, AdminStatus, AdminRemarks, CreatedAt, UpdatedAt
   - `LeaveRequests`: ID, EmployeeID, LeaveType, FromDate, ToDate, Reason, Status, AdminRemarks, ReviewedBy, CreatedAt, UpdatedAt
   - **Optional tabs** (the app works without them, those features just stay off) -- create them all at once with `python setup_sheets.py` (safe to re-run, only adds, never deletes):
     - `Holidays`: ID, Date, Name -- without it, holidays show as Absent
     - `Notifications`: ID, EmployeeID, Type, Message, RelatedID, IsRead, CreatedAt -- leave/task decisions notify the employee (bell icon in the app)
     - `Photos`: EmployeeID, Photo, UpdatedAt -- employee profile photos (employees upload their own on My Profile; admins can set/remove any from Employees -> Photo)
2. Every sheet needs at least the header row already typed in — an empty sheet raises a clear error rather than failing silently.
3. Delete/ignore any leftover `EditRequests` tab — it's not used in this version.

## 2. Google service account
1. In Google Cloud Console: create a project (or reuse one) → enable the **Google Sheets API**.
2. Create a **Service Account**, then create a JSON key for it and download it.
3. Open your spreadsheet → Share → paste the service account's email (looks like `xxx@xxx.iam.gserviceaccount.com`) → give it **Editor** access.
4. Get your **Spreadsheet ID** from its URL: `https://docs.google.com/spreadsheets/d/`**`THIS_PART`**`/edit`.

## 3. Local development
```bash
cd ems-backend
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
```
Edit `.env`:
- Paste the **entire contents** of the service account JSON key as one line into `GOOGLE_SERVICE_ACCOUNT_JSON` (or use `GOOGLE_SERVICE_ACCOUNT_FILE` pointing at the downloaded file instead).
- Set `SPREADSHEET_ID` and a real random `JWT_SECRET`.

Run it:
```bash
uvicorn main:app --reload
```
Visit `http://localhost:8000/docs` for interactive Swagger docs of every endpoint.

## 4. First admin user
There's no signup flow — seed the first admin row by hand. In a Python shell (with your venv active):
```python
from auth import hash_password
print(hash_password("your-temp-admin-password"))
```
Copy the printed hash into a new row in the `Users` sheet: `Role=admin`, `EmployeeID` left blank, `IsActive=TRUE`, `PasswordHash=<the hash>`.

## 5. Deploying to Vercel
If this backend is deployed as its own Vercel project, set the Vercel project Root Directory to `ems-backend`. The existing `main.py` exposes the FastAPI `app`.

Set these Production environment variables in the backend Vercel project:
- `SPREADSHEET_ID`
- `GOOGLE_SERVICE_ACCOUNT_JSON`
- `JWT_SECRET`
- `CORS_ORIGINS` = your exact frontend Vercel origin, e.g. `https://your-ems.vercel.app`
- `APP_TIMEZONE=Asia/Kolkata`
- `ATTENDANCE_START_DATE=2026-10-08`
- Optional: `SHEET_CACHE_TTL_SECONDS=15`

After changing environment variables, redeploy the backend. Test `GET /health`, then log in from the frontend.

## 5. Deploying to Render
1. New Web Service → connect this repo → Build command `pip install -r requirements.txt` → Start command `uvicorn main:app --host 0.0.0.0 --port $PORT --proxy-headers --forwarded-allow-ips='*'` (the last two flags make the login rate limit count each person's own IP instead of Render's proxy IP, which every employee would otherwise share).
2. Set environment variables on Render: `GOOGLE_SERVICE_ACCOUNT_JSON`, `SPREADSHEET_ID`, `JWT_SECRET`, `CORS_ORIGINS` (your Vercel domain, e.g. `https://your-app.vercel.app`).
3. Render's free tier spins down after ~15 min idle — the first request after that takes 30-60s to wake up. Fine for an internal tool.

## 6. Notes / known trade-offs
- No real transactions — two admins reviewing the same item at the same instant is a rare, accepted race condition.
- IDs are simple incrementing integers, computed as `max existing + 1` — not safe under true concurrent writes, acceptable at ~50-employee scale.
- No self-service password reset. Reset a password manually the same way the first admin user was seeded (`hash_password(...)` → paste into the `PasswordHash` cell).
- **Attendance is flexible-hours by default.** One check-in and one check-out per day; the app records the times and computes working hours. No "Late" marking unless you set `ENABLE_LATE_MARKING=true` (then `LATE_CUTOFF_HOUR`/`LATE_CUTOFF_MINUTE` apply, default 10:00). Status is computed when a page loads, not trusted from the sheet's `Status` column. Optional rules, off by default: `HALF_DAY_HOURS` and `FULL_DAY_HOURS` (e.g. `4` and `7`).
- `APP_TIMEZONE` (default `Asia/Kolkata`) decides "today" and all check-in/out times. Render servers run in UTC, so don't remove it.
- `ATTENDANCE_START_DATE` is the EMS go-live date in `YYYY-MM-DD` format (for this deployment: `2026-10-08`). Days before it are not generated as Absent and cannot be manually recorded.
- `WEEKLY_OFF_DAYS` (default `6` = Sunday; Monday=0). Use `5,6` for Saturday + Sunday.
- `SHEET_DAY_FIRST=true` if your sheet's locale shows dates as dd/mm/yyyy. Only affects reading old cells that Sheets converted into real dates; new writes use `RAW`, so dates stay as plain ISO text.
- Optional columns: `TokenVersion` on `Users` (password change/reset then logs out every old session) and `EditedBy` on `Attendance` (records which admin corrected a day).
- Admins fix forgotten check-ins/check-outs from **Attendance** in the admin sidebar. Employees can undo a mistaken check-out on the same day.
- Tests: `pip install pytest httpx && pytest tests` (uses an in-memory fake of the sheet, no Google access needed).
- **Photos** are resized in the browser to a small square JPEG (~15-30 KB) and stored as text in the `Photos` tab, one row per employee (a Sheets cell holds max 50,000 characters; the server rejects anything over 42,000 or that isn't a real JPEG). They live in their own tab so the busy `Employees` tab stays light.
- **Google quota (60 reads/min):** notifications are fetched on app load / navigation / returning to the tab, at most once a minute, with no polling. "Mark all read" is one batched write. Photos are cached in the browser.
- Login is rate-limited to 10 attempts/minute per IP via `slowapi` as basic brute-force protection.
