#!/usr/bin/env python
# coding: utf-8

# %% [markdown]
# # 📦 Tutorial: Загрузка фьючерсов Si и CNY в Data Catalog
#
# **Цель:** Загрузить ВСЕЙ ДОСТУПНОЙ ИСТОРИИ по фьючерсам USD/RUB (Si) и CNY/RUB (CR*)
# за период 2024-2027 в ParquetDataCatalog для бэктестинга.
#
# **Период:** 2024-2027 (вся доступная история для каждого контракта до экспирации)
# **Таймфрейм:** M1 (1 минута)
# **Фьючерсы:**
#   - Si (USD/RUB): 14 контрактов (H4, M4, U4, Z4, H5, M5, U5, Z5, H6, M6, U6, Z6, H7, M7)
#   - CR (CNY/RUB): 13 контрактов (CRH4, CRM4, CRU4, CRZ4, CRH5, CRM5, CRU5, CRZ5, CRH6, CRM6, CRU6, CRZ6, CRH7)
#
# **Важно:** CNY фьючерсы используют префикс CR, а не CNYRUB (подтверждено через Finam API)
#
# ## ⚠️ ОГРАНИЧЕНИЯ Finam API (из proto-файлов):
#
# **Размер чанка (одного API запроса) по таймфреймам:**
# - **M1 (1 минута):** максимум **7 дней за один запрос**
# - M5/M15/M30/H1/H2/H4/H8: максимум 30 дней за один запрос
# - D (день): максимум 365 дней за один запрос
# - W/MN/QR (неделя/месяц/квартал): максимум 1825 дней за один запрос
#
# **ВАЖНО:** Это НЕ означает, что доступны только последние N дней!
# - Адаптер **автоматически разбивает** большие периоды на чанки
# - Можно загрузить ЛЮБОЙ период истории (например, 500+ дней для M1)
# - Каждый чанк запрашивается отдельно с задержкой 0.5 сек
# - Пример: 492 дня M1 = ~70 запросов по 7 дней = 83,385 баров ✅
#
# **Доступность истекших контрактов:**
# - Истекшие контракты удаляются из API через несколько месяцев после экспирации
# - Невозможно загрузить данные по удаленным контрактам (ошибка: "Security id doesn't exist")
# - Рекомендуется использовать только АКТИВНЫЕ контракты (экспирация > текущей даты)
#
# **Стратегия работы скрипта:**
# 1. Автоматический chunking для любых периодов
# 2. Merge старых и новых данных с дедупликацией по ts_event
# 3. Пересоздание баров с монотонным ts_init (требование каталога)
#
# **Структура:**
# 1. Setup и конфигурация
# 2. Определение контрактов (квартальные H/M/U/Z, 2024-2027)
# 3. Загрузка истории через Finam gRPC (с учетом лимитов API)
# 4. Сохранение в ParquetDataCatalog с дедупликацией и merge
# 5. Верификация и примеры использования
#
# **Автор:** Claude Code
# **Дата:** 2025-10-22
# **Обновлено:** 2025-10-23 (исправлены символы CNY → CR, добавлены контракты 2024-2027, merge logic)

# %%
import asyncio
import os
import sys
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import List, Dict

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)8s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# %% [markdown]
# ## Часть 1: Импорты и настройка окружения

# %%
# Импорты NautilusTrader
from nautilus_trader.adapters.finam.grpc.client.client import FinamGrpcClient
from nautilus_trader.adapters.finam.grpc.common.enums import TimeFrame
from nautilus_trader.adapters.finam.grpc.parsing.market_data import parse_bar_response
from nautilus_trader.adapters.finam.grpc.streams.bars import BarsStreamManager
from nautilus_trader.common.component import LiveClock, Logger
from nautilus_trader.model.data import BarSpecification, BarType, Bar
from nautilus_trader.model.enums import BarAggregation, PriceType, AggregationSource
from nautilus_trader.model.identifiers import InstrumentId, Symbol, Venue
from nautilus_trader.persistence.catalog.parquet import ParquetDataCatalog

