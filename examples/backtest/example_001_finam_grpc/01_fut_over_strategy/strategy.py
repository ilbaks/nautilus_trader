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
FutOverNightStrategy: Простая overnight стратегия на фьючерсах Si.

Логика:
  - Покупка в 17:00 МСК (MARKET, 1 контракт)
  - Продажа в 10:00 МСК следующего дня (MARKET)
  - Без StopLoss/TakeProfit

Автор: Claude Code
Дата: 2025-10-25
"""

import datetime as dt
from decimal import Decimal

import pandas as pd
import pytz

from nautilus_trader.common.enums import LogColor
from nautilus_trader.common.events import TimeEvent
from nautilus_trader.core.datetime import unix_nanos_to_dt
from nautilus_trader.model.data import Bar, BarType
from nautilus_trader.model.enums import OrderSide, TimeInForce
from nautilus_trader.model.identifiers import InstrumentId
from nautilus_trader.model.instruments import Instrument
from nautilus_trader.model.orders import MarketOrder
from nautilus_trader.trading.strategy import Strategy


class FutOverNightStrategy(Strategy):
    """
    Overnight стратегия на фьючерсах Si.

    Параметры:
    ----------
    instrument_id : InstrumentId
        ID инструмента для торговли (например, SiZ5-RTSX.FINAM)
    entry_time_hour : int
        Час входа в позицию (по МСК), по умолчанию 17
    entry_time_minute : int
        Минута входа в позицию (по МСК), по умолчанию 0
    exit_time_hour : int
        Час выхода из позиции (по МСК), по умолчанию 10
    exit_time_minute : int
        Минута выхода из позиции (по МСК), по умолчанию 0
    """

    # Константы для таймеров
    ENTRY_TIMER_NAME = "entry_timer_17_00"
    EXIT_TIMER_NAME = "exit_timer_10_00"

    def __init__(
        self,
        instrument_id: InstrumentId,
        entry_time_hour: int = 17,
        entry_time_minute: int = 0,
        exit_time_hour: int = 10,
        exit_time_minute: int = 0,
    ):
        """
        Инициализация стратегии.

        Parameters
        ----------
        instrument_id : InstrumentId
            ID инструмента для торговли
        entry_time_hour : int, optional
            Час входа в позицию (МСК), по умолчанию 17
        entry_time_minute : int, optional
            Минута входа в позицию (МСК), по умолчанию 0
        exit_time_hour : int, optional
            Час выхода из позиции (МСК), по умолчанию 10
        exit_time_minute : int, optional
            Минута выхода из позиции (МСК), по умолчанию 0
        """
        super().__init__()
        self.instrument_id = instrument_id
        self.entry_time_hour = entry_time_hour
        self.entry_time_minute = entry_time_minute
        self.exit_time_hour = exit_time_hour
        self.exit_time_minute = exit_time_minute

        # Статистика
        self.trades_count = 0
        self.positions_opened = 0
        self.positions_closed = 0

        # Часовой пояс Москвы
        self.moscow_tz = pytz.timezone("Europe/Moscow")

    def on_start(self):
        """Вызывается при старте стратегии."""
        self.log.info("=" * 80, color=LogColor.BLUE)
        self.log.info("FutOverNightStrategy started", color=LogColor.BLUE)
        self.log.info(f"Instrument: {self.instrument_id}", color=LogColor.BLUE)
        self.log.info(f"Entry time: {self.entry_time_hour:02d}:{self.entry_time_minute:02d} MSK", color=LogColor.BLUE)
        self.log.info(f"Exit time: {self.exit_time_hour:02d}:{self.exit_time_minute:02d} MSK", color=LogColor.BLUE)
        self.log.info("=" * 80, color=LogColor.BLUE)

        # Получаем инструмент
        instrument = self.cache.instrument(self.instrument_id)
        if instrument is None:
            self.log.error(f"Instrument {self.instrument_id} not found in cache!")
            return

        # КРИТИЧНО для backtest: подписываемся на бары
        bar_type = BarType.from_str(f"{self.instrument_id}-1-MINUTE-LAST-EXTERNAL")
        self.subscribe_bars(bar_type)
        self.log.info(f"Subscribed to bars: {bar_type}")
        self.log.info("Strategy will check entry/exit times on each bar")

    def on_entry_timer(self, event: TimeEvent):
        """
        Callback для таймера входа в позицию (17:00 МСК).

        Проверяет текущее время и открывает позицию, если время совпадает
        с заданным временем входа.
        """
        if event.name != self.ENTRY_TIMER_NAME:
            return

        # Конвертируем время события в московское время
        event_time_utc = unix_nanos_to_dt(event.ts_event)
        event_time_msk = event_time_utc.astimezone(self.moscow_tz)

        # DEBUG: Логируем первые 3 срабатывания и каждое 17:00
        if not hasattr(self, '_entry_timer_count'):
            self._entry_timer_count = 0
        self._entry_timer_count += 1

        if (self._entry_timer_count <= 3 or
            (event_time_msk.hour == self.entry_time_hour and event_time_msk.minute == self.entry_time_minute)):
            self.log.info(
                f"Entry timer #{self._entry_timer_count}: {event_time_msk.strftime('%Y-%m-%d %H:%M:%S %Z')} "
                f"(hour={event_time_msk.hour}, min={event_time_msk.minute})",
                color=LogColor.YELLOW,
            )

        # Проверяем, наступило ли время входа
        if (event_time_msk.hour == self.entry_time_hour and
            event_time_msk.minute == self.entry_time_minute):

            self.log.info(
                f"✅ Entry time reached: {event_time_msk.strftime('%Y-%m-%d %H:%M:%S %Z')}",
                color=LogColor.GREEN,
            )

            # Проверяем, нет ли уже открытой позиции
            if self.portfolio.is_flat(self.instrument_id):
                self._open_position()
            else:
                self.log.warning(
                    f"Position already exists for {self.instrument_id}, skipping entry",
                    color=LogColor.YELLOW,
                )

    def on_exit_timer(self, event: TimeEvent):
        """
        Callback для таймера выхода из позиции (10:00 МСК).

        Проверяет текущее время и закрывает позицию, если время совпадает
        с заданным временем выхода.
        """
        if event.name != self.EXIT_TIMER_NAME:
            return

        # Конвертируем время события в московское время
        event_time_utc = unix_nanos_to_dt(event.ts_event)
        event_time_msk = event_time_utc.astimezone(self.moscow_tz)

        # Проверяем, наступило ли время выхода
        if (event_time_msk.hour == self.exit_time_hour and
            event_time_msk.minute == self.exit_time_minute):

            self.log.info(
                f"Exit time reached: {event_time_msk.strftime('%Y-%m-%d %H:%M:%S %Z')}",
                color=LogColor.RED,
            )

            # Проверяем, есть ли открытая позиция
            if not self.portfolio.is_flat(self.instrument_id):
                self._close_position()
            else:
                self.log.warning(
                    f"No open position for {self.instrument_id}, skipping exit",
                    color=LogColor.YELLOW,
                )

    def _open_position(self):
        """Открывает длинную позицию (BUY 1 контракт)."""
        instrument = self.cache.instrument(self.instrument_id)
        if instrument is None:
            self.log.error(f"Cannot open position: instrument {self.instrument_id} not found")
            return

        # Создаем MARKET ордер на покупку 1 контракта
        order = self.order_factory.market(
            instrument_id=self.instrument_id,
            order_side=OrderSide.BUY,
            quantity=instrument.make_qty(1),  # 1 контракт
            time_in_force=TimeInForce.GTC,
        )

        self.submit_order(order)
        self.positions_opened += 1

        self.log.info(
            f"BUY order submitted: {order.client_order_id} (1 contract)",
            color=LogColor.GREEN,
        )

    def _close_position(self):
        """Закрывает открытую позицию (SELL все контракты)."""
        # Получаем все открытые позиции для данного инструмента
        positions = self.cache.positions_open(instrument_id=self.instrument_id)

        if not positions:
            self.log.warning(f"No open position to close for {self.instrument_id}")
            return

        # Берем первую позицию (у нас всегда одна)
        position = positions[0]

        # Создаем MARKET ордер на продажу (закрытие позиции)
        order = self.order_factory.market(
            instrument_id=self.instrument_id,
            order_side=OrderSide.SELL,
            quantity=position.quantity,  # Продаем всю позицию
            time_in_force=TimeInForce.GTC,
        )

        self.submit_order(order)
        self.positions_closed += 1

        self.log.info(
            f"SELL order submitted: {order.client_order_id} (close position)",
            color=LogColor.RED,
        )

    def on_bar(self, bar: Bar):
        """Вызывается при получении нового бара - проверяем время входа/выхода."""
        # Конвертируем время бара в московское время
        bar_time_utc = unix_nanos_to_dt(bar.ts_event)
        bar_time_msk = bar_time_utc.astimezone(self.moscow_tz)

        # Логируем первые 5 баров для отладки
        if not hasattr(self, '_bars_received'):
            self._bars_received = 0
        self._bars_received += 1

        if self._bars_received <= 5:
            self.log.info(
                f"Bar #{self._bars_received}: {bar_time_msk.strftime('%Y-%m-%d %H:%M:%S %Z')} | "
                f"Close: {bar.close}",
                color=LogColor.CYAN,
            )

        # ПРОВЕРКА ВРЕМЕНИ ВХОДА (17:00 МСК)
        if (bar_time_msk.hour == self.entry_time_hour and
            bar_time_msk.minute == self.entry_time_minute):

            self.log.info(
                f"✅ Entry time reached: {bar_time_msk.strftime('%Y-%m-%d %H:%M:%S %Z')}",
                color=LogColor.GREEN,
            )

            # Проверяем, нет ли уже открытой позиции
            if self.portfolio.is_flat(self.instrument_id):
                self._open_position()
            else:
                self.log.warning(
                    f"Position already exists for {self.instrument_id}, skipping entry",
                    color=LogColor.YELLOW,
                )

        # ПРОВЕРКА ВРЕМЕНИ ВЫХОДА (10:00 МСК)
        if (bar_time_msk.hour == self.exit_time_hour and
            bar_time_msk.minute == self.exit_time_minute):

            self.log.info(
                f"❌ Exit time reached: {bar_time_msk.strftime('%Y-%m-%d %H:%M:%S %Z')}",
                color=LogColor.RED,
            )

            # Проверяем, есть ли открытая позиция
            if not self.portfolio.is_flat(self.instrument_id):
                self._close_position()
            else:
                self.log.warning(
                    f"No open position for {self.instrument_id}, skipping exit",
                    color=LogColor.YELLOW,
                )

    def on_order_filled(self, event):
        """Вызывается при исполнении ордера."""
        self.trades_count += 1

        self.log.info(
            f"Order filled: {event.client_order_id} | "
            f"Side: {event.order_side} | Qty: {event.last_qty} | "
            f"Price: {event.last_px}",
            color=LogColor.CYAN,
        )

    def on_stop(self):
        """Вызывается при остановке стратегии."""
        self.log.info("=" * 80, color=LogColor.BLUE)
        self.log.info("FutOverNightStrategy stopped", color=LogColor.BLUE)
        self.log.info(f"Total positions opened: {self.positions_opened}", color=LogColor.BLUE)
        self.log.info(f"Total positions closed: {self.positions_closed}", color=LogColor.BLUE)
        self.log.info(f"Total trades executed: {self.trades_count}", color=LogColor.BLUE)
        self.log.info("=" * 80, color=LogColor.BLUE)
