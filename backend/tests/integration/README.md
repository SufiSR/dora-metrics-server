# Backend integration tests

## Plan (concise)

1. **Environment:** Real **PostgreSQL 16** via **testcontainers** (requires **Docker**). **Alembic** `upgrade head` once per session. The FastAPI app uses `TestClient`; env is like local dev but **no** real GitLab/Jira endpoints (tokens may be empty).
2. **Migrations / DB:** `alembic_version`, core table presence, `SELECT 1` (`test_migrations.py`).
3. **API:** Public metrics, repositories, sync, MTTR, health; validation (404, 400, 422); auth + admin config; raw tables 404; data health (authenticated); manual sync 202; webhook test with **respx**-mocked HTTP (`test_api_validation_and_admin_smoke.py`, `test_admin_webhook_httpx.py`, `test_public_metrics_and_sync.py`, `test_auth_admin_api.py`).
4. **Collectors (HTTP + DB):** `test_collectors_on_postgres.py` uses the real `GitLabTagsClient` and `JiraBugsClient` (real `httpx.Client`), with **`respx`** mock routes for the same URLs the collectors call (`/api/v4/...` for GitLab, `/rest/api/3/search/jql` and `.../worklog` for Jira) — no in-process fakes of those classes.
5. **Out of scope / next:** End-to-end against **live** GitLab/Jira hosts, full `run_nightly_sync` through the stack, browser E2E.

## Inventory (test modules)

| Module | What |
|--------|------|
| `conftest.py` | Postgres + Alembic, `api_client`, `session_factory` |
| `test_migrations.py` | Schema + Alembic revision |
| `test_auth_admin_api.py` | Health, login, admin config, logout |
| `test_public_metrics_and_sync.py` | Public read routes + unauth admin 401 |
| `test_api_validation_and_admin_smoke.py` | 404/400/422, raw tables, data-health, MTTR releases, manual sync 202 |
| `test_admin_webhook_httpx.py` | Admin webhook test + **respx** |
| `test_collectors_on_postgres.py` | GitLab + Jira collectors: real `httpx` + `respx` stubs + Postgres |

**Tracking** [DEVOPS-517](https://plunet.atlassian.net/browse/DEVOPS-517) under [DEVOPS-446](https://plunet.atlassian.net/browse/DEVOPS-446). Implementation status is also updated in Jira comments on that subtask.

## How to run

From the `backend` directory (so `alembic.ini` resolves):

```bash
cd backend
pytest tests/integration/ -m integration
```

Add `respx` if needed: `pip install respx` (declared in `backend/requirements.txt`).

If Docker is not running, the suite **skips** (fixtures require the daemon). Unit tests: `pytest tests/unit/`.
