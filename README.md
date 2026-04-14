# DEMS Repository Manual (Detailed)

This document is a thorough analysis + user manual for this repository, written to be directly convertible to PDF.

---

## 1) Project Overview

### What this repository implements

This repository contains a **Digital Evidence Management System (DEMS)** with:

- A **FastAPI backend** (`dems_backend/app`) for authentication, user administration, case lifecycle, evidence handling, custody chain, and audit logging.
- A **PostgreSQL database** (configured directly or via Docker Compose).
- A **React frontend** (`dems_backend/dems_frontend`) for role-based operations.
- Local **evidence file storage** on disk (`evidences/`), with metadata stored in PostgreSQL.

### Problem domain

The system models a law-enforcement style workflow:

1. Admin creates users (inspector/officer/admin).
2. Inspector creates a case and assigns officers.
3. Inspector/officer add evidence to the case.
4. Inspector records custody transfer/possession history.
5. Every important operation writes to an audit trail.

---

## 2) Repository Structure

```text
DBMS/
├── README.md                         # This manual
└── dems_backend/
    ├── app/
    │   ├── main.py                   # FastAPI app bootstrap, CORS, scheduler, routers
    │   ├── config.py                 # Environment settings model
    │   ├── database.py               # SQLAlchemy engine/session/base
    │   ├── models.py                 # ORM models / table definitions
    │   ├── oauth2.py                 # JWT creation + verification + current user dependency
    │   ├── utils.py                  # password hash/verify, audit helper, badge/password generation, emails
    │   ├── routers/                  # API routes grouped by feature
    │   │   ├── auth.py
    │   │   ├── users.py
    │   │   ├── cases.py
    │   │   ├── evidence.py
    │   │   ├── custody.py
    │   │   └── audit.py
    │   └── schemas/                  # Pydantic request/response schemas
    ├── dems_frontend/
    │   ├── App.jsx                   # Main UI (role-based views in one file)
    │   ├── api.js                    # Frontend API client wrapper
    │   ├── App.css
    │   ├── main.jsx
    │   ├── index.html
    │   ├── package.json
    │   └── vite.config.js
    ├── Dockerfile
    ├── docker-compose.yml
    ├── requirements.txt
    ├── .env.example
    └── .env
```

---

## 3) Technology Stack

### Backend

- Python 3.11
- FastAPI
- SQLAlchemy 2.x
- psycopg2-binary (PostgreSQL driver)
- python-jose (JWT)
- passlib + bcrypt_sha256 (password hashing)
- APScheduler (periodic background checks)

### Frontend

- React 18
- Vite 5
- Plain JavaScript (no TypeScript in the active frontend entry files)

### Database

- PostgreSQL 15 (Docker image used in compose)

---

## 4) Architecture and Runtime Flow

### High-level architecture

```text
[React Frontend]
      |
      | HTTP + Bearer JWT
      v
[FastAPI Backend]
      | \
      |  \---> local filesystem (evidences/case_xxx/...)
      v
[PostgreSQL]
```

### App startup behavior

From `app/main.py`:

- Creates scheduler and configures missing-file job.
- Registers startup and shutdown handlers for scheduler.
- Calls `Base.metadata.create_all(bind=engine)` to create tables if absent.
- Enables CORS for:
  - `http://localhost:5173`
  - `http://127.0.0.1:5173`
- Includes all routers:
  - `users`, `cases`, `evidence`, `custody`, `audit`, `auth`

---

## 5) Data Model (Database Analysis)

## 5.1 Tables and columns

### `users`

- `UserID` (PK)
- `Name` (required)
- `Role` (required; values used in code: `admin`, `inspector`, `officer`)
- `BadgeNumber` (required, unique)
- `Contact` (nullable)
- `Status` (default `"ACTIVE"`)
- `LastLogin` (nullable timestamp with tz)
- `Password` (required hash)
- `Email` (required)

### `cases`

- `CaseID` (PK)
- `Title` (required)
- `Type` (required)
- `Status` (required)
- `DateOpened` (default now)
- `DateClosed` (nullable)
- `Description` (nullable text)
- `ActingInspectorID` (int, required)

