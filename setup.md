# Setup & Administration Guide (v6.6.0)

Welcome to the **Finances Bot** deployment guide. The project now uses a robust **Docker Compose** architecture containing both the Telegram Bot and a web-based Admin Dashboard.

## 📌 Prerequisites
- **Docker** and **Docker Compose** installed on your server/machine.
- **Telegram Bot Token** (from [@BotFather](https://t.me/BotFather)).
- **MongoDB instance** (local or MongoDB Atlas).

---

## 🚀 Quick Start (Docker Deployment)

The recommended and easiest way to deploy the new version is via Docker. This ensures all memory limits, health checks, and dependencies are perfectly isolated.

1. **Clone the repository:**
   ```bash
   git clone https://github.com/teferdet/finances.git
   cd finances
   ```

2. **Configure Environment Variables:**
   The new version uses a `.env` file instead of manually editing `settings.json`.
   ```bash
   cp .env.example .env
   ```
   Open `.env` and fill in your keys. The most critical variables are:
   - `BOT_TOKEN=your_bot_token_here`
   - `BOT_ADMIN_IDS=[123456789]` *(Must be an array of integers)*
   - `MONGO_URI=mongodb+srv://...` *(If you use external Mongo, otherwise leave it to use internal)*

3. **Start the services:**
   Build and run the bot and dashboard in the background:
   ```bash
   docker compose up -d --build
   ```

4. **Verify it's running:**
   ```bash
   docker compose ps
   ```

---

## ⚙️ How Configuration Works Now

In older versions, you had to manually edit `config/settings.json`. 
**Now, configuration is automated!**

When you run `docker compose up`, a script (`docker/entrypoint-bot.sh`) automatically reads your `.env` file and dynamically generates the `config/settings.json` file inside the container before starting the bot. 

### Key Environment Variables
| Variable | Description |
|-----------|-------------|
| `BOT_TOKEN` | Your Telegram Bot Token. |
| `BOT_ADMIN_IDS` | List of Telegram User IDs with admin access (e.g. `[123456789]`). |
| `MONGO_URI` | MongoDB connection string. Defaults to internal `mongodb://mongo:27017/finances`. |
| `REDIS_URL` | Optional Redis URL for caching. |

---

## 🖥 Admin Dashboard (New!)

Version 6.0+ introduces a standalone **React + FastAPI Web Dashboard**.

- **URL:** `http://localhost:8090` (by default).
- **Authentication:** The dashboard is secured via a Telegram OTP (One-Time Password).
  1. Open the dashboard in your browser.
  2. Enter your Telegram User ID (it must be listed in `BOT_ADMIN_IDS`).
  3. The bot will send you a 6-digit code in Telegram.
  4. Enter the code to log in.

### Dashboard Features:
- **Overview:** Real-time DAU, requests, and performance metrics.
- **DataGrids:** View Users, Error Logs, and Groups with advanced sorting and filtering.
- **Config Management:** Toggle parsers and features directly from the web interface.

---

## 🛠 Local Development (Without Docker)

If you want to run the project locally for development without Docker:

1. **Set up Python Environment:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

2. **Generate Settings:**
   Manually create `config/settings.json` based on your needs (you can look at `docker/entrypoint-bot.sh` for the schema).

3. **Start the Bot:**
   ```bash
   python -m app
   ```

4. **Start the Dashboard:**
   ```bash
   # Backend
   cd dashboard
   uvicorn api.main:app --host 0.0.0.0 --port 8090
   
   # Frontend
   cd frontend
   npm install
   npm run dev
   ```

---

## ❓ Troubleshooting

| Issue | Possible Cause | Solution |
|-------|---------------|----------|
| **Bot keeps restarting** | Invalid `.env` or Mongo URL | Check logs using `docker compose logs -f bot`. Ensure `BOT_TOKEN` is correct. |
| **Cannot log into Dashboard** | ID not in `BOT_ADMIN_IDS` | Ensure your numeric Telegram ID is in the `.env` file array. Restart the bot container to apply. |
| **High Memory Usage** | Normal Python behavior | The Docker containers use `libjemalloc2` and strict limits (400MB for bot). Do not worry if the image size is ~600MB; runtime RAM is capped. |
