# Example 001: Finam gRPC - Load Si & CNY Futures to Data Catalog

**Tutorial:** Загрузка фьючерсов USD/RUB (Si) и CNY/RUB (CNY) в ParquetDataCatalog

---

## 📚 Описание

Этот пример демонстрирует, как загрузить исторические данные по квартальным фьючерсам с ММВБ через Finam gRPC API и сохранить их в NautilusTrader Data Catalog для последующего использования в backtesting.

**Период:** 2024-2027 (вся доступная история для каждого контракта)
**Таймфрейм:** M1 (1 минута)
**Инструменты:** 27 контрактов (14 Si + 13 CNY)
**Логика загрузки:** Для каждого контракта загружается ВСЯ ДОСТУПНАЯ ИСТОРИЯ до даты экспирации

---

## 🎯 Что вы узнаете

1. **Система нотации фьючерсов ММВБ**
   - Квартальные месяцы: H=март, M=июнь, U=сентябрь, Z=декабрь
   - Годовая цифра: 4=2024, 5=2025
   - Пример: SiH4@RTSX (Si март 2024), SiU5@RTSX (Si сентябрь 2025)

2. **Загрузка больших объемов исторических данных**
   - Automatic chunking (7 дней) для обхода API limits (30 дней max)
   - Асинхронная загрузка через `request_historical_bars()`
   - Progress logging для отслеживания процесса

3. **Работа с ParquetDataCatalog**
   - Сохранение данных с дедупликацией
   - Запросы с фильтрацией по инструменту и времени
   - Верификация целостности данных

---

## 🚀 Быстрый старт

### Предварительные требования

1. **Учетные данные Finam API** в файле `.env`:
   ```bash
   FINAM_SECRET_TOKEN=your_token_here
   FINAM_ACCOUNT_ID=your_account_id_here
   ```

2. **Установленные зависимости:**
   ```bash
   pip install nautilus_trader python-dotenv
   ```

### Запуск tutorial

**Вариант 1: Как Python скрипт**
```bash
python load_si_cny_futures_tutorial.py
```

**Вариант 2: В VSCode как Notebook**
1. Откройте `load_si_cny_futures_tutorial.py` в VSCode
2. VSCode автоматически распознает ячейки `# %%`
3. Запускайте ячейки последовательно через "Run Cell"

**Вариант 3: В Jupyter Notebook**
```bash
# Конвертация в .ipynb (если нужно)
jupytext --to notebook load_si_cny_futures_tutorial.py
jupyter notebook load_si_cny_futures_tutorial.ipynb
```

---

## 📋 Структура tutorial

### Часть 1-2: Setup и конфигурация
- Импорты библиотек
- Загрузка учетных данных из `.env`
- Настройка логирования

### Часть 3: Определение фьючерсных контрактов
- Список всех контрактов Si и CNY за март 2024 - сентябрь 2025
- Определение периодов загрузки для каждого контракта

### Часть 4: Функция загрузки исторических данных
- `load_historical_bars_for_contract()` - асинхронная загрузка
- Automatic chunking для больших периодов
- Конвертация Protobuf → NautilusTrader Bar objects

### Часть 5: Главная функция
- Цикл загрузки всех контрактов
- Дедупликация данных (по timestamp)
- Сохранение в ParquetDataCatalog
- Верификация целостности

### Часть 6-7: Примеры использования
- Запросы данных из каталога
- Фильтрация по инструменту и времени
- Интеграция с backtesting

---

## 📊 Загружаемые контракты

### Si (USD/RUB) - 14 контрактов (2024-2027)
**2024:** `SiH4@RTSX` `SiM4@RTSX` `SiU4@RTSX` `SiZ4@RTSX`
**2025:** `SiH5@RTSX` `SiM5@RTSX` `SiU5@RTSX` `SiZ5@RTSX`
**2026:** `SiH6@RTSX` `SiM6@RTSX` `SiU6@RTSX` `SiZ6@RTSX`
**2027:** `SiH7@RTSX` `SiM7@RTSX`

