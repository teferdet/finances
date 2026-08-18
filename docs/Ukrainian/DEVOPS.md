[← Повернутися до змісту](README.md)

# DevOps — Операційний посібник сервера

Повний операційний довідник для управління ботом **finances** на production-сервері.
Цей посібник охоплює як **Modern (Docker)** архітектуру для версій 6.6.0+, так і **Legacy (systemd)** архітектуру для старших версій.

---
## 🐋 Частина 1: Сучасні деплої (v6.6.0+ з Docker Compose)

Застосунок працює як набір Docker-контейнерів, визначених у `docker-compose.yml`.

### 1.1 Управління сервісами

| Команда | Дія |
|---|---|
| `docker compose up -d` | Запуск або перезапуск бота та дашборда |
| `docker compose stop` | Грацільна зупинка сервісів |
| `docker compose restart bot` | Перезапуск лише контейнера бота |
| `docker compose ps` | Перегляд поточного статусу всіх контейнерів |
| `docker compose down` | Зупинка та видалення контейнерів |
| `docker compose build` | Перебудова образів з вихідного коду |

**Перевірка здоров'я контейнера:**
```bash
docker inspect --format='{{json .State.Health}}' finances-bot | jq
```

### 1.2 Логи в реальному часі

```bash
# Слідкувати за логами всіх сервісів
docker compose logs -f

# Тільки бот
docker compose logs -f bot

# Тільки дашборд
docker compose logs -f dashboard

# Останні 100 рядків з подальшим слідкуванням
docker compose logs --tail=100 -f bot
```

### 1.3 Моніторинг ресурсів

```bash
# Живий CPU, RAM та мережа (оновлення щосекунди)
docker stats

# Одноразовий знімок
docker stats --no-stream
```

### 1.4 Ручний деплой

```bash
APP_DIR="/home/ubuntu/finances"
cd "$APP_DIR"

git fetch origin main
git reset --hard origin/main

docker compose build --no-cache
docker compose up -d
docker compose ps
```

### 1.5 Корисні однорядкові команди

```bash
# Повне очищення Docker (НЕБЕЗПЕЧНО: видаляє всі зупинені контейнери, мережі, образи)
docker system prune -a --volumes

# Вхід у контейнер бота
docker exec -it finances-bot /bin/bash

# Перевірка внутрішнього settings.json
docker exec -it finances-bot cat /app/config/settings.json
```

---

## ⚙️ Частина 2: Legacy-деплої (v6.5.0 та старші з systemd)

### 2.1 Управління сервісами (systemd)

Бот працює як systemd-сервіс `finances-bot.service`.

| Команда | Дія |
|---|---|
| `sudo systemctl start finances-bot` | Запуск бота |
| `sudo systemctl stop finances-bot` | Зупинка бота |
| `sudo systemctl restart finances-bot` | Перезапуск бота |
| `sudo systemctl status finances-bot` | Перегляд статусу |
| `sudo systemctl enable finances-bot` | Увімкнення автозапуску |
| `sudo systemctl disable finances-bot` | Вимкнення автозапуску |

### 2.2 Логи в реальному часі

```bash
# systemd журнал
sudo journalctl -u finances-bot.service -f

# З мітками часу
sudo journalctl -u finances-bot.service -f --output=short-iso

# Лише помилки
sudo journalctl -u finances-bot.service -f -p err

# Останні N рядків
sudo journalctl -u finances-bot.service -n 100 -f
```

### Фільтрація за часом

```bash
# Логи за сьогодні
sudo journalctl -u finances-bot.service --since today

# Логи за останню годину
sudo journalctl -u finances-bot.service --since "1 hour ago"

# Логи в конкретному часовому діапазоні
sudo journalctl -u finances-bot.service \
  --since "2026-07-20 03:00:00" \
  --until "2026-07-20 04:00:00"
```

### 2.3 Файлові логи

Бот підтримує власні лог-файли через `RotatingFileHandler` у `/home/ubuntu/finances/logs/`.

| Файл | Зміст | Ротація |
|---|---|---|
| `logs/bot.log` | Усі повідомлення (DEBUG і вище) | 10 МБ × 5 файлів |
| `logs/errors.log` | Лише ERROR та CRITICAL | 5 МБ × 3 файли |
| `logs/d_admin.log` | Дії динамічних адмінів | 5 МБ × 3 файли |

```bash
# Слідкувати за основним логом
tail -f /home/ubuntu/finances/logs/bot.log

# Тільки помилки
tail -f /home/ubuntu/finances/logs/errors.log
```

### 2.4 Моніторинг ресурсів

```bash
# RAM та Swap
free -h

# Дискове місце
df -h
du -sh /home/ubuntu/finances/

# Мережа
ss -tlnp
```

### 2.5 Бекапи