### `case_assignments`

- `id` (PK)
- `CaseID` (FK -> `cases.CaseID`, cascade on delete)
- `AssignedOfficerId` (FK -> `users.UserID`, cascade on delete)

### `evidenceitems`

- `EvidenceID` (PK)
- `CaseID` (FK -> `cases.CaseID`, set null on delete)
- `Description` (nullable)
- `EvidenceType` (required)
- `SourceOrigin` (required)
- `DateCollected` (default now)
- `SubmittingOfficerID` (FK -> `users.UserID`, set null on delete)
- `FilePath` (nullable, path to physical file)

### `custodyrecords`

- `RecordID` (PK)
- `EvidenceID` (FK -> `evidenceitems.EvidenceID`, set null on delete)
- `Timestamp` (default now)
- `ActingOfficerID` (FK -> `users.UserID`, set null on delete)
- `Notes` (nullable)

### `auditlog`

- `LogID` (PK)
- `Timestamp` (default now)
- `UserID` (FK -> `users.UserID`, set null on delete)
- `EventType` (`READ` / `CREATE` / `UPDATE` / `DELETE`)
- `Details` (text)

## 5.2 Conceptual relationships

```text
users (admin/inspector/officer)
  ├──< cases via ActingInspectorID (logical owner)
  ├──< case_assignments >── cases
  ├──< evidenceitems (SubmittingOfficerID)
  ├──< custodyrecords (ActingOfficerID)
  └──< auditlog (UserID)

cases
  └──< evidenceitems

evidenceitems
  └──< custodyrecords
```

## 5.3 Important design note

Evidence files are stored on disk, not in DB blobs.  
Therefore, **database backup alone is not enough**. You must also back up the `evidences/` directory.

---

## 6) Authentication and Authorization

## 6.1 Auth flow

1. Client posts to `POST /login` using form data (`username` = badge number, `password`).
2. Backend verifies hashed password via Passlib.
3. Backend checks user status is `ACTIVE`.
4. Backend issues JWT with payload `{ BadgeNumber, exp }`.
5. Client calls protected endpoints using:
   - `Authorization: Bearer <token>`

## 6.2 Current user resolution

- `oauth2.get_current_user`:
  - Decodes JWT
  - Extracts `BadgeNumber`
  - Fetches user from DB
  - Raises `401` if invalid/missing

## 6.3 Role model

- `admin`
- `inspector`
- `officer`

Role checks are enforced inside each router function (server-side).

---

## 7) Feature-by-Feature Behavior

## 7.1 Users module (`/users`)

### Main capabilities

- Admin creates users.
- Badge number and temporary password are auto-generated on create.
- Credentials are emailed to the user.
- Admin can list/update/delete users.
- Any logged-in user can change own password (`/users/change-password`).
- Admin/Inspector can fetch active officers (`/users/officers/active`).

### Notable implementation details

- Create route expects `Name`, `Role`, `Contact`, `Email`, `Status`.
- Password is not accepted from request body during user create/update.
- Password change requires correct old password.

## 7.2 Cases module (`/cases`)

### Main capabilities

- Inspector creates cases and can assign officers.
- Inspector can update, close, and remove/add officers on their own cases.
- Officer can view assigned cases.
- Admin/Inspector can list all cases.
- Admin can delete cases.
- Officers or acting inspector can reactivate inactive cases.

### Key business rules

- Only `inspector` can create cases.
- Only the acting inspector for that case can mutate assignments/case details.
- `close` sets status to inactive and sets `DateClosed`.
- `reactivate` only works if case is inactive.

## 7.3 Evidence module (`/evidence`)

### Main capabilities

- Inspector or assigned officer uploads evidence files.
- Any authenticated user can list/download evidence for a case.
- Inspector or assigned officer can update evidence metadata.
- Admin can delete evidence and the underlying file.

### File handling behavior

- Upload endpoint is `multipart/form-data`.
- Server creates folder `evidences/case_<CaseID>/`.
- Saved filename pattern:
  - `case_id<CaseID>_evidence_id<EvidenceID>.<ext>`
- `FilePath` column stores this path.

### Integrity monitoring

