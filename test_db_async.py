import asyncio
from sqlalchemy import select
from app.database import AsyncSessionLocal
from app.models import User

async def main():
    async with AsyncSessionLocal() as session:
        res = await session.execute(select(User).limit(10))
        users = res.scalars().all()
        print("Найдено пользователей:", len(users))
        for u in users:
            print(f"ID: {u.id}, Telegram ID: {u.telegram_id}, Name: {u.name}, Username: {u.username}")

if __name__ == "__main__":
    asyncio.run(main())
