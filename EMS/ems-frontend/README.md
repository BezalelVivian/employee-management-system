# EMS Frontend (React + Vite)

## Local development
```bash
cd ems-frontend
npm install
cp .env.example .env
```
Edit `.env` so `VITE_API_BASE_URL` points at your running backend (defaults to `http://localhost:8000`, matching the backend's default `uvicorn` port).

```bash
npm run dev
```
Visit `http://localhost:5173`.

## What's here
- **Routing**: `react-router-dom`, role-gated via `ProtectedRoute` — an employee account is redirected away from `/admin/*` and vice versa.
- **State**: plain `fetch` (in `src/api/client.js`) + React Context for the logged-in user (`src/context/AuthContext.jsx`). No React Query — not needed at this scale, and it keeps the dependency list small.
- **Auth**: JWT is stored in `localStorage`, attached as `Authorization: Bearer <token>` on every request. A `401` response clears it and bounces to `/login` automatically.
- **Pages**: `src/pages/employee/*` (Dashboard, Profile, Attendance, Tasks, Leave) and `src/pages/admin/*` (Dashboard, Employees, Task Review, Leave Review), matching Section 5 of the spec.

## Deploying to Vercel
1. New Project → import this repo (or just the `ems-frontend` folder if it's its own repo) → framework preset **Vite**.
2. Set the environment variable `VITE_API_BASE_URL` to your Render backend's URL (e.g. `https://your-app.onrender.com`).
3. Deploy. Build command `npm run build`, output directory `dist` (Vercel detects both automatically for Vite).
4. Once deployed, add this Vercel URL to the backend's `CORS_ORIGINS` env var on Render and redeploy the backend — otherwise the browser will block every request.

## Known gaps / next passes
- No toast/notification system — save/error feedback is shown as inline banners on each page.
- No client-side route-level code splitting — fine at this app's size, worth revisiting only if it grows a lot.
- Admin "Department ID" is a free-text field (the spec leaves `Departments`' schema up to your existing sheet) — if you want a dropdown populated from the `Departments` tab, tell me its actual column names and I'll wire it up.