# %% [markdown]
# ## Часть 2: Загрузка учетных данных
#
# **ВАЖНО:** Убедитесь, что файл `.env` содержит:
# ```
# FINAM_SECRET_TOKEN=your_token_here
# FINAM_ACCOUNT_ID=your_account_id_here
# ```

# %%
from dotenv import load_dotenv

# Загружаем переменные окружения
dotenv_path = Path(__file__).parent.parent.parent.parent.parent.parent / ".env"
load_dotenv(dotenv_path)
logger.info(f"✅ Загружены переменные окружения из: {dotenv_path}")

TOKEN = os.getenv("FINAM_SECRET_TOKEN")
ACCOUNT_ID_STR = os.getenv("FINAM_ACCOUNT_ID")

if not TOKEN or not ACCOUNT_ID_STR:
    logger.error("❌ FINAM_SECRET_TOKEN или FINAM_ACCOUNT_ID не найдены в .env")
    raise RuntimeError("Missing credentials in .env file")

ACCOUNT_ID = int(ACCOUNT_ID_STR)
logger.info(f"✅ Учетные данные загружены для аккаунта: {ACCOUNT_ID}")

# Константы
# CATALOG_PATH = Path(__file__).parent / "si_cny_futures_catalog"
CATALOG_PATH = Path("/workspace/alphamax/data/00_datacatalog/NAUTILUS_CATALOG")
VENUE_FINAM = Venue("FINAM")

# %% [markdown]
# ## Часть 3: Определение фьючерсных контрактов
#
# ### Система нотации ММВБ:
# - **Квартальные месяцы:** H=март, M=июнь, U=сентябрь, Z=декабрь
# - **Год:** 4=2024, 5=2025, 6=2026, 7=2027
# - **Примеры:** SiH4@RTSX (Si март 2024), CRU6@RTSX (CNY сентябрь 2026)
#
# ### Загружаемые контракты:
# - **Si (USD/RUB):** 14 контрактов 2024-2027 (H4, M4, U4, Z4, H5, M5, U5, Z5, H6, M6, U6, Z6, H7, M7)
# - **CNY (CNY/RUB):** 13 контрактов 2024-2027 (префикс CR: CRH4, CRM4, CRU4, CRZ4, CRH5, CRM5, CRU5, CRZ5, CRH6, CRM6, CRU6, CRZ6, CRH7)
#
# ### Период загрузки:
# - Для каждого контракта: **ВСЯ ДОСТУПНАЯ ИСТОРИЯ** до даты экспирации

