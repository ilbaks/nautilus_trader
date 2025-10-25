#!/usr/bin/env python3
# -------------------------------------------------------------------------------------------------
#  Copyright (C) 2015-2025 Nautech Systems Pty Ltd. All rights reserved.
#  https://nautechsystems.io
#
#  Licensed under the GNU Lesser General Public License Version 3.0 (the "License");
#  You may not use this file except in compliance with the License.
#  You may obtain a copy of the License at https://www.gnu.org/licenses/lgpl-3.0.en.html
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
# -------------------------------------------------------------------------------------------------

"""
Backtest runner для FutOverNightStrategy.

Запускает бэктест стратегии overnight торговли на фьючерсах Si
за период 21.08.2025 - 21.10.2025.

Автор: Claude Code
Дата: 2025-10-25
"""

from decimal import Decimal
from pathlib import Path

import pandas as pd

from strategy import FutOverNightStrategy

from nautilus_trader.backtest.engine import BacktestEngine
from nautilus_trader.config import BacktestEngineConfig
from nautilus_trader.config import LoggingConfig
from nautilus_trader.model import TraderId
from nautilus_trader.model.currencies import USD, RUB
from nautilus_trader.model.enums import AccountType
from nautilus_trader.model.enums import OmsType
from nautilus_trader.model.identifiers import InstrumentId, Venue
from nautilus_trader.model.objects import Money
from nautilus_trader.persistence.catalog.parquet import ParquetDataCatalog


