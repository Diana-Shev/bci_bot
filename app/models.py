from datetime import datetime, date, time, timezone
from typing import List

from sqlalchemy import (
    Integer, String, Text, Date, Time, DateTime, Numeric,
    BigInteger, ForeignKey
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


# 🔹 Базовый класс для моделей
class Base(DeclarativeBase):
    pass


# 🔹 Пользователи
class User(Base):
    __tablename__ = "users"

    user_id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False)
    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=True)
    name: Mapped[str] = mapped_column(String(100), nullable=True)
    email: Mapped[str] = mapped_column(String(100), unique=True, nullable=True)
    iaf: Mapped[float] = mapped_column(Numeric(4, 2), nullable=True)  # Individual Alpha Frequency
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now())

    # связи
    metrics: Mapped[List["Metric"]] = relationship(back_populates="user")
    recommendations: Mapped[List["DailyRecommendation"]] = relationship(back_populates="user")


# 🔹 Метрики (соответствуют NUMERIC_MAP в utils.py и обращениям в боте)
class Metric(Base):
    __tablename__ = "metrics"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.user_id"))

    # временная метка
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now())

    # числовые поля
    cognitive_score: Mapped[int] = mapped_column(Integer, nullable=True)
    focus: Mapped[int] = mapped_column(Integer, nullable=True)
    chill: Mapped[int] = mapped_column(Integer, nullable=True)
    stress: Mapped[int] = mapped_column(Integer, nullable=True)
    self_control: Mapped[int] = mapped_column(Integer, nullable=True)
    anger: Mapped[int] = mapped_column(Integer, nullable=True)

    relaxation_index: Mapped[float] = mapped_column(Numeric, nullable=True)
    concentration_index: Mapped[float] = mapped_column(Numeric, nullable=True)
    fatique_score: Mapped[float] = mapped_column(Numeric, nullable=True)
    reverse_fatique: Mapped[float] = mapped_column(Numeric, nullable=True)
    alpha_gravity: Mapped[float] = mapped_column(Numeric, nullable=True)

    heart_rate: Mapped[int] = mapped_column(Integer, nullable=True)

    # связь с пользователем
    user: Mapped["User"] = relationship(back_populates="metrics")


# 🔹 Периоды продуктивности
class ProductivityPeriod(Base):
    __tablename__ = "productivity_periods"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.user_id"))
    start_time: Mapped[time] = mapped_column(Time)
    end_time: Mapped[time] = mapped_column(Time)
    productivity_score: Mapped[float] = mapped_column(Numeric)
    recommended_activity: Mapped[str] = mapped_column(String(200), nullable=True)


# 🔹 Рекомендации на день
class DailyRecommendation(Base):
    __tablename__ = "daily_recommendations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    date: Mapped[date] = mapped_column(Date, nullable=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.user_id"))
    recommendation_text: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now())

    # связь с пользователем
    user: Mapped["User"] = relationship(back_populates="recommendations")


# 🔹 Предложения по улучшению
class ImprovementSuggestion(Base):
    __tablename__ = "improvement_suggestions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.user_id"))
    suggestion_text: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now())
