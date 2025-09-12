#сохраняет и читает данные из БД
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, date, time, timezone
from typing import List
from .models import User, Metric, ProductivityPeriod, DailyRecommendation, ImprovementSuggestion

# users
async def get_or_create_user(session: AsyncSession, telegram_id: int, name: str | None) -> User:
    res = await session.execute(select(User).where(User.telegram_id == telegram_id))
    user = res.scalars().first()
    if user:
        return user
    user = User(telegram_id=int(telegram_id), name=name, created_at=datetime.now())
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user

async def update_user_iaf(session: AsyncSession, telegram_id: int, iaf: float) -> User:
    res = await session.execute(select(User).where(User.telegram_id == telegram_id))
    user = res.scalars().first()
    if not user:
        raise ValueError("User not found")
    user.iaf = iaf
    await session.commit()
    await session.refresh(user)
    return user



# metrics
async def save_metrics_bulk(session: AsyncSession, user_id: int, rows: List[dict]) -> int:
    objs = []
    for r in rows:
        # r must have keys matching model: timestamp, cognitive_score, ...
        objs.append(Metric(user_id=user_id, **r))
    session.add_all(objs)
    await session.commit()
    return len(objs)

async def get_user_metrics(session: AsyncSession, user_id: int) -> List[Metric]:
    res = await session.execute(select(Metric).where(Metric.user_id == user_id).order_by(Metric.timestamp.asc()))
    return list(res.scalars().all())

# productivity periods
async def save_productivity_periods(session: AsyncSession, user_id: int, periods: List[dict]) -> int:
    objs = []
    for p in periods:
        st_raw = p.get("start_time", "")[:5]
        et_raw = p.get("end_time", "")[:5]
        try:
            st = time.fromisoformat(st_raw)
            et = time.fromisoformat(et_raw)
        except Exception:
            continue
        objs.append(ProductivityPeriod(
            user_id=user_id, 
            start_time=st, 
            end_time=et,
            productivity_score=p.get("productivity_score", 0.0),
            recommended_activity=p.get("recommended_activity")
        ))
    if not objs:
        return 0
    session.add_all(objs)
    await session.commit()
    return len(objs)

async def get_productivity_periods(session: AsyncSession, user_id: int):
    res = await session.execute(select(ProductivityPeriod).where(ProductivityPeriod.user_id == user_id).order_by(ProductivityPeriod.start_time))
    return list(res.scalars().all())

# daily plan
async def save_day_plan(session: AsyncSession, user_id: int, day_plan_text: str):
    rec = DailyRecommendation(user_id=user_id, date=date.today(), recommendation_text=day_plan_text, created_at=datetime.now())
    session.add(rec)
    await session.commit()
    return rec.id

# improvement suggestions
async def save_improvement_suggestions(session: AsyncSession, user_id: int, suggestions: List[str]) -> int:
    if not suggestions:
        return 0
    objs = [ImprovementSuggestion(user_id=user_id, suggestion_text=s, created_at=datetime.now()) for s in suggestions]
    session.add_all(objs)
    await session.commit()
    return len(objs)
