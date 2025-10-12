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
Enums for Finam gRPC adapter.

This module provides Python enums that wrap Protobuf enums for better IDE support
and type safety.
"""

from enum import Enum

# Import Protobuf TimeFrame enum
from nautilus_trader.adapters.finam.grpc.proto.finam_grpc.tradeapi.v1.marketdata.marketdata_service_pb2 import (
    TIME_FRAME_M1 as _TIME_FRAME_M1,
    TIME_FRAME_M5 as _TIME_FRAME_M5,
    TIME_FRAME_M15 as _TIME_FRAME_M15,
    TIME_FRAME_M30 as _TIME_FRAME_M30,
    TIME_FRAME_H1 as _TIME_FRAME_H1,
    TIME_FRAME_H2 as _TIME_FRAME_H2,
    TIME_FRAME_H4 as _TIME_FRAME_H4,
    TIME_FRAME_H8 as _TIME_FRAME_H8,
    TIME_FRAME_D as _TIME_FRAME_D,
    TIME_FRAME_W as _TIME_FRAME_W,
    TIME_FRAME_MN as _TIME_FRAME_MN,
    TIME_FRAME_QR as _TIME_FRAME_QR,
)


class TimeFrame(Enum):
    """
    Finam Bar Timeframe enum.

    Wraps Protobuf TimeFrame enum for better Python integration.

    Usage:
        >>> timeframe = TimeFrame.M1
        >>> request = SubscribeBarsRequest(symbol="SBER", timeframe=timeframe.value)
    """

    M1 = _TIME_FRAME_M1      # 1 minute
    M5 = _TIME_FRAME_M5      # 5 minutes
    M15 = _TIME_FRAME_M15    # 15 minutes
    M30 = _TIME_FRAME_M30    # 30 minutes
    H1 = _TIME_FRAME_H1      # 1 hour
    H2 = _TIME_FRAME_H2      # 2 hours
    H4 = _TIME_FRAME_H4      # 4 hours
    H8 = _TIME_FRAME_H8      # 8 hours
    D = _TIME_FRAME_D        # Daily
    W = _TIME_FRAME_W        # Weekly
    MN = _TIME_FRAME_MN      # Monthly
    QR = _TIME_FRAME_QR      # Quarterly

    @classmethod
    def from_string(cls, timeframe_str: str) -> "TimeFrame":
        """
        Create TimeFrame from string.

        Parameters
        ----------
        timeframe_str : str
            Timeframe string (e.g., "M1", "H1", "D")

        Returns
        -------
        TimeFrame
            The corresponding TimeFrame enum

        Raises
        ------
        ValueError
            If timeframe_str is not valid
        """
        timeframe_upper = timeframe_str.upper()
        try:
            return cls[timeframe_upper]
        except KeyError:
            valid_values = ", ".join(tf.name for tf in cls)
            raise ValueError(
                f"Invalid timeframe '{timeframe_str}'. "
                f"Valid values: {valid_values}"
            )

    def to_protobuf(self) -> int:
        """
        Get Protobuf enum value.

        Returns
        -------
        int
            Protobuf TimeFrame enum value
        """
        return self.value

    def __str__(self) -> str:
        """Return string representation."""
        return self.name

    def __repr__(self) -> str:
        """Return detailed representation."""
        return f"TimeFrame.{self.name}"
