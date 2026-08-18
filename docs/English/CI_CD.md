[← Back to docs index](README.md)

# CI/CD and Automation (v6.6.0+)

The repository utilizes GitHub Actions (`.github/workflows/`) for code validation, health monitoring, locale verification, and automated deployment to an Oracle VPS using the modern Docker Compose architecture.

## Workflows

### 1. `ci.yml` (Code Quality)
**Triggers:** Push to `main`/`dev`, Pull Requests to `main`.
- Checks out the repository.
- Sets up Python 3.12 & Node.js 20.
- Installs `ruff` for Python linting and `eslint` for the React Dashboard.
- Runs `ruff check app/` to enforce Python linting standards.
- Runs `npm run lint` inside `dashboard/frontend` to verify React code formatting.

### 2. `locales.yml` (Translation Validation)
**Triggers:** Push or Pull Request modifying files inside `locales/**`.
- Validates that all `.json` files are syntactically valid JSON.
- Compares `en.json` (the reference file) against all other language files (`uk.json`, etc.).
- Fails the build if any translation keys are missing in target languages.

### 3. `security.yml` (Vulnerability Scanning)
**Triggers:** Push to `main`, Scheduled (Mondays at 09:00 UTC).
- Uses `pip-audit` to scan `requirements.txt` and `dashboard/requirements.txt` against known CVEs.
- Fails the build if critical dependencies are compromised.

### 4. `health.yml` (Server Monitoring)
**Triggers:** Scheduled (Every 30 minutes).
- Connects to the production server via SSH using `appleboy/ssh-action`.
- Queries the `docker` daemon to verify `finances-bot` and `finances-dashboard` containers are running (`docker compose ps`).
- Prints diagnostic information (Memory usage, CPU load, Disk space) and reads the last 30 lines of container logs (`docker compose logs --tail=30 bot`) if the service crashed.

### 5. `deploy.yml` (Production Deployment)
**Triggers:** Push to `main`.
- **Concurrency**: Guaranteed to only run one deployment at a time.
- **Steps**:
  1. Pulls the latest `main` branch code on the target server.
  2. Creates or updates the `.env` file using environment variables populated from GitHub Secrets (`BOT_TOKEN`, `MONGO_URI`, `BOT_ADMIN_IDS`, etc.).
  3. Rebuilds the Docker images using `docker compose build --no-cache`.
  4. Restarts the services in the background using `docker compose up -d`.
  5. Performs a rolling health check (wait 20s). If the bot or dashboard crashes on boot (`docker inspect --format='{{.State.Status}}' finances-bot`), performs an automatic `git reset --hard` to the previously working commit and restarts the containers, marking deployment as failed.

### 6. `stale.yml`
**Triggers:** Scheduled (Mondays at 09:00 UTC).
- Automatically manages GitHub Issues and Pull Requests via `actions/stale`. Marks issues inactive for 30 days as `stale`, and closes them after 14 days. Allows exemptions for specific labels like `pinned` or `security`.

---

*Last updated: 2026-08-16*
