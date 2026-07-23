# ❓ FAQ & Troubleshooting

**TL;DR:** Common solutions for issues encountered when running or administering the Finances bot.

### 1. Bot won't start: Package missing errors
**Cause**: The custom dependency check in `__main__.py` detected missing libraries.
**Solution**: Ensure your virtual environment is activated and run `pip install -r requirements.txt`. If `curl_cffi` fails to build, check if you have the necessary C++ build tools or try installing binary wheels.

### 2. Parser is not updating exchange rates
**Cause**: The background parser might be paused in the database, or the `update_interval_sec` is too long.
**Solution**: Open the bot, run `/admin`, go to **System Configuration**, and ensure the parser state is set to `🟢 Parser: Enabled`.

### 3. Log download fails with "Authorization Failed"
**Cause**: Downloading raw `.log` files requires strict authorization. Your numeric Telegram ID must be explicitly configured.
**Solution**: Verify your Telegram User ID is in the `bot.admin_ids` list inside `config/settings.json`. It must be an integer, not a string.

### 4. UI displays raw keys (e.g. `menu.welcome`) instead of text
**Cause**: The `i18n` engine couldn't find the key in the selected language file or the default fallback file.
**Solution**: Check your `locales/` directory. If you are developing a new feature, make sure to add the translation keys to `en.json` (and other languages).

### 5. Bot crashes with `ServerSelectionTimeoutError`
**Cause**: The `motor` client cannot connect to MongoDB.
**Solution**: Check if MongoDB is running locally (`systemctl status mongod`). If using Atlas, verify that your VPS/Home IP address is whitelisted in the MongoDB Atlas Network Access settings.
