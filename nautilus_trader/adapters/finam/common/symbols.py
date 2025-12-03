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
Helpers for converting between Finam API symbols (``@`` separator) and
Nautilus identifiers (``-`` separator).
"""


def to_nautilus_symbol(symbol: str) -> str:
    """
    Convert a Finam API symbol (``<code>@<exchange>``) into the Nautilus format
    (``<code>-<exchange>``). If the symbol is already in Nautilus format then it
    is returned unchanged.
    """
    if "@" not in symbol:
        return symbol

    instrument, exchange = symbol.rsplit("@", 1)
    return f"{instrument}-{exchange}"


def to_finam_symbol(symbol: str) -> str:
    """
    Convert a Nautilus symbol (``<code>-<exchange>``) into the Finam API format
    (``<code>@<exchange>``). If the symbol already contains ``@`` or does not
    include a separator then the original string is returned.
    """
    if "@" in symbol or "-" not in symbol:
        return symbol

    instrument, exchange = symbol.rsplit("-", 1)
    return f"{instrument}@{exchange}"