- `utils.check_missing_files` scans DB paths and emails alert if file missing.
- Scheduler in `main.py` runs this job periodically.

## 7.4 Custody module (`/custody`)

### Main capabilities

- Inspector can add custody records.
- All authenticated users can read custody records.
- Inspector can update custody records.
- Admin can delete custody records.

### Key business checks

- Evidence must exist.
- Case linked to evidence must exist.
- Case must be active.
- Inspector must be acting inspector of that case to add custody.
- Duplicate `(EvidenceID, ActingOfficerID)` pair is blocked in add route.

## 7.5 Audit module (`/audit`)

### Main capabilities

- Admin-only endpoint to query audit logs.
- Supports pagination + filters:
  - `user_id`, `search`, `from_date`, `to_date`, `limit`, `skip`

### Logging strategy

Most business operations write an audit log row through `create_log`.

## 7.6 Auth module (`/login`, `/me`)

- `POST /login` returns token.
- `GET /me` returns current user profile.

---

## 8) API Endpoint Catalog

All protected routes require bearer token unless explicitly public (none of business routes are public).

### Auth

- `POST /login`
- `GET /me`

### Users

- `POST /users/` (admin)
- `GET /users/` (admin)
- `GET /users/officers/active` (admin, inspector)
- `PUT /users/{badge_num}` (admin)
- `DELETE /users/{badge_num}` (admin)
- `POST /users/change-password` (all authenticated)

### Cases

- `POST /cases/` (inspector)
- `GET /cases/` (admin, inspector)
- `GET /cases/assigned` (inspector, officer)
- `GET /cases/assigned/{officer_id}` (admin, inspector)
- `GET /cases/assigned-officers/{case_id}` (admin, inspector, with ownership checks)
- `POST /cases/{case_id}/assign` (inspector-owner)
- `POST /cases/{case_id}/remove-officers` (inspector-owner)
- `PUT /cases/{case_id}` (inspector-owner)
- `PUT /cases/{case_id}/close` (inspector-owner)
- `PUT /cases/{case_id}/reactivate` (assigned officer or acting inspector)
- `DELETE /cases/{case_id}` (admin)

### Evidence

- `POST /evidence/` (inspector-owner, assigned officer)
- `GET /evidence/case/{case_id}` (all authenticated)
- `GET /evidence/{case_id}/{evidence_id}/download` (all authenticated)
- `PUT /evidence/{case_id}/{evidence_id}` (inspector-owner, assigned officer; blocked for inactive case)
- `DELETE /evidence/{evidence_id}` (admin)

### Custody

- `POST /custody/` (inspector-owner)
- `GET /custody/` (all authenticated)
- `GET /custody/{record_id}` (all authenticated)
- `PUT /custody/{record_id}` (inspector)
- `DELETE /custody/{record_id}` (admin)

### Audit

- `GET /audit/` (admin)

---

## 9) Pydantic Contracts (Important Request Bodies)

## 9.1 User creation

`POST /users/`

```json
{
  "Name": "John Doe",
  "Role": "officer",
  "Contact": "9876543210",
  "Email": "john@example.com",
  "Status": "ACTIVE"
}
```

## 9.2 Case creation

`POST /cases/`

```json
{
  "Title": "Arms Seizure 2026-04-01",
  "Type": "Criminal",
  "Status": "Open",
  "Description": "Initial report",
  "AssignedOfficerIDs": [11, 12]
}
```

## 9.3 Assign/remove officers

`POST /cases/{case_id}/assign` and `POST /cases/{case_id}/remove-officers`

```json
{
  "officer_ids": [11, 12]
}
```

## 9.4 Evidence upload

`POST /evidence/` as multipart with fields:

- `CaseID` (int)
- `Description` (string, optional)
- `EvidenceType` (string)
- `SourceOrigin` (string)
- `file` (binary)

## 9.5 Evidence metadata update

`PUT /evidence/{case_id}/{evidence_id}`

```json
{
  "Description": "Updated label",
  "EvidenceType": "Weapon",
  "SourceOrigin": "Crime Scene"
}
```

## 9.6 Custody create/update

`POST /custody/`

