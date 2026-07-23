# 🚀 Deployment

**TL;DR:** The project employs GitHub Actions for CI/CD, automatically deploying to an Oracle VPS when pushing to the `main` branch.

## CI/CD Workflows (`.github/workflows/deploy.yml`)
The main deployment workflow triggers on pushes to `main`. It uses `appleboy/ssh-action` to connect to the server and execute commands.

### The Pipeline Steps:
1. **Pull Latest Code**: Fetches the newest commit from the repository via GitHub PAT.
2. **Generate Settings**: Dynamically generates `config/settings.json` injecting GitHub Secrets as values.
3. **Install Dependencies**: Creates/updates the Python virtual environment (`venv`). It intelligently hashes `requirements.txt` to skip reinstalling if nothing changed.
4. **Configure Systemd**: Re-copies `deploy/finances-bot.service` and reloads the daemon.
5. **Restart Bot**: Restarts the systemd service.
6. **Health Check**: Monitors the systemd status for 20 seconds. If the bot fails to start, it rolls back to the previous commit and restores older dependencies.

## Required Environment Variables / Secrets
To configure GitHub Actions, populate the following Repository Secrets:
- `SERVER_HOST`, `SERVER_USERNAME`, `SERVER_PORT`, `SSH_PRIVATE_KEY` (VPS Connection)
- `GH_PAT` (GitHub Personal Access Token for cloning)
- `BOT_TOKEN`
- `MONGO_URI`
- `CRYPTO_API_KEY`, `STOCKS_API_KEY`
- `FERNET_KEY`
- `BOT_ADMIN_IDS` (JSON Array format, e.g., `[12345]`)

Repository Variables (Non-secret):
- `URL_COMMUNICATION`, `URL_INVITE`, `URL_BUYMEACOFFEE`, `URL_MINI_APP`, etc.

## Troubleshooting Deployments
- **"Import FAILED" during CI**: The `requirements.txt` installation might have failed. The CI checks imports for `aiogram`, `motor`, `curl_cffi`, etc. Connect via SSH and run `pip install -r requirements.txt` manually to debug package compilation errors.
- **Bot fails Health Check**: Check the raw logs using `sudo journalctl -u finances-bot.service -n 50`. Often caused by an invalid `MONGO_URI` or `BOT_TOKEN`.
