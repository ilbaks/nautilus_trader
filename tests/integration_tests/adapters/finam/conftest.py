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
Shared fixtures for Finam adapter tests.
"""

import pytest

from nautilus_trader.model.identifiers import InstrumentId, Symbol, Venue
from nautilus_trader.model.instruments import FuturesContract
from nautilus_trader.model.objects import Price, Quantity, Currency
from nautilus_trader.model.enums import AssetClass
from nautilus_trader.core.datetime import dt_to_unix_nanos
from datetime import datetime, timezone


@pytest.fixture()
def venue():
    """Provide Finam venue for tests."""
    return Venue("FINAM")


@pytest.fixture()
def instrument(venue):
    """
    Provide a sample Finam futures instrument for tests.

    Returns a Si (RUB/USD futures) contract typical for MOEX.
    """
    return FuturesContract(
        instrument_id=InstrumentId(Symbol("SiZ5-RTSX"), venue),
        raw_symbol=Symbol("SiZ5-RTSX"),
        asset_class=AssetClass.FX,
        currency=Currency.from_str("RUB"),
        price_precision=0,
        price_increment=Price.from_str("1"),
        multiplier=Quantity.from_int(1),
        lot_size=Quantity.from_int(1),
        underlying="USD/RUB",
        activation_ns=dt_to_unix_nanos(datetime(2024, 6, 18, tzinfo=timezone.utc)),
        expiration_ns=dt_to_unix_nanos(datetime(2025, 12, 18, tzinfo=timezone.utc)),
        ts_event=0,
        ts_init=0,
    )


@pytest.fixture()
def data_client():
    """
    Stub data_client fixture for tests that don't require it.

    This satisfies parent conftest requirements without creating actual client.
    """
    return None


@pytest.fixture()
def exec_client():
    """
    Stub exec_client fixture for tests that don't require it.

    This satisfies parent conftest requirements without creating actual client.
    """
    return None


@pytest.fixture()
def account_state():
    """
    Stub account_state fixture for tests that don't require it.

    This satisfies parent conftest requirements without creating actual state.
    """
    return None
