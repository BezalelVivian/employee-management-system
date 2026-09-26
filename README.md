# EMS - Employment Management System

Professional employee self-service + admin management system built with FastAPI, Jinja2, SQLAlchemy and MySQL.

## Setup

1. Create a MySQL database:
   `CREATE DATABASE ems_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;`
2. Copy `.env.example` to `.env` and update the database credentials and secret key.
3. Create and activate a virtual environment.
4. Install dependencies: `pip install -r requirements.txt`
5. Start: `uvicorn app.main:app --reload`
6. Open `http://127.0.0.1:8000`

On first startup, the application creates the tables and an admin account from `ADMIN_EMAIL` / `ADMIN_PASSWORD` if it does not already exist.

## Business rules implemented

- One attendance session per employee per day.
- Check-in twice is blocked; check-out twice is blocked.
- Working hours are calculated from check-in/check-out.
- Attendance status: Present when checked in on/before the configured late cutoff, Late after it. Absent is represented when there is no attendance and no approved leave/permission for the date; this is mainly calculated in admin/dashboard summaries because a day cannot be known to be absent until the attendance window has passed.
- Leave/permission can explain an otherwise non-attending day.
- Task edits require an employee edit request and admin approval. Admins can edit tasks directly.
- Admin has full management permissions.
- Employee profile edits can be requested and approved by an admin.
- CSRF tokens are used on state-changing forms.