```json
{
  "EvidenceID": 101,
  "ActingOfficerID": 12,
  "Notes": "Received from inspector at station locker"
}
```

`PUT /custody/{record_id}`

```json
{
  "ActingOfficerID": 14,
  "Notes": "Transferred to forensic lab unit"
}
```

## 9.7 Change password

`POST /users/change-password`

```json
{
  "oldPassword": "old_password_here",
  "newPassword": "new_password_here"
}
```

---

## 10) Frontend Manual (How to Use the System)

The frontend is an SPA implemented mainly in `dems_backend/dems_frontend/App.jsx`.

## 10.1 Login

1. Open app URL (Vite default: `http://localhost:5173`).
2. Enter badge number and password.
3. On success, token/user are stored in session storage and dashboard opens.

## 10.2 Navigation by role

### Admin sees

- Dashboard
- Cases
- Users
- Audit Log
- Profile

### Inspector sees

- Dashboard
- Cases
- Profile

### Officer sees

- Dashboard
- Cases
- Profile

## 10.3 Cases screen usage

### Inspector workflow

1. Create case.
2. Assign officers to case.
3. Open case detail.
4. Add/update evidence.
5. Add/update custody records.
6. Close case when complete.
7. Reactivate if needed.

### Officer workflow

1. Open assigned cases.
2. Add or update evidence for assigned cases.
3. View custody chain.
4. Reactivate inactive case only if assigned (business rule permits).

### Admin workflow

1. Browse all cases.
2. Open details and evidence/custody views.
3. Delete case if needed.

## 10.4 User management (Admin)

1. Create user with name/role/contact/email/status.
2. System auto-generates badge + temporary password.
3. Credentials are emailed.
4. Edit user metadata/status.
5. Delete user (cannot delete currently logged-in admin).

## 10.5 Audit usage (Admin)

1. Open Audit Log view.
2. Filter by user, text, date range.
3. Inspect recent activity first (sorted descending).

## 10.6 Profile and password updates

All roles can change their own password from Profile view.

---

## 11) Environment Configuration

`.env.example` includes all required keys from `config.py`.

Use this as a complete template:

```env
DATABASE_HOSTNAME=postgres
DATABASE_PORT=5432
DATABASE_PASSWORD=dems_password
DATABASE_NAME=dems_db
DATABASE_USERNAME=dems_user

SECRET_KEY=replace_with_a_long_random_secret
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60

SENDER_MAIL=your_sender@gmail.com
SUPERADMIN_MAIL=your_admin@gmail.com
APP_PASSWORD_MAIL=your_gmail_app_password
APP_SCHEDULING_TIME=30
```

### Email notes

- Gmail SMTP (`smtp.gmail.com:587`) is used in `utils.py`.
- `app_password_mail` should be an App Password, not normal account password.

---

## 12) Setup and Run Guide

## 12.1 Option A: Run with Docker Compose (recommended for quick local setup)

From project root:

```bash
cp .env.example .env
docker compose up --build
```

This starts three services:

- Frontend on `http://localhost:5173`
- Backend API on `http://localhost:8000`
- PostgreSQL on `localhost:5432`

## 12.2 Option B: Run backend directly

Use this mode if you are not using Docker for local development.

Set DB variables in `.env` to your local PostgreSQL values (`DATABASE_HOSTNAME=localhost`, etc.), then:

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## 12.3 Run frontend

From `dems_backend/dems_frontend`:

```bash
npm install
npm run dev
```

Frontend API base is hardcoded in `api.js`:

- `API_BASE = 'http://localhost:8000'`

---

## 13) First Admin Bootstrap

On backend startup, the system now checks for existing users with role `admin`.

- If at least one admin exists, nothing is created.
- If no admin exists, one bootstrap admin is inserted automatically.

### Bootstrap configuration (via `.env`)

Use these variables (available in `.env.example`):

- `BOOTSTRAP_ADMIN_NAME`
- `BOOTSTRAP_ADMIN_BADGE`
- `BOOTSTRAP_ADMIN_PASSWORD`
- `BOOTSTRAP_ADMIN_EMAIL`
- `BOOTSTRAP_ADMIN_CONTACT`

After first successful startup/login, change this password immediately for security.

