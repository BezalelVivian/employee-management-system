# EMS Backend (FastAPI + Google Sheets)

## 1. Spreadsheet setup
1. Reuse your existing Google Sheet (or a copy). Confirm these tabs and headers exist **exactly** as spelled (case-sensitive) — order of columns doesn't matter, spelling does:
   - `Users`: ID, Email, PasswordHash, Role, EmployeeID, IsActive, CreatedAt
   - `Employees`: ID, EmployeeCode, Name, Email, Phone, DOB, Designation, DepartmentID, RoleTitle, Address, JoinedDate, IsActive
   - `Departments`: whatever columns you already use
   - `Attendance`: ID, EmployeeID, AttendanceDate, CheckIn, CheckOut, Status
   - `Tasks`: ID, EmployeeID, ClientName, ProjectName, Description, Status, Priority, Remarks, TaskDate, AdminStatus, AdminRemarks, CreatedAt, UpdatedAt
   - `LeaveRequests`: ID, EmployeeID, LeaveType, FromDate, ToDate, Reason, Status, AdminRemarks, ReviewedBy, CreatedAt, UpdatedAt
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

## 5. Deploying to Render
1. New Web Service → connect this repo → Build command `pip install -r requirements.txt` → Start command `uvicorn main:app --host 0.0.0.0 --port $PORT`.
2. Set environment variables on Render: `GOOGLE_SERVICE_ACCOUNT_JSON`, `SPREADSHEET_ID`, `JWT_SECRET`, `CORS_ORIGINS` (your Vercel domain, e.g. `https://your-app.vercel.app`).
3. Render's free tier spins down after ~15 min idle — the first request after that takes 30-60s to wake up. Fine for an internal tool.

## 6. Notes / known trade-offs
- No real transactions — two admins reviewing the same item at the same instant is a rare, accepted race condition.
- IDs are simple incrementing integers, computed as `max existing + 1` — not safe under true concurrent writes, acceptable at ~50-employee scale.
- No self-service password reset. Reset a password manually the same way the first admin user was seeded (`hash_password(...)` → paste into the `PasswordHash` cell).
- `LATE_CUTOFF_HOUR`/`LATE_CUTOFF_MINUTE` env vars control the check-in cutoff for marking `Status=Late` (default 9:30).
- Login is rate-limited to 10 attempts/minute per IP via `slowapi` as basic brute-force protection.