### CNY (CNY/RUB) - 13 контрактов (2024-2027)
⚠️ **Префикс CR, не CNYRUB** (подтверждено через Finam API)

**2024:** `CRH4@RTSX` `CRM4@RTSX` `CRU4@RTSX` `CRZ4@RTSX`
**2025:** `CRH5@RTSX` `CRM5@RTSX` `CRU5@RTSX` `CRZ5@RTSX`
**2026:** `CRH6@RTSX` `CRM6@RTSX` `CRU6@RTSX` `CRZ6@RTSX`
**2027:** `CRH7@RTSX`

✅ **Символы подтверждены:** Используйте `check_available_symbols.py` для проверки доступных контрактов.

---

## 💾 Результат работы

После успешного выполнения tutorial создается каталог:
```
si_cny_futures_catalog/
└── data/
    └── bar/
        ├── SiH4-RTSX.FINAM/
        ├── SiM4-RTSX.FINAM/
        ├── ...
        ├── CNYRUBH4-RTSX.FINAM/
        └── ...
```

**Статистика (ожидаемая):**
- 27 инструментов (14 Si + 13 CNY контрактов)
- 2024-2027 (вся доступная история для каждого контракта)
- ~1,000,000+ минутных баров (зависит от доступности исторических данных)
- Размер каталога: ~100-200 MB (с compression)
- Контракты 2024 года могут содержать архивные данные, если доступны в Finam API

---

## 🔍 Примеры использования данных

### Пример 1: Запрос всех баров для контракта
```python
from nautilus_trader.persistence.catalog.parquet import ParquetDataCatalog
from nautilus_trader.model.identifiers import InstrumentId, Symbol, Venue

catalog = ParquetDataCatalog("./si_cny_futures_catalog")
instrument_id = InstrumentId(Symbol("SiZ4-RTSX"), Venue("FINAM"))
bars = catalog.bars(instrument_ids=[str(instrument_id)])
print(f"Загружено {len(bars)} баров для SiZ4")
```

### Пример 2: Фильтрация по времени
```python
from datetime import datetime, timedelta, timezone

end = datetime.now(timezone.utc)
start = end - timedelta(days=30)

bars = catalog.bars(
    instrument_ids=[str(instrument_id)],
    start=start.isoformat(),
    end=end.isoformat(),
)
print(f"Последние 30 дней: {len(bars)} баров")
```

### Пример 3: Все Si контракты 2024-2027
```python
si_symbols = ["SiH4-RTSX", "SiM4-RTSX", "SiU4-RTSX", "SiZ4-RTSX",
              "SiH5-RTSX", "SiM5-RTSX", "SiU5-RTSX", "SiZ5-RTSX",
              "SiH6-RTSX", "SiM6-RTSX", "SiU6-RTSX", "SiZ6-RTSX",
              "SiH7-RTSX", "SiM7-RTSX"]
si_ids = [str(InstrumentId(Symbol(s), Venue("FINAM"))) for s in si_symbols]

all_si_bars = catalog.bars(instrument_ids=si_ids)
print(f"Всего Si баров (2024-2027): {len(all_si_bars)}")
```

### Пример 4: Все CNY контракты (префикс CR)
```python
cny_symbols = ["CRH4-RTSX", "CRM4-RTSX", "CRU4-RTSX", "CRZ4-RTSX",
               "CRH5-RTSX", "CRM5-RTSX", "CRU5-RTSX", "CRZ5-RTSX",
               "CRH6-RTSX", "CRM6-RTSX", "CRU6-RTSX", "CRZ6-RTSX", "CRH7-RTSX"]
cny_ids = [str(InstrumentId(Symbol(s), Venue("FINAM"))) for s in cny_symbols]

all_cny_bars = catalog.bars(instrument_ids=cny_ids)
print(f"Всего CNY баров (2024-2027): {len(all_cny_bars)}")
```