---

## 14) Operations, Backup, and Maintenance

## 14.1 Backup strategy

You must back up both:

- PostgreSQL database
- `evidences/` directory

If you restore DB only, many evidence file paths may break.

## 14.2 Missing file monitor

- Scheduler periodically calls `check_missing_files`.
- If missing files found, it sends email alert to `superadmin_mail`.

## 14.3 Health check

- `GET /` returns:

```json
{ "status": "running" }
```

---

## 15) Security and Governance Notes

### Strengths present in code

- Password hashing (bcrypt_sha256 via Passlib)
- JWT-based auth
- Role checks in backend routes
- Audit logging on most critical actions
- User status enforcement on login

### Risks / improvement points (important for report)

- `Base.metadata.create_all()` is useful for dev but migrations (Alembic) are preferred for production.
- Secrets should never be committed in source control.
- Some ownership checks are strict and role behavior should be tested end-to-end before deployment.
- Consider file storage hardening (checksums, malware scan, immutable archive strategy).

---

## 16) Quick API Testing Snippets

## 16.1 Login

```bash
curl -X POST "http://localhost:8000/login" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=ADM12345&password=your_password"
```

## 16.2 Get profile

```bash
curl "http://localhost:8000/me" \
  -H "Authorization: Bearer <ACCESS_TOKEN>"
```

## 16.3 List cases

```bash
curl "http://localhost:8000/cases/?limit=20&skip=0" \
  -H "Authorization: Bearer <ACCESS_TOKEN>"
```

## 16.4 Upload evidence

```bash
curl -X POST "http://localhost:8000/evidence/" \
  -H "Authorization: Bearer <ACCESS_TOKEN>" \
  -F "CaseID=1" \
  -F "Description=Knife recovered near scene" \
  -F "EvidenceType=Weapon" \
  -F "SourceOrigin=Crime Scene" \
  -F "file=@/path/to/photo.jpg"
```

---



# DBMS Workspace — Digital Evidence Management System (DEMS)

This document is both a **technical report** on what the database and application do, and a **user manual** for operating the system end to end.

---

## Part 1 — Repository and database analysis report

### 1.1 What this project is

The workspace centers on **`dems_backend`**, a **Digital Evidence Management System** for law-enforcement–style workflows:

- **Cases** are opened and owned by an **acting inspector**, with **officers** assigned to work them.
- **Evidence** (metadata + uploaded files) is tied to cases; files are stored on disk under an `evidences/` folder, with paths recorded in the database.
- **Chain of custody** rows link evidence to the officer responsible at a point in time.
- **Audit logs** record who did what (create, read, update, delete style events) for accountability.
- **Users** authenticate with **badge number + password**; JWT bearer tokens protect the API.

A **React (Vite + TypeScript)** web app lives in `dems_backend/dems_frontend/` and proxies API calls to the FastAPI server during development.

### 1.2 Technology stack

| Layer | Technology |
|--------|------------|
| API | FastAPI (Python) |
| ORM / schema sync | SQLAlchemy; `Base.metadata.create_all()` on startup creates tables if missing |
| Database | PostgreSQL 15 (Docker Compose) or any PostgreSQL instance you configure |
| Auth | OAuth2 password flow (`POST /login`), JWT (`python-jose`), passwords hashed with Passlib (`bcrypt_sha256`) |
| Frontend | React, Vite, TypeScript; dev proxy to `http://127.0.0.1:8000` |

### 1.3 Logical data model (what the database is “about”)

Entities map to these tables (names as in SQLAlchemy):

#### `users`

Personnel accounts: name, role (`admin` | `inspector` | `officer`), unique badge number, contact, status (`ACTIVE` / inactive), last login, password hash.

#### `cases`

Investigations or matters: title, type, status, description, opened/closed timestamps, **acting inspector** (`ActingInspectorID` — a user id, not a foreign key in the model but semantically tied to `users`).

#### `case_assignments`

Many-to-many between cases and assigned officers (`CaseID`, `AssignedOfficerId`). Deleting a case cascades assignments.

#### `evidenceitems`

Evidence for a case: description, type, source/origin, collection time, submitting officer, optional `FilePath` after upload.

