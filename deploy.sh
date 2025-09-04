#!/bin/bash

# Скрипт автоматического развертывания BCI Bot на Ubuntu 22.04
# Запускай от имени root или с sudo

set -e  # Останавливаемся при ошибке

echo "🚀 Начинаю развертывание BCI Bot..."

# Проверяем, что мы root
if [ "$EUID" -ne 0 ]; then
    echo "❌ Запустите скрипт с sudo"
    exit 1
fi

# Обновляем систему
echo "📦 Обновляю систему..."
apt update && apt upgrade -y

# Устанавливаем необходимые пакеты
echo "🔧 Устанавливаю зависимости..."
apt install -y python3 python3-pip python3-venv postgresql postgresql-contrib git curl

# Создаем пользователя для бота
echo "👤 Создаю пользователя bcibot..."
if id "bcibot" &>/dev/null; then
    echo "Пользователь bcibot уже существует"
else
    adduser --disabled-password --gecos "" bcibot
    usermod -aG sudo bcibot
fi

# Переключаемся на пользователя bcibot
echo "🔄 Переключаюсь на пользователя bcibot..."
su - bcibot << 'EOF'

# Клонируем проект (замените на ваш репозиторий)
echo "📥 Клонирую проект..."
cd ~
if [ -d "bci_bot" ]; then
    echo "Проект уже существует, обновляю..."
    cd bci_bot
    git pull
else
    git clone <ВАШ_РЕПОЗИТОРИЙ> bci_bot
    cd bci_bot
fi

# Создаем виртуальное окружение
echo "🐍 Создаю виртуальное окружение..."
python3 -m venv .venv
source .venv/bin/activate

# Устанавливаем зависимости
echo "📚 Устанавливаю Python зависимости..."
pip install --upgrade pip
pip install -r requirements.txt

# Создаем папку для загрузок
mkdir -p downloads

echo "✅ Установка завершена!"
echo "📝 Теперь создайте .env файл и настройте базу данных"

EOF

# Настраиваем PostgreSQL
echo "🗄️ Настраиваю PostgreSQL..."
sudo -u postgres psql -c "CREATE DATABASE bci_bot;" 2>/dev/null || echo "База данных уже существует"
sudo -u postgres psql -c "CREATE USER bcibot_user WITH PASSWORD 'bcibot_password123';" 2>/dev/null || echo "Пользователь БД уже существует"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE bci_bot TO bcibot_user;"

# Создаем systemd сервис
echo "🔧 Создаю systemd сервис..."
cat > /etc/systemd/system/bcibot.service << 'EOF'
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
EOF

# Перезагружаем systemd и активируем сервис
echo "🔄 Активирую сервис..."
systemctl daemon-reload
systemctl enable bcibot

# Создаем .env файл
echo "📝 Создаю .env файл..."
cat > /home/bcibot/bci_bot/.env << 'EOF'
BOT_TOKEN=your_bot_token_here
DATABASE_URL=postgresql+asyncpg://bcibot_user:bcibot_password123@localhost:5432/bci_bot
DEEPSEEK_API_KEY=your_api_key_here
DOWNLOADS_DIR=./downloads
EOF

# Устанавливаем права
chown bcibot:bcibot /home/bcibot/bci_bot/.env
chmod 600 /home/bcibot/bci_bot/.env

echo ""
echo "🎉 Развертывание завершено!"
echo ""
echo "📋 Что нужно сделать дальше:"
echo "1. Отредактируйте /home/bcibot/bci_bot/.env файл:"
echo "   - Укажите ваш BOT_TOKEN"
echo "   - Укажите ваш DEEPSEEK_API_KEY (опционально)"
echo ""
echo "2. Создайте таблицы в базе данных:"
echo "   sudo -u bcibot bash -c 'cd /home/bcibot/bci_bot && source .venv/bin/activate && python create_tables.py'"
echo ""
echo "3. Запустите бота:"
echo "   sudo systemctl start bcibot"
echo ""
echo "4. Проверьте статус:"
echo "   sudo systemctl status bcibot"
echo ""
echo "5. Посмотрите логи:"
echo "   sudo journalctl -u bcibot -f"
echo ""
echo "📚 Подробные инструкции в README.md"
