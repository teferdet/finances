[← Back to docs index](README.md)

# CI/CD and Automation

The repository utilizes GitHub Actions (`.github/workflows/`) for code validation, health monitoring, locale verification, and automated deployment to an Oracle VPS.

## Workflows

### 1. `ci.yml` (Code Quality)
**Triggers:** Push to `main`/`dev`, Pull Requests to `main`.
- Checks out the repository.
- Sets up Python 3.12.
- Installs `ruff`.
- Runs `ruff check app/` to enforce linting standards and `ruff format app/ --check` to verify code formatting.

### 2. `locales.yml` (Translation Validation)
**Triggers:** Push or Pull Request modifying files inside `locales/**`.
- Validates that all `.json` files are syntactically valid JSON.
- Uses a custom Python script to deeply traverse `en.json` (the reference file) and compares it against all other language files (`uk.json`, `fr.json`, etc.).
- Fails the build if any translation keys are missing in target languages.

### 3. `security.yml` (Vulnerability Scanning)
**Triggers:** Push to `main`, Scheduled (Mondays at 09:00 UTC).
- Uses `pip-audit` to scan `requirements.txt` against known CVEs (Common Vulnerabilities and Exposures) and fails the build if critical dependencies are compromised.

### 4. `health.yml` (Server Monitoring)
**Triggers:** Scheduled (Every 30 minutes).
- Connects to the production server via SSH using `appleboy/ssh-action`.
- Queries the `systemd` daemon to verify `finances-bot.service` is active.
- Prints diagnostic information (Memory usage, CPU load, Disk space) and reads the last 30 lines of the journal if the service crashed.

### 5. `deploy.yml` (Production Deployment)
**Triggers:** Push to `main`.
- **Concurrency**: Guaranteed to only run one deployment at a time.
- **Steps**:
  1. Clones or pulls the latest `main` branch code on the target server.
  2. Dynamically generates `config/settings.json` using environment variables populated from GitHub Secrets (`BOT_TOKEN`, `MONGO_URI`, etc.).
  3. Updates the `venv` and installs dependency changes from `requirements.txt`.
  4. Copies `deploy/finances-bot.service` into `/etc/systemd/system/` and restarts the daemon.
  5. Performs a rolling health check (wait 20s). If the bot crashes on boot, performs an automatic `git reset --hard` to the previously working commit and restarts the service, marking deployment as failed.

### 6. `stale.yml`
**Triggers:** Scheduled (Mondays at 09:00 UTC).
- Automatically manages GitHub Issues and Pull Requests via `actions/stale` (v10). Marks issues inactive for 30 days as `stale`, and closes them after 14 days. Marks PRs stale after 60 days. Allows exemptions for specific labels like `pinned` or `security`.

---

*Last updated: 2026-07-22*

