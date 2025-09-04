import os

env_content = """BOT_TOKEN=test_token
DATABASE_URL=postgresql+asyncpg://postgres:password@localhost:5432/bci_bot_test
DEEPSEEK_API_KEY=test_key
DOWNLOADS_DIR=./downloads
"""

with open('.env', 'w', encoding='utf-8') as f:
    f.write(env_content)

print("Файл .env создан успешно!")
