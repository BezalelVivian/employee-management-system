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
1. New Project → import this repo → set **Root Directory** to `ems-frontend` → framework preset **Vite** (build `npm run build`, output `dist`; `vercel.json` already says so and adds the SPA rewrite so refreshing `/admin/attendance` works).
2. Set the environment variable `VITE_API_BASE_URL` to your API's URL (e.g. `https://your-ems-api.vercel.app`) for **Production** (and Preview). Vite bakes it in at build time, so **redeploy after changing it**. If you forget, the login page now tells you exactly that, instead of silently calling `localhost`.
3. Deploy.
4. Add this frontend's URL to the backend's `CORS_ORIGINS` env var and redeploy the backend, otherwise the browser blocks every request.
5. Smoke test: open the site → log in as admin → Employees → Attendance. Then `https://<api>/health` should say `{"status":"ok"}`.

## Known gaps / next passes
- No toast/notification system — save/error feedback is shown as inline banners on each page.
- No client-side route-level code splitting — fine at this app's size, worth revisiting only if it grows a lot.
- Admin "Department ID" is a free-text field (the spec leaves `Departments`' schema up to your existing sheet) — if you want a dropdown populated from the `Departments` tab, tell me its actual column names and I'll wire it up.
