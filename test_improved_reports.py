#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Тестовый скрипт для проверки улучшенных отчетов GitSearch
"""

import os
import sys
from datetime import datetime

# Добавляем корневую папку проекта в путь
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src import reports

def test_improved_business_report():
    """Тестирует улучшенную генерацию бизнес-отчета"""
    print("🚀 Тестирование улучшенного бизнес-отчета...")
    
    try:
        # Генерируем улучшенный бизнес-отчет за весь период
        start_date = "2010-12-30"
        end_date = "2025-07-01"
        
        print(f"📅 Генерация улучшенного бизнес-отчета: {start_date} - {end_date}")
        
        report_result = reports.generate_report(
            start_date=start_date,
            end_date=end_date,
            report_type="business"
        )
        
        print("✅ Улучшенный бизнес-отчет успешно сгенерирован!")
        print(f"📁 Файл: {report_result.get('path', 'не указан')}")
        
        # Выводим статистику
        print(f"📊 Всего утечек: {report_result.get('total_leaks', 0)}")
        print(f"🏢 Компаний: {report_result.get('unique_companies', 0)}")
        print(f"⚡ Средняя серьезность: {report_result.get('average_severity', 0):.2f}")
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка генерации улучшенного бизнес-отчета: {e}")
        return False

def test_improved_technical_report():
    """Тестирует улучшенную генерацию технического отчета"""
    print("\n🔧 Тестирование улучшенного технического отчета...")
    
    try:
        # Генерируем улучшенный технический отчет за последний месяц
        start_date = "2025-06-01"
        end_date = "2025-07-01"
        
        print(f"📅 Генерация улучшенного технического отчета: {start_date} - {end_date}")
        
        report_result = reports.generate_report(
            start_date=start_date,
            end_date=end_date,
            report_type="technical"
        )
        
        print("✅ Улучшенный технический отчет успешно сгенерирован!")
        print(f"📁 Файл: {report_result.get('path', 'не указан')}")
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка генерации улучшенного технического отчета: {e}")
        return False

def main():
    """Основная функция тестирования"""
    print("🎯 Тестирование улучшенных отчетов GitSearch")
    print("=" * 50)
    
    success_count = 0
    
    # Тестируем улучшенный бизнес-отчет
    if test_improved_business_report():
        success_count += 1
    
    # Тестируем улучшенный технический отчет
    if test_improved_technical_report():
        success_count += 1
    
    print("\n" + "=" * 50)
    print(f"✅ Успешно: {success_count}/2 тестов")
    print("🎉 Тестирование улучшенных отчетов завершено!")

if __name__ == "__main__":
    main()