# %%
# Определяем контракты 2024-2027 для загрузки ВСЕЙ ДОСТУПНОЙ ИСТОРИИ
# Символы подтверждены через Finam API (check_available_symbols.py)
# Даты начала = 18 месяцев до экспирации (типичный lifecycle фьючерса)
FUTURES_CONTRACTS = {
    # USD/RUB фьючерсы (Si)
    "Si": [
        # # 2024 год - могут быть в исторических данных
        # {"symbol": "SiH4@RTSX", "name": "Si март 2024", "start": "2022-09-21", "expiry": "2024-03-21"},
        # {"symbol": "SiM4@RTSX", "name": "Si июнь 2024", "start": "2022-12-20", "expiry": "2024-06-20"},
        # {"symbol": "SiU4@RTSX", "name": "Si сентябрь 2024", "start": "2023-03-19", "expiry": "2024-09-19"},
        # {"symbol": "SiZ4@RTSX", "name": "Si декабрь 2024", "start": "2023-06-19", "expiry": "2024-12-19"},
        # # 2025-2027 - активно торгуются
        # {"symbol": "SiH5@RTSX", "name": "Si март 2025", "start": "2023-09-20", "expiry": "2025-03-20"},
        # {"symbol": "SiM5@RTSX", "name": "Si июнь 2025", "start": "2023-12-19", "expiry": "2025-06-19"},
        # {"symbol": "SiU5@RTSX", "name": "Si сентябрь 2025", "start": "2024-03-18", "expiry": "2025-09-18"},
        {"symbol": "SiZ5@RTSX", "name": "Si декабрь 2025", "start": "2024-06-18", "expiry": "2025-12-18"},
        # {"symbol": "SiH6@RTSX", "name": "Si март 2026", "start": "2024-09-19", "expiry": "2026-03-19"},
        # {"symbol": "SiM6@RTSX", "name": "Si июнь 2026", "start": "2024-12-18", "expiry": "2026-06-18"},
        # {"symbol": "SiU6@RTSX", "name": "Si сентябрь 2026", "start": "2025-03-17", "expiry": "2026-09-17"},
        # {"symbol": "SiZ6@RTSX", "name": "Si декабрь 2026", "start": "2025-06-17", "expiry": "2026-12-17"},
        # {"symbol": "SiH7@RTSX", "name": "Si март 2027", "start": "2025-09-18", "expiry": "2027-03-18"},
        # {"symbol": "SiM7@RTSX", "name": "Si июнь 2027", "start": "2025-12-17", "expiry": "2027-06-17"},
    ],
    # # CNY/RUB фьючерсы (CR* - подтверждено через API)
    # "CNY": [
    #     # 2024 год - могут быть в исторических данных
    #     {"symbol": "CRH4@RTSX", "name": "CNY март 2024", "start": "2022-09-21", "expiry": "2024-03-21"},
    #     {"symbol": "CRM4@RTSX", "name": "CNY июнь 2024", "start": "2022-12-20", "expiry": "2024-06-20"},
    #     {"symbol": "CRU4@RTSX", "name": "CNY сентябрь 2024", "start": "2023-03-19", "expiry": "2024-09-19"},
    #     {"symbol": "CRZ4@RTSX", "name": "CNY декабрь 2024", "start": "2023-06-19", "expiry": "2024-12-19"},
    #     # 2025-2027 - активно торгуются (подтверждено в API)
    #     {"symbol": "CRH5@RTSX", "name": "CNY март 2025", "start": "2023-09-20", "expiry": "2025-03-20"},
    #     {"symbol": "CRM5@RTSX", "name": "CNY июнь 2025", "start": "2023-12-19", "expiry": "2025-06-19"},
    #     {"symbol": "CRU5@RTSX", "name": "CNY сентябрь 2025", "start": "2024-03-18", "expiry": "2025-09-18"},
    #     {"symbol": "CRZ5@RTSX", "name": "CNY декабрь 2025", "start": "2024-06-18", "expiry": "2025-12-18"},
    #     {"symbol": "CRH6@RTSX", "name": "CNY март 2026", "start": "2024-09-19", "expiry": "2026-03-19"},
    #     {"symbol": "CRM6@RTSX", "name": "CNY июнь 2026", "start": "2024-12-18", "expiry": "2026-06-18"},
    #     {"symbol": "CRU6@RTSX", "name": "CNY сентябрь 2026", "start": "2025-03-17", "expiry": "2026-09-17"},
    #     {"symbol": "CRZ6@RTSX", "name": "CNY декабрь 2026", "start": "2025-06-17", "expiry": "2026-12-17"},
    #     {"symbol": "CRH7@RTSX", "name": "CNY март 2027", "start": "2025-09-18", "expiry": "2027-03-18"},
    # ],
}

# Выводим список контрактов
logger.info("=" * 80)
logger.info("📋 СПИСОК КОНТРАКТОВ ДЛЯ ЗАГРУЗКИ")
logger.info("=" * 80)
for instrument, contracts in FUTURES_CONTRACTS.items():
    logger.info(f"\n{instrument} ({len(contracts)} контрактов):")
    for contract in contracts:
        logger.info(f"  - {contract['symbol']}: {contract['name']}")

# %% [markdown]
# ## Часть 4: Функция загрузки исторических данных
#
# Использует метод `request_historical_bars()` с автоматическим chunking.
# Данные разбиваются на чанки по 7 дней для обхода ограничений Finam API (30 дней max).

