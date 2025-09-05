# BCI Bot - Telegram бот для анализа BCI метрик

Этот бот помогает пользователям анализировать данные с BCI-модуля и получать рекомендации по режиму дня.

## 🚀 Как работает бот

1. **Старт** - пользователь нажимает /start
2. **Приветствие** - бот показывает экран с кнопкой "Введи свои IAF"
3. **Ввод IAF** - пользователь вводит индивидуальную альфа-частоту
4. **Загрузка файла** - пользователь загружает CSV/XLSX с метриками
5. **Валидация файла** - бот проверяет корректность данных:
   - ❌ **Ошибка загрузки** → кнопка "Start (переход на начало)"
   - ⚠️ **Неполные данные** → кнопка "Прикрепить файл"
   - ✅ **Успешно** → продолжение анализа
6. **Анализ** - бот анализирует данные через LLM (DeepSeek или мок)
7. **Результаты** - бот показывает периоды продуктивности и кнопки
8. **Рекомендации** - бот дает советы по режиму дня
9. **Улучшения** - бот предлагает улучшения режима

## 📋 Требования

- Python 3.8+
- PostgreSQL база данных
- Telegram Bot Token
- DeepSeek API ключ (опционально)

## 🛠️ Установка на сервере Ubuntu 22.04

### 1. Обновляем систему
```bash
sudo apt update && sudo apt upgrade -y
```

### 2. Устанавливаем Python и зависимости
```bash
sudo apt install python3 python3-pip python3-venv postgresql postgresql-contrib -y
```

### 3. Создаем пользователя для бота
```bash
sudo adduser bcibot
sudo usermod -aG sudo bcibot
sudo su - bcibot
```

### 4. Клонируем проект
```bash
cd ~
git clone <ваш-репозиторий> bci_bot
cd bci_bot
```

### 5. Создаем виртуальное окружение
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

### 6. Настраиваем базу данных
```bash
sudo -u postgres psql
```

В PostgreSQL консоли:
```sql
CREATE DATABASE bci_bot;
CREATE USER bcibot_user WITH PASSWORD 'ваш_пароль';
GRANT ALL PRIVILEGES ON DATABASE bci_bot TO bcibot_user;
\q
```

### 7. Создаем .env файл
```bash
cp env_example.txt .env
nano .env
```

Заполните файл:
```env
BOT_TOKEN=ваш_токен_бота
DATABASE_URL=postgresql+asyncpg://bcibot_user:ваш_пароль@localhost:5432/bci_bot
DEEPSEEK_API_KEY=ваш_ключ_api
DOWNLOADS_DIR=./downloads
```

### 8. Создаем таблицы
```bash
python create_tables.py
```

### 9. Тестируем бота
```bash
python run_bot.py
```

## 🔧 Настройка автозапуска (systemd)

### 1. Создаем сервис файл
```bash
sudo nano /etc/systemd/system/bcibot.service
```

Содержимое файла:
```ini
[Unit]
Description=BCI Bot Telegram Service
After=network.target postgresql.service

[Service]
Type=simple
User=bcibot
WorkingDirectory=/home/bcibot/bci_bot
Environment=PATH=/home/bcibot/bci_bot/.venv/bin
ExecStart=/home/bcibot/bci_bot/.venv/bin/python run_bot.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

### 2. Активируем сервис
```bash
sudo systemctl daemon-reload
sudo systemctl enable bcibot
sudo systemctl start bcibot
sudo systemctl status bcibot
```

## 📁 Структура проекта

```
bci_bot/
├── app/                    # Основной код приложения
│   ├── __init__.py
│   ├── bot.py             # Логика Telegram бота
│   ├── config.py          # Конфигурация
│   ├── crud.py            # Операции с базой данных
│   ├── database.py        # Подключение к БД
│   ├── llm_client.py      # Клиент для LLM API
│   ├── models.py          # Модели базы данных
│   └── utils.py           # Утилиты
├── .env                    # Переменные окружения
├── requirements.txt        # Зависимости Python
├── create_tables.py        # Скрипт создания таблиц
├── run_bot.py             # Скрипт запуска бота
└── README.md              # Этот файл
```

## 🧪 Тестирование

### Локальное тестирование
```bash
# Активируем виртуальное окружение
source .venv/bin/activate

# Запускаем тесты
python -m pytest test_*.py

# Запускаем бота
python run_bot.py
```

### Тестирование на сервере
```bash
# Проверяем статус сервиса
sudo systemctl status bcibot

# Смотрим логи
sudo journalctl -u bcibot -f

# Перезапускаем сервис
sudo systemctl restart bcibot
```

## 🔍 Логи и отладка

### Просмотр логов в реальном времени
```bash
sudo journalctl -u bcibot -f
```

### Просмотр последних логов
```bash
sudo journalctl -u bcibot -n 100
```

### Проверка подключения к базе данных
```bash
sudo -u postgres psql -d bci_bot -c "SELECT version();"
```

## 🚨 Устранение неполадок

### Бот не запускается
1. Проверьте токен бота в .env
2. Проверьте подключение к базе данных
3. Посмотрите логи: `sudo journalctl -u bcibot -f`

### Ошибки с базой данных
1. Проверьте, что PostgreSQL запущен: `sudo systemctl status postgresql`
2. Проверьте права доступа пользователя
3. Проверьте строку подключения в .env

### Файлы не загружаются
1. Проверьте права на папку downloads
2. Убедитесь, что формат файла CSV или XLSX
3. Проверьте структуру колонок в файле

## 📞 Поддержка

Если возникли проблемы:
1. Проверьте логи: `sudo journalctl -u bcibot -f`
2. Убедитесь, что все зависимости установлены
3. Проверьте настройки в .env файле
4. Убедитесь, что база данных доступна

## 🔐 Безопасность

- Никогда не коммитьте .env файл в git
- Используйте сложные пароли для базы данных
- Ограничьте доступ к серверу только необходимыми портами
- Регулярно обновляйте систему и зависимости