#### `custodyrecords`

Custody events: evidence id, timestamp, acting officer, notes.

#### `auditlog`

Append-only style log: timestamp, optional user id, event type string, free-text details.

### 1.4 Relationships (conceptual)

```
users ──────────────┬──────────── cases (ActingInspectorID)
      │               │
      │               └── case_assignments ── users (assigned officers)
      │
      ├── evidenceitems (SubmittingOfficerID)
      └── custodyrecords (ActingOfficerID)

evidenceitems ── CaseID ──► cases
custodyrecords ── EvidenceID ──► evidenceitems
auditlog ── UserID ──► users (nullable on delete)
```

### 1.5 Files vs database

Binary evidence is **not** stored in PostgreSQL. The API writes files under `evidences/case_{CaseID}/` and stores the relative path in `evidenceitems.FilePath`. A background job (`check_missing_files` in `app/utils.py`) can email alerts if DB paths point to missing files; scheduling for that job is present but commented out in `app/main.py`.

### 1.6 Security and governance (as implemented)

- Role checks on routes enforce separation of duties (e.g. only **admin** deletes cases/evidence/custody records and reads audit logs; **inspectors** manage cases and custody creation; **officers** work assigned cases).
- Sensitive actions are mirrored into `auditlog` via `create_log()`.
- **Admins** cannot upload or modify evidence through the API (by design in `evidence` routes).

---

## Part 2 — User manual: managing the system

### 2.1 Prerequisites

- Python 3 with dependencies from `dems_backend/requirements.txt`
- PostgreSQL (local or remote)
- Node.js (for the React frontend)
- Optional: Docker + Docker Compose for the bundled Postgres + API layout

### 2.2 Configuration (environment)

Copy `dems_backend/.env.example` to `.env` inside `dems_backend` and set at least:

- `DATABASE_HOSTNAME`, `DATABASE_PORT`, `DATABASE_USERNAME`, `DATABASE_PASSWORD`, `DATABASE_NAME`
- `SECRET_KEY`, `ALGORITHM`, `ACCESS_TOKEN_EXPIRE_MINUTES`

The application also expects (from `app/config.py`): `sender_mail`, `superadmin_mail`, `app_password_mail`, `app_scheduling_time` — used for optional email alerts, not for core CRUD.

**Docker Compose note:** The sample `docker-compose.yml` sets Postgres user `pashantraj`, password `dbproject`, database `fastapi`, and exposes Postgres on host port **5433**. Your `.env` must match whatever database you actually run.

### 2.3 Starting the backend

From `dems_backend`:

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Interactive API documentation: **http://127.0.0.1:8000/docs** (Swagger UI).