if __name__ == "__main__":
    """
    Запуск бэктеста FutOverNightStrategy на данных SiZ5 фьючерса.

    Стратегия:
    ----------
    - Вход: 17:00 МСК (MARKET BUY, 1 контракт)
    - Выход: 10:00 МСК следующего дня (MARKET SELL)

    Период тестирования:
    -------------------
    21.08.2025 - 21.10.2025

    Данные:
    -------
    Загружаются из ParquetDataCatalog (1-минутные бары SiZ5-RTSX.FINAM)
    """

    # ----------------------------------------------------------------------------------
    # 1. Настройка путей и параметров
    # ----------------------------------------------------------------------------------

    # Путь к каталогу с данными (централизованный каталог)
    CATALOG_PATH = Path("/workspace/alphamax/data/00_datacatalog/NAUTILUS_CATALOG")

    # ID инструмента
    INSTRUMENT_ID = InstrumentId.from_str("SiZ5-RTSX.FINAM")

    # Период бэктеста (UTC для совместимости с каталогом)
    START_DATE = pd.Timestamp("2025-08-20 21:00", tz="UTC")  # 21.08.2025 00:00 МСК
    END_DATE = pd.Timestamp("2025-10-20 21:00", tz="UTC")     # 21.10.2025 00:00 МСК

    print("=" * 80)
    print("FutOverNightStrategy Backtest")
    print("=" * 80)
    print(f"Instrument: {INSTRUMENT_ID}")
    print(f"Period: {START_DATE} - {END_DATE}")
    print(f"Catalog: {CATALOG_PATH}")
    print("=" * 80)

    # ----------------------------------------------------------------------------------
    # 2. Создание инструмента и загрузка данных из каталога
    # ----------------------------------------------------------------------------------

    print("\n📦 Creating instrument and loading data from catalog...")

    from nautilus_trader.model.instruments import FuturesContract
    from nautilus_trader.model.objects import Price, Quantity
    from nautilus_trader.model.enums import AssetClass

    # Создаем инструмент вручную (т.к. в каталоге нет метаданных)
    # ВАЖНО: Precision должен совпадать с данными в каталоге!
    # size_precision определяется автоматически из lot_size.precision
    instrument = FuturesContract(
        instrument_id=INSTRUMENT_ID,
        raw_symbol=INSTRUMENT_ID.symbol,
        asset_class=AssetClass.FX,  # Валютный фьючерс (FX)
        currency=RUB,  # Валюта котировки
        price_precision=1,  # Данные имеют price.precision=1
        price_increment=Price(Decimal("0.1"), precision=1),  # Минимальный шаг цены = 0.1 руб
        multiplier=Quantity(Decimal("1000.0"), precision=1),  # 1000 USD за 1 контракт
        lot_size=Quantity(Decimal("0.1"), precision=1),  # precision=1 для volume (данные имеют volume.precision=1)
        underlying="USD/RUB",  # Базовый актив
        activation_ns=0,  # Начало торгов (0 = активен)
        expiration_ns=int(pd.Timestamp("2025-12-18 14:00", tz="UTC").timestamp() * 1e9),  # Экспирация
        ts_event=0,
        ts_init=0,
        exchange="RTSX",  # Московская биржа (секция срочного рынка)
    )

    print(f"✅ Instrument created: {instrument.id}")
    print(f"   Symbol: {instrument.id.symbol}")
    print(f"   Asset: {instrument.underlying}")
    print(f"   Price precision: {instrument.price_precision}")
    print(f"   Size precision: {instrument.size_precision}")
    print(f"   Expiration: {pd.to_datetime(instrument.expiration_ns, unit='ns', utc=True)}")

    # Загружаем бары из каталога (все доступные)
    catalog = ParquetDataCatalog(CATALOG_PATH)

    # Загружаем все бары (фильтрацию по периоду сделает BacktestEngine)
    bars = catalog.bars(instrument_ids=[str(INSTRUMENT_ID)])

    if not bars:
        raise ValueError(f"No bars found for {INSTRUMENT_ID} in catalog!")

    print(f"✅ Bars loaded: {len(bars)} bars (total)")
    print(f"   First bar: {pd.to_datetime(bars[0].ts_event, unit='ns', utc=True).tz_convert('Europe/Moscow')}")
    print(f"   Last bar: {pd.to_datetime(bars[-1].ts_event, unit='ns', utc=True).tz_convert('Europe/Moscow')}")

    # Фильтруем бары по нужному периоду вручную
    start_ns = START_DATE.value
    end_ns = END_DATE.value

    bars_filtered = [bar for bar in bars if start_ns <= bar.ts_event <= end_ns]

    if not bars_filtered:
        raise ValueError(f"No bars in requested period {START_DATE} - {END_DATE}!")

    print(f"✅ Filtered to period: {len(bars_filtered)} bars")
    print(f"   Period: {pd.to_datetime(bars_filtered[0].ts_event, unit='ns', utc=True).tz_convert('Europe/Moscow')} - "
          f"{pd.to_datetime(bars_filtered[-1].ts_event, unit='ns', utc=True).tz_convert('Europe/Moscow')}")

    # Проверяем несколько баров из разных частей периода
    print(f"\n📊 Sample bars check:")
    print(f"   First bar time: {pd.to_datetime(bars_filtered[0].ts_event, unit='ns', utc=True).tz_convert('Europe/Moscow')}")
    print(f"   Middle bar time: {pd.to_datetime(bars_filtered[len(bars_filtered)//2].ts_event, unit='ns', utc=True).tz_convert('Europe/Moscow')}")
    print(f"   Last bar time: {pd.to_datetime(bars_filtered[-1].ts_event, unit='ns', utc=True).tz_convert('Europe/Moscow')}")
    print(f"   Time span: {pd.to_datetime(bars_filtered[-1].ts_event, unit='ns', utc=True) - pd.to_datetime(bars_filtered[0].ts_event, unit='ns', utc=True)}")

    bars = bars_filtered  # Используем отфильтрованные бары

    # ----------------------------------------------------------------------------------
    # 3. Конфигурация и создание Backtest Engine
    # ----------------------------------------------------------------------------------

    print("\n🔧 Configuring backtest engine...")

    engine_config = BacktestEngineConfig(
        trader_id=TraderId("BACKTEST-FUTOVER-001"),
        logging=LoggingConfig(
            log_level="INFO",  # INFO для основных событий
        ),
    )

    engine = BacktestEngine(config=engine_config)

    # ----------------------------------------------------------------------------------
    # 4. Настройка торгового окружения
    # ----------------------------------------------------------------------------------

    print("🏛️ Setting up trading environment...")

    # Добавляем venue с MARGIN аккаунтом
    engine.add_venue(
        venue=Venue("FINAM"),
        oms_type=OmsType.NETTING,  # Неттинг для фьючерсов
        account_type=AccountType.MARGIN,  # MARGIN аккаунт для фьючерсов
        starting_balances=[Money(1_000_000, RUB)],  # Начальный капитал 1 млн рублей
        base_currency=RUB,
        default_leverage=Decimal(1),  # Без плеча (можно увеличить при необходимости)
    )

    # Регистрируем инструмент
    engine.add_instrument(instrument)

    # Загружаем исторические данные
    engine.add_data(bars)

    print(f"✅ Venue added: FINAM (MARGIN account)")
    print(f"✅ Starting balance: 1,000,000 RUB")

    # ----------------------------------------------------------------------------------
    # 5. Создание и запуск стратегии
    # ----------------------------------------------------------------------------------

    print("\n🚀 Creating and running strategy...")

    # Создаем стратегию
    strategy = FutOverNightStrategy(
        instrument_id=INSTRUMENT_ID,
        entry_time_hour=17,  # Вход в 17:00 МСК
        entry_time_minute=0,
        exit_time_hour=10,   # Выход в 10:00 МСК
        exit_time_minute=0,
    )

    # Добавляем стратегию в движок
    engine.add_strategy(strategy)

    # Запускаем бэктест
    print("\n▶️ Running backtest...\n")
    engine.run()

    # ----------------------------------------------------------------------------------
    # 6. Вывод результатов
    # ----------------------------------------------------------------------------------

    print("\n" + "=" * 80)
    print("📊 BACKTEST RESULTS")
    print("=" * 80)

    # Получаем статистику
    account = engine.trader.generate_account_report(Venue("FINAM"))
    print("\n💰 Account Summary:")
    print(account)

    # Статистика позиций
    positions = engine.trader.generate_positions_report()
    print("\n📈 Positions Summary:")
    print(positions)

    # Статистика ордеров
    orders = engine.trader.generate_orders_report()
    print("\n📋 Orders Summary:")
    print(orders)

    # Статистика заполнений
    fills = engine.trader.generate_fills_report()
    print("\n✅ Fills Summary:")
    print(fills)

    print("\n" + "=" * 80)
    print("✅ Backtest completed successfully!")
    print("=" * 80)

    # Очистка ресурсов
    engine.dispose()