# %%
async def load_historical_bars_for_contract(
    client: FinamGrpcClient,
    contract: Dict,
    timeframe: TimeFrame = TimeFrame.M1,
) -> List:
    """
    Загружает исторические бары для одного фьючерсного контракта.

    Parameters
    ----------
    client : FinamGrpcClient
        Подключенный gRPC клиент
    contract : Dict
        Информация о контракте (symbol, name, start, end)
    timeframe : TimeFrame
        Таймфрейм (default: M1)

    Returns
    -------
    List
        Список NautilusTrader Bar objects
    """
    symbol = contract["symbol"]
    name = contract["name"]

    logger.info(f"\n{'=' * 60}")
    logger.info(f"📊 Загрузка: {name} ({symbol})")
    logger.info(f"{'=' * 60}")

    # Парсим период: от указанной даты до экспирации или текущей даты
    start_time = datetime.fromisoformat(contract["start"]).replace(tzinfo=timezone.utc)
    expiry_time = datetime.fromisoformat(contract["expiry"]).replace(tzinfo=timezone.utc)

    # Загружаем до экспирации или до текущей даты (что раньше)
    now = datetime.now(timezone.utc)
    end_time = min(expiry_time, now)

    days_range = (end_time - start_time).days
    logger.info(f"   Период: {start_time.date()} → {end_time.date()} ({days_range} дней)")
    logger.info(f"   Экспирация контракта: {expiry_time.date()}")

    # Создаем InstrumentId и BarType
    nautilus_symbol = symbol.replace("@", "-")
    instrument_id = InstrumentId(Symbol(nautilus_symbol), VENUE_FINAM)

    if timeframe == TimeFrame.M1:
        bar_spec = BarSpecification(1, BarAggregation.MINUTE, PriceType.LAST)
    elif timeframe == TimeFrame.M5:
        bar_spec = BarSpecification(5, BarAggregation.MINUTE, PriceType.LAST)
    elif timeframe == TimeFrame.H1:
        bar_spec = BarSpecification(1, BarAggregation.HOUR, PriceType.LAST)
    else:
        logger.error(f"Неподдерживаемый timeframe: {timeframe}")
        return []

    bar_type = BarType(
        instrument_id=instrument_id,
        bar_spec=bar_spec,
        aggregation_source=AggregationSource.EXTERNAL,
    )

    # Создаем stream manager
    stream = BarsStreamManager(client, Logger(f"BarsStream_{symbol}"))
    clock = LiveClock()

    try:
        import time
        request_start = time.time()

        # Запрашиваем исторические данные с automatic chunking
        proto_bars = await stream.request_historical_bars(
            symbol=symbol,
            timeframe=timeframe,
            start_time=start_time,
            end_time=end_time,
            chunk_days=7,  # Размер чанка: 7 дней для M1 (адаптер автоматически делает множество запросов)
        )

        request_duration = time.time() - request_start
        logger.info(f"   ⏱️  API запрос: {request_duration:.2f}s ({len(proto_bars)} protobuf bars)")

        # Конвертируем в NautilusTrader Bar objects
        nautilus_bars = []
        for proto_bar in proto_bars:
            from nautilus_trader.adapters.finam.grpc.proto.finam_grpc.tradeapi.v1.marketdata.marketdata_service_pb2 import (
                SubscribeBarsResponse,
            )

            mock_response = SubscribeBarsResponse(symbol=symbol, bars=[proto_bar])
            ts_init = clock.timestamp_ns()
            parsed = parse_bar_response(mock_response, instrument_id, bar_type, ts_init)
            nautilus_bars.extend(parsed)

        if nautilus_bars:
            first_bar_time = datetime.fromtimestamp(nautilus_bars[0].ts_event / 1e9, tz=timezone.utc)
            last_bar_time = datetime.fromtimestamp(nautilus_bars[-1].ts_event / 1e9, tz=timezone.utc)
            actual_days = (last_bar_time - first_bar_time).total_seconds() / 86400

            logger.info(f"✅ Загружено {len(nautilus_bars)} баров")
            logger.info(f"   📅 Фактический диапазон: {first_bar_time.strftime('%Y-%m-%d')} → {last_bar_time.strftime('%Y-%m-%d')} ({actual_days:.1f} дней)")
        else:
            logger.warning(f"⚠️  Загружено 0 баров (контракт может быть неактивен или данных нет)")

        return nautilus_bars

    except Exception as e:
        logger.error(f"❌ Ошибка при загрузке {symbol}: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return []

# %% [markdown]
# ## Часть 5: Главная функция загрузки и сохранения

# %%
async def main():
    """Основная функция загрузки всех контрактов."""

    logger.info("=" * 80)
    logger.info("📦 ЗАГРУЗКА ФЬЮЧЕРСОВ Si И CNY В DATA CATALOG")
    logger.info("=" * 80)

    # 1. Создаем каталог
    logger.info(f"\n📁 Создаем каталог: {CATALOG_PATH}")
    catalog = ParquetDataCatalog(str(CATALOG_PATH))

    # 2. Подключаемся к Finam
    logger.info(f"\n🔌 Подключаемся к Finam (Account: {ACCOUNT_ID})")
    client = FinamGrpcClient(client_id=ACCOUNT_ID, access_token=TOKEN)
    await client.connect()
    logger.info("✅ Подключение установлено")

    # 3. Загружаем данные для всех контрактов
    all_bars_by_contract = {}

    for instrument_name, contracts in FUTURES_CONTRACTS.items():
        logger.info(f"\n\n{'#' * 80}")
        logger.info(f"# ИНСТРУМЕНТ: {instrument_name}")
        logger.info(f"{'#' * 80}")

        for contract in contracts:
            symbol = contract["symbol"]

            # Загружаем минутные бары
            bars = await load_historical_bars_for_contract(
                client=client,
                contract=contract,
                timeframe=TimeFrame.M1,
            )

            if bars:
                all_bars_by_contract[symbol] = bars
                logger.info(f"✅ Собрано {len(bars)} баров для {symbol}")
            else:
                logger.warning(f"⚠️  Нет данных для {symbol}")

    # 4. Отключаемся от Finam
    await client.disconnect()
    logger.info("\n🔌 Отключились от Finam")

    # 5. Сохраняем данные в каталог с дедупликацией
    logger.info(f"\n\n{'=' * 80}")
    logger.info("💾 СОХРАНЕНИЕ ДАННЫХ В КАТАЛОГ")
    logger.info(f"{'=' * 80}")

    for symbol, new_bars in all_bars_by_contract.items():
        if not new_bars:
            continue

        logger.info(f"\n{'=' * 60}")
        logger.info(f"💾 Обработка {symbol}: {len(new_bars)} новых баров")

        try:
            # Формируем идентификатор
            nautilus_symbol = symbol.replace("@", "-")
            instrument_id = InstrumentId(Symbol(nautilus_symbol), VENUE_FINAM)

            # 1. Читаем существующие данные для merge (доливка)
            logger.info(f"📖 Читаем существующие данные...")
            try:
                existing_bars = catalog.bars(instrument_ids=[str(instrument_id)])
                logger.info(f"   Найдено существующих: {len(existing_bars)} баров")
            except Exception:
                existing_bars = []
                logger.info(f"   Существующих данных нет (первая загрузка)")

            # 2. Объединяем и дедуплицируем по ts_event
            logger.info(f"🔀 Объединяем старые и новые данные...")
            all_bars_combined = list(existing_bars) + list(new_bars)
            logger.info(f"   Всего баров для обработки: {len(all_bars_combined)}")

            logger.info(f"🧹 Дедупликация по ts_event...")
            bars_dict = {}
            for bar in all_bars_combined:
                ts_event = bar.ts_event
                # Оставляем бар с наибольшим ts_init (самый свежий)
                if ts_event not in bars_dict or bar.ts_init > bars_dict[ts_event].ts_init:
                    bars_dict[ts_event] = bar

            # Сортируем по ts_event (время события на бирже)
            sorted_bars = sorted(bars_dict.values(), key=lambda b: b.ts_event)

            duplicates_removed = len(all_bars_combined) - len(sorted_bars)
            logger.info(f"   Удалено дубликатов: {duplicates_removed}")
            logger.info(f"   Итого уникальных: {len(sorted_bars)}")

            # 3. Пересоздаем бары с монотонным ts_init
            # КРИТИЧНО: Каталог требует строгую монотонность по ts_init
            # Решение: пересоздаем все бары (старые + новые) с единым базовым ts_init
            logger.info(f"🔄 Пересоздаем бары с монотонным ts_init...")
            current_ts_init = int(datetime.now(timezone.utc).timestamp() * 1_000_000_000)  # nanoseconds
            deduplicated_bars = []

            for bar in sorted_bars:
                # Создаем новый бар с актуальным ts_init
                new_bar = Bar(
                    bar_type=bar.bar_type,
                    open=bar.open,
                    high=bar.high,
                    low=bar.low,
                    close=bar.close,
                    volume=bar.volume,
                    ts_event=bar.ts_event,
                    ts_init=current_ts_init,
                )
                deduplicated_bars.append(new_bar)
                current_ts_init += 1  # Инкремент для строгой монотонности

            logger.info(f"   Создано баров с монотонным ts_init: {len(deduplicated_bars)}")

            # 3. Удаляем ВСЕ старые данные перед записью обновленного набора
            bar_type_str = f"{nautilus_symbol}.FINAM-1-MINUTE-LAST-EXTERNAL"
            logger.info(f"🗑️  Удаляем старые данные для {symbol}")

            try:
                catalog.delete_data_range(
                    data_cls=Bar,
                    identifier=bar_type_str,
                    start=None,
                    end=None,
                )
                logger.info(f"   ✅ Старые данные удалены")
            except Exception:
                logger.info(f"   ℹ️  Старых данных не было (первая загрузка)")

            # 4. Записываем объединенный набор (merge)
            if deduplicated_bars:
                catalog.write_data(deduplicated_bars)
                logger.info(f"✅ Сохранено {len(deduplicated_bars)} уникальных баров")
            else:
                logger.warning(f"⚠️  Нет данных для сохранения")

        except Exception as e:
            logger.error(f"❌ Ошибка при сохранении {symbol}: {e}", exc_info=True)

    # 6. Верификация данных
    logger.info(f"\n\n{'=' * 80}")
    logger.info("🔍 ВЕРИФИКАЦИЯ ДАННЫХ В КАТАЛОГЕ")
    logger.info(f"{'=' * 80}")

    # Список типов данных
    data_types = catalog.list_data_types()
    logger.info(f"\n📋 Типы данных в каталоге:")
    for dt in data_types:
        logger.info(f"  - {dt}")

    # Получаем все бары
    all_saved_bars = catalog.bars()
    logger.info(f"\n📊 Всего баров в каталоге: {len(all_saved_bars)}")

    # Проверяем по каждому инструменту
    for instrument_name, contracts in FUTURES_CONTRACTS.items():
        logger.info(f"\n{'=' * 60}")
        logger.info(f"📈 {instrument_name} (всего {len(contracts)} контрактов)")
        logger.info(f"{'=' * 60}")

        total_bars_for_instrument = 0

        for contract in contracts:
            symbol = contract["symbol"]
            nautilus_symbol = symbol.replace("@", "-")
            instrument_id = InstrumentId(Symbol(nautilus_symbol), VENUE_FINAM)
            symbol_bars = catalog.bars(instrument_ids=[str(instrument_id)])

            if symbol_bars:
                total_bars_for_instrument += len(symbol_bars)
                first_bar_dt = datetime.fromtimestamp(symbol_bars[0].ts_event / 1e9, tz=timezone.utc)
                last_bar_dt = datetime.fromtimestamp(symbol_bars[-1].ts_event / 1e9, tz=timezone.utc)

                logger.info(f"\n✅ {symbol}:")
                logger.info(f"   Баров: {len(symbol_bars)}")
                logger.info(f"   Период: {first_bar_dt.strftime('%Y-%m-%d')} → {last_bar_dt.strftime('%Y-%m-%d')}")
                logger.info(f"   Первый бар: O={symbol_bars[0].open} C={symbol_bars[0].close}")
                logger.info(f"   Последний бар: O={symbol_bars[-1].open} C={symbol_bars[-1].close}")
            else:
                logger.warning(f"\n⚠️  {symbol}: Нет данных в каталоге")

        logger.info(f"\n📊 ИТОГО по {instrument_name}: {total_bars_for_instrument} баров")

    # Финальная статистика
    logger.info("\n" + "=" * 80)
    logger.info("🎉 ЗАГРУЗКА ЗАВЕРШЕНА!")
    logger.info("=" * 80)
    logger.info(f"\n📁 Каталог: {CATALOG_PATH}")
    logger.info(f"📊 Всего загружено: {len(all_saved_bars)} баров")
    logger.info(f"📈 Инструментов: {sum(len(contracts) for contracts in FUTURES_CONTRACTS.values())}")
    logger.info(f"\n💡 Используйте каталог для backtesting в NautilusTrader!")

# %% [markdown]
# ## Часть 6: Запуск загрузки

# %%
# Запускаем главную функцию
await main()

# %% [markdown]
# ## Часть 7: Примеры работы с загруженными данными
#
# После успешной загрузки данных, вы можете использовать следующие примеры
# для работы с каталогом.

# %%
def example_query_catalog():
    """Пример запроса данных из каталога."""
    catalog = ParquetDataCatalog(str(CATALOG_PATH))

    # Пример 1: Получить все бары для конкретного контракта
    symbol = "SiZ4-RTSX"  # Декабрь 2024
    instrument_id = InstrumentId(Symbol(symbol), VENUE_FINAM)

    bars = catalog.bars(instrument_ids=[str(instrument_id)])
    print(f"\n✅ Контракт {symbol}: {len(bars)} баров")

    if bars:
        print(f"   Первый бар: {bars[0]}")
        print(f"   Последний бар: {bars[-1]}")

    # Пример 2: Фильтрация по времени
    end_time = datetime.now(timezone.utc)
    start_time = end_time - timedelta(days=30)

    recent_bars = catalog.bars(
        instrument_ids=[str(instrument_id)],
        start=start_time.isoformat(),
        end=end_time.isoformat(),
    )
    print(f"\n✅ Последние 30 дней для {symbol}: {len(recent_bars)} баров")

    # Пример 3: Получить все данные по всем Si контрактам 2024-2027
    si_symbols = [f"Si{code}-RTSX" for code in ["H4", "M4", "U4", "Z4", "H5", "M5", "U5", "Z5", "H6", "M6", "U6", "Z6", "H7", "M7"]]
    si_instrument_ids = [str(InstrumentId(Symbol(s), VENUE_FINAM)) for s in si_symbols]

    all_si_bars = catalog.bars(instrument_ids=si_instrument_ids)
    print(f"\n✅ Все Si контракты (2024-2027): {len(all_si_bars)} баров")

    # Пример 4: Получить CNY контракты (используем префикс CR)
    cny_symbols = [f"CR{code}-RTSX" for code in ["H4", "M4", "U4", "Z4", "Z5", "H6", "M6", "U6", "Z6", "H7"]]
    cny_instrument_ids = [str(InstrumentId(Symbol(s), VENUE_FINAM)) for s in cny_symbols]

    all_cny_bars = catalog.bars(instrument_ids=cny_instrument_ids)
    print(f"\n✅ Все CNY контракты (2024-2027): {len(all_cny_bars)} баров")

# Раскомментируйте для запуска примера:
# example_query_catalog()

# %% [markdown]
# ## 🎉 Tutorial завершен!
#
# **Что вы узнали:**
# - Как определять фьючерсные контракты по нотации ММВБ (H/M/U/Z)
# - Как загружать большие объемы исторических данных с automatic chunking
# - Как сохранять данные в ParquetDataCatalog с дедупликацией
# - Как запрашивать данные из каталога для backtesting
#
# **Следующие шаги:**
# 1. Запустите `await main()` для загрузки данных
# 2. Используйте `example_query_catalog()` для проверки
# 3. Интегрируйте каталог в ваши backtesting стратегии
#
# **Полезные ссылки:**
# - NautilusTrader Data Catalog: https://docs.nautechsystems.io/concepts/data.html
# - Finam gRPC API: https://tradeapi.finam.ru/docs/guides/grpc/

# %%
if __name__ == "__main__":
    # Запускаем асинхронную функцию
    asyncio.run(main())
