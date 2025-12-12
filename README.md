# Task Management API (FastAPI)

A production-style RESTful API for task management using **FastAPI + PostgreSQL + SQLAlchemy (async) + Alembic**.

## Features Implemented

### Core requirements ✅
- Task CRUD (with subtasks via `parent_task_id`)
- Authentication & Authorization (JWT + Role-Based Access Control)
- Database schema with migrations (Alembic)
- Fast response time design choices (async DB, pagination, indexes, lean response DTOs)
- Bulk update multiple tasks in one request (transactional)

### Product Features Chosen

I implemented the following three features:

1. **Advanced Task Filtering (AND/OR logic)**  
   Enables filtering tasks by status, priority, assignee, tags, and date ranges with flexible logical conditions. This is a core feature in real-world task management systems.

2. **Task Dependencies**  
   Allows tasks to be blocked by other tasks, modeling real execution order and enforcing dependency validation.

3. **Task Distribution & Overdue Analytics**  
   Provides managerial insights by exposing APIs that show task distribution and overdue tasks per user.

These features were chosen because they provide the highest practical value, demonstrate non-trivial backend design, and go beyond basic CRUD functionality.

## Tech Stack
- FastAPI
- PostgreSQL (Docker)
- SQLAlchemy 2.0 async
- Alembic migrations
- JWT auth (OAuth2 password flow)
- Pytest + HTTPX for tests

---

## Local Setup (Recommended)

### 1) Clone & create venv
```bash
git clone <your-repo-url>
cd task-management-api
python -m venv .venv
source .venv/bin/activate  # mac/linux
# .venv\Scripts\activate # windows
pip install -r requirements.txt
```

### 2) Start Postgres (Docker)
```bash
docker compose up -d db
```

### 3) Configure env
Create a `.env` file:
```env
DATABASE_URL=postgresql+asyncpg://taskapi:taskapi@localhost:5432/taskapi
JWT_SECRET_KEY=dev-secret-change
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=60
```

### 4) Run migrations
```bash
alembic upgrade head
```

### 5) Run API
```bash
uvicorn app.main:app --reload
```

Open:
- Swagger: http://127.0.0.1:8000/docs
- OpenAPI: http://127.0.0.1:8000/openapi.json

---

## Docker Compose (API + DB)
```bash
docker compose up --build
```

---

## Quick API Walkthrough

### Auth
1) Register:
`POST /auth/register`
```json
{ "email": "admin@x.com", "password": "Admin@123", "role": "ADMIN", "full_name": "Admin" }
```

2) Login (token):
`POST /auth/token` (form-data)
- username = email
- password = password

Use the returned `access_token` as:
`Authorization: Bearer <token>`

### Tasks
- `POST /tasks` create task (with assignees/collaborators/tags, optional `parent_task_id`)
- `GET /tasks/{id}` get task (RBAC + collaborator checks)
- `PATCH /tasks/{id}` update task (RBAC)
- `DELETE /tasks/{id}` delete task (ADMIN only)
- `PATCH /tasks/bulk` bulk update tasks (transactional)
- `POST /tasks/filter` advanced filter (AND/OR)
- `POST /tasks/{id}/dependencies` set dependencies
- `PATCH /tasks/{id}/archive` Marks task as archived instead of deleting, Records archived_at and archived_by_user_id

### Analytics
- `GET /analytics/task-distribution`
- `GET /analytics/overdue`

### Timeline (auditing)
- `GET /timeline?days=7` (changes relevant to current user)

---

## Running Tests
```bash
pytest -q
```

---

## Notes on Design / Standards
- Clear layering: `api` (routes) → `services` → `repositories` → `db`
- DTOs with Pydantic, DB models with SQLAlchemy
- RBAC in dependencies + service methods
- Transactional bulk updates
- Indexed fields for filter performance

---

## Future Enhancements
- Webhook events on task changes
- Rate limiting, request tracing, metrics (Prometheus)