Health check: **GET /** returns `{"status":"running"}`.

### 2.4 Starting the frontend

From `dems_backend/dems_frontend`:

```bash
npm install
npm run dev
```

The Vite dev server proxies `/login`, `/me`, `/users`, `/cases`, `/evidence`, `/custody`, and `/audit` to the backend. Open the URL Vite prints (typically **http://localhost:5173**).

### 2.5 First-time access: creating an admin user

There is **no built-in seed script** in this repo. You need at least one row in `users` with `Role = 'admin'` and a **bcrypt-hashed** password (same scheme as `app.utils.hash`). Practical options:

1. Temporarily add a small script that calls `hash()` and `INSERT`, or  
2. Use `POST /users/` once you already have a token from an existing admin (chicken-and-egg: first user must be created by SQL or a one-off script).

After a user exists, log in through the UI (**Login** page) or `POST /login` with form fields `username` = badge number, `password` = plain password.

### 2.6 Roles and what each role can do

| Capability | Admin | Inspector | Officer |
|------------|:-----:|:---------:|:-------:|
| Create / list / update / delete users | Yes | No | No |
| View audit log (`GET /audit/`) | Yes | No | No |
| Delete case | Yes | No | No |
| Delete evidence | Yes | No | No |
| Delete custody record | Yes | No | No |
| Create case; assign/remove officers; update/close own cases | No | Yes (own cases) | No |
| List all cases (with filters) | Yes | Yes | No |
| See “my” cases | No | Own as inspector | Assigned only |
| Add / list / download / update evidence | No | Own cases | Assigned cases only |
| Create custody record | No | Yes | No |
| Update custody record | Yes | Yes | No |
| List custody records | Yes | Yes | Yes |

**Login:** inactive users (`Status` not `ACTIVE`) cannot authenticate.

### 2.7 Typical workflows (web UI)

The app routes (from `dems_frontend/src/App.tsx`) are:

| Path | Who | Purpose |
|------|-----|---------|
| `/login` | All | Sign in with badge + password |
| `/` | All | Home |
| `/cases` | Logged-in | Case lists (behavior depends on role; API enforces rules) |
| `/cases/new` | Inspector | Create a case and assign officers |
| `/cases/:caseId` | Logged-in | Case detail, assignments, updates, close case (inspector) |
| `/evidence/:caseId` | Logged-in | Evidence for that case: upload, list, download, edit |
| `/users` | Admin | User CRUD |
| `/custody` | Logged-in | Custody listing and inspector actions |
| `/audit` | Admin | Searchable audit log |

Use the in-app navigation from the shell layout after login.

### 2.8 API quick reference (for scripts or Postman)

Unless noted, send header: `Authorization: Bearer <access_token>`.

**Auth**

- `POST /login` — body: `application/x-www-form-urlencoded` (`username` = badge, `password`)
- `GET /me` — current user profile

**Users** (admin)

- `POST /users/`, `GET /users/`, `PUT /users/{badge_num}`, `DELETE /users/{badge_num}`  
  Query params on list: `badge_num`, `status_isActive`, `search`, `limit`, `skip`

**Cases**

- `POST /cases/` — create (inspector); body includes `AssignedOfficerIDs`
- `GET /cases/` — all cases with pagination/search/status (admin, inspector)
- `GET /cases/assigned` — my cases (inspector: acting; officer: assigned)
- `GET /cases/assigned/{officer_id}` — cases assigned to an officer (admin, inspector)
- `GET /cases/assigned-officers/{case_id}` — officers on a case (inspector owning that case)
- `POST /cases/{case_id}/assign`, `POST /cases/{case_id}/remove-officers`
- `PUT /cases/{case_id}`, `PUT /cases/{case_id}/close`
- `DELETE /cases/{case_id}` — admin only

**Evidence**

- `POST /evidence/` — `multipart/form-data`: `CaseID`, `Description`, `EvidenceType`, `SourceOrigin`, `file`
- `GET /evidence/case/{case_id}` — list (optional `search`, `limit`, `skip`)
- `GET /evidence/{case_id}/{evidence_id}/download`
- `PUT /evidence/{case_id}/{evidence_id}` — JSON body (cannot update if case status is closed/inactive as enforced)
- `DELETE /evidence/{evidence_id}` — admin only

**Custody**

- `POST /custody/` — create (inspector); duplicate (same evidence + officer) is rejected
- `GET /custody/`, `GET /custody/{record_id}` — filters: `Evidence_id`, `ActingOfficerID`, pagination
- `PUT /custody/{record_id}` — admin or inspector
- `DELETE /custody/{record_id}` — admin only

**Audit**

- `GET /audit/` — admin only; query: `user_id`, `search`, `from_date`, `to_date`, `limit`, `skip`

### 2.9 Operating tips

1. **Backups:** Back up PostgreSQL and the `evidences/` directory together; restoring only the DB will break downloads if files are missing.
2. **Case closure:** Closing a case sets status to inactive and blocks evidence updates for that case.
3. **Port conflicts:** Compose maps Postgres to **5433** on the host to avoid clashing with a local 5432 instance.
4. **Production:** Change default Compose credentials, use strong `SECRET_KEY`, HTTPS, and restrict CORS/proxy as needed; this README describes the project as shipped for development/study.

---

## Repository layout (summary)

```
DBMS/
└── dems_backend/           # FastAPI app + Docker
    ├── app/                  # models, routers, schemas, auth
    ├── dems_frontend/        # React UI
    ├── docker-compose.yml
    ├── Dockerfile
    ├── requirements.txt
    └── .env.example
```

---