Бот автоматично бекапить MongoDB **щодня о 03:00 UTC** у `/home/ubuntu/finances/backups/`.
Зберігаються лише **7 останніх** бекапів. Формат: `backup_YYYYMMDD_HHMMSS.gz` (JSON + gzip).

```bash
# Список бекапів
ls -lh /home/ubuntu/finances/backups/

# Останній бекап
ls -t /home/ubuntu/finances/backups/backup_*.gz | head -1

# Загальний розмір бекапів
du -sh /home/ubuntu/finances/backups/
```

### Тригер ручного бекапу

```bash
cd /home/ubuntu/finances
source venv/bin/activate

python -c "
import asyncio
from app.config import get_settings
from app.services.backup import daily_backup
settings = get_settings()
asyncio.run(daily_backup(settings.database.mongo_uri))
"
```

### Відновлення з бекапу

> [!WARNING]
> Відновлення перезаписує існуючі дані в MongoDB. Продовжуйте лише якщо впевнені.

```bash
BACKUP=$(ls -t /home/ubuntu/finances/backups/backup_*.gz | head -1)
echo "Відновлення з: $BACKUP"
zcat "$BACKUP" > /tmp/restore.json

cd /home/ubuntu/finances
source venv/bin/activate
python3 -c "
import asyncio, json
from motor.motor_asyncio import AsyncIOMotorClient
from app.config import get_settings

async def restore(path):
    settings = get_settings()
    with open(path) as f:
        data = json.load(f)
    client = AsyncIOMotorClient(settings.database.mongo_uri)
    db = client[settings.database.mongo_database]
    for coll, docs in data.items():
        if coll.startswith('_') or not docs:
            continue
        await db[coll].delete_many({})
        await db[coll].insert_many(docs)
        print(f'  ✅ Відновлено {len(docs):>5} документів → {coll}')
    client.close()
    print('Готово.')

asyncio.run(restore('/tmp/restore.json'))
"
```

### 2.6 Ручний деплой

> [!NOTE]
> За звичайних обставин деплої повністю автоматизовані через GitHub Actions. Ручний деплой слід використовувати лише в екстрених випадках.

```bash
APP_DIR="/home/ubuntu/finances"
VENV_DIR="$APP_DIR/venv"
cd "$APP_DIR"

sudo systemctl stop finances-bot
git fetch origin main
git reset --hard origin/main

"$VENV_DIR/bin/pip" install -r requirements.txt \
  --upgrade --upgrade-strategy only-if-needed

sudo systemctl start finances-bot
sleep 3
sudo systemctl status finances-bot --no-pager
```

### 2.7 Відкат та відновлення

```bash
APP_DIR="/home/ubuntu/finances"
cd "$APP_DIR"

# Перегляд останніх комітів
git log --oneline -10

# Відкат до конкретного коміту
COMMIT="abc1234"
sudo systemctl stop finances-bot
git reset --hard "$COMMIT"

"$APP_DIR/venv/bin/pip" install -r requirements.txt \
  --upgrade --upgrade-strategy only-if-needed

sudo systemctl start finances-bot
echo "⏪ Відкат до: $(git rev-parse --short HEAD)"
```

### 2.8 Корисні однорядкові команди

```bash
# Чи працює бот?
sudo systemctl is-active finances-bot && echo "✅ Працює" || echo "❌ Зупинено"

# Коли бот був перезапущений?
sudo systemctl show finances-bot --property=ActiveEnterTimestamp

# Поточне використання RAM (МБ)
sudo systemctl show finances-bot --property=MemoryCurrent \
  | awk -F= '{printf "RAM: %.1f МБ\n", $2/1024/1024}'

# Активний коміт на сервері
cd /home/ubuntu/finances && git log -1 --pretty=format:'%h — %s (%cr)'
```

### 2.9 Структура файлів на сервері

```
/home/ubuntu/finances/
├── app/                        # Вихідний код бота
├── config/
│   ├── settings.json           # Runtime-конфіг (генерується GitHub Actions)
│   ├── data.json               # Статичні дані валют, крипто та компаній
│   └── currencies_data.json    # Метадані валют (емодзі, символи)
├── logs/
│   ├── bot.log                 # Основний лог — всі рівні (10 МБ × 5 ротацій)
│   ├── errors.log              # Лише помилки (5 МБ × 3 ротації)
│   └── d_admin.log             # Аудит-лог дій динамічних адмінів
├── backups/
│   └── backup_YYYYMMDD_HHMMSS.gz  # Щоденні бекапи MongoDB (7 зберігаються)
├── venv/                       # Python virtual environment
├── deploy/
│   └── finances-bot.service    # systemd unit-файл
└── requirements.txt            # Python-залежності
```

---

*Останнє оновлення: 2026-08-16*