---

## ⚙️ Технические детали

### API Limits (Finam gRPC)
- **⚠️ КРИТИЧНО:** M1 timeframe лимит: **~7-9 дней** за запрос (не 30!)
- **Документация vs Реальность:** Документация говорит "30 days", но API возвращает "Invalid date range" для >7-9 дней
- **Daily timeframes (D, W, MN):** без ограничений
- **Solution:** Automatic chunking `chunk_days=7` (НЕ ОПТИМИЗИРУЙТЕ!)

### Дедупликация
- Ключ: `ts_event` (timestamp события на бирже)
- При дублировании: сохраняется бар с максимальным `ts_init` (самый свежий)
- Гарантирует отсутствие дубликатов при повторных загрузках

### Performance
- **Chunking:** ~2-4 секунды на чанк (7 дней M1 данных)
- **⚠️ ВАЖНО:** `chunk_days=7` это **КРИТИЧЕСКИЙ ЛИМИТ** API, не параметр оптимизации!
- **Время загрузки контракта:** ~2-5 минут (зависит от истории)
- **Все 27 контрактов:** ~1-2 часа (нормально для ~1M+ минутных баров)
- **Оптимизация дат:** Start = expiry - 18 месяцев (экономия ~40% vs фиксированные даты)

---

## 🐛 Troubleshooting

**Проблема:** "Не найдены FINAM_SECRET_TOKEN или FINAM_ACCOUNT_ID"
- **Решение:** Создайте `.env` файл в корне проекта с учетными данными

**Проблема:** "Ошибка подключения к Finam API"
- **Решение:** Проверьте интернет-соединение и валидность токена
- **Решение:** Убедитесь, что токен не истек (обновите при необходимости)

**Проблема:** "Загружено 0 баров для контракта"
- **Причина 1:** Контракт может быть истекшим или неактивным
- **Причина 2:** ⚠️ **chunk_days > 7** (превышен API лимит!)
- **Решение:** Проверьте символ контракта в Finam API
- **Решение:** Убедитесь что `chunk_days=7` (НЕ 28, НЕ 30!)
- **Решение:** Убедитесь, что период загрузки соответствует времени жизни контракта

**Проблема:** "INVALID_ARGUMENT: Invalid date range"
- **⚠️ ПРИЧИНА:** `chunk_days > 7-9` для M1 timeframe
- **Решение:** Используйте `chunk_days=7` (КРИТИЧЕСКИЙ ЛИМИТ API)
- **НЕ ПЫТАЙТЕСЬ "ОПТИМИЗИРОВАТЬ"** chunk_days - это сломает загрузку!

**Проблема:** "API rate limit exceeded"
- **Решение:** Уменьшите количество одновременных запросов
- **Решение:** Увеличьте задержки между чанками (НЕ chunk_days!)

---

## 📚 Дополнительные ресурсы

**NautilusTrader Documentation:**
- [Data Catalog Guide](https://docs.nautechsystems.io/concepts/data.html#data-catalog)
- [Backtesting with Historical Data](https://docs.nautechsystems.io/concepts/backtesting.html)
- [Parquet Data Catalog API](https://docs.nautechsystems.io/api_reference/persistence.html)

**Finam API:**
- [gRPC API Documentation](https://tradeapi.finam.ru/docs/guides/grpc/)
- [Proto Definitions](https://github.com/FinamWeb/finam-trade-api)

**Task Documentation:**
- [Task README](/workspace/alphamax/task/_projects/trading/fut_over_n/01_load_fut_in_datacatalog/docs/claude/README.md)

**Debug & Troubleshooting:**
- [DEBUG_SUMMARY.md](DEBUG_SUMMARY.md) - Полное расследование проблемы с chunk_days и API лимитами

---

## 🤝 Contributing

Нашли баг или хотите улучшить tutorial? Создайте issue или pull request!

---

**Автор:** Claude Code
**Дата создания:** 2025-10-22
**Версия:** 1.0
