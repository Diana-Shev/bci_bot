#!/usr/bin/env python3
# -*- coding: utf-8 -*-

print("🚀 Запуск теста моделей...")

try:
    # Тест импорта
    from app.models import User, Metric, ProductivityPeriod, DailyRecommendation, ImprovementSuggestion
    print("✅ Импорт моделей успешен")
    
    # Тест создания User
    user = User(
        telegram_id=12345,
        username="test_user",
        name="Test User",
        email="test@example.com"
    )
    print("✅ Модель User создана успешно")
    
    # Тест создания Metric
    from datetime import datetime
    metric = Metric(
        user_id=1,
        timestamp=datetime.utcnow(),
        cognitive_score=85,
        focus=70,
        chill=30,
        stress=20,
        self_control=60,
        anger=5,
        relaxation_index=0.5,
        concentration_index=0.7,
        fatique_score=0.2,
        reverse_fatique=0.1,
        alpha_gravity=0.3,
        heart_rate=72
    )
    print("✅ Модель Metric создана успешно")
    
    # Тест создания ProductivityPeriod
    from datetime import time
    period = ProductivityPeriod(
        user_id=1,
        start_time=time(9, 0),
        end_time=time(12, 0),
        productivity_score=90.0,
        recommended_activity="coding"
    )
    print("✅ Модель ProductivityPeriod создана успешно")
    
    # Тест создания DailyRecommendation
    from datetime import date
    rec = DailyRecommendation(
        user_id=1,
        date=date.today(),
        recommendation_text="Test recommendation"
    )
    print("✅ Модель DailyRecommendation создана успешно")
    
    # Тест создания ImprovementSuggestion
    suggestion = ImprovementSuggestion(
        user_id=1,
        suggestion_text="Test suggestion"
    )
    print("✅ Модель ImprovementSuggestion создана успешно")
    
    print("\n🎉 Все тесты моделей прошли успешно!")
    
except Exception as e:
    print(f"❌ Ошибка: {e}")
    import traceback
    traceback.print_exc()

