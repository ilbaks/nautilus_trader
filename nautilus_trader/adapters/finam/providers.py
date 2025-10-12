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
#%%
from nautilus_trader.adapters.finam.grpc.client.client import FinamGrpcClient
from nautilus_trader.adapters.finam.grpc.proto.finam_grpc.tradeapi.v1.assets.assets_service_pb2 import (
    AssetsRequest,
)
from nautilus_trader.adapters.finam.parsing.instruments import parse_instrument
from nautilus_trader.common.component import Clock
from nautilus_trader.common.providers import InstrumentProvider
from nautilus_trader.config import InstrumentProviderConfig
from nautilus_trader.core.correctness import PyCondition
from nautilus_trader.model.identifiers import InstrumentId
#%%

class FinamInstrumentProvider(InstrumentProvider):
    """
    Provides instruments from Finam Trade API via gRPC.

    Parameters
    ----------
    client : FinamGrpcClient
        The Finam gRPC client.
    clock : Clock
        The clock from timestamp generation.
    config : InstrumentProviderConfig, optional
        The instrument provider configuration.
    """

    def __init__(
        self,
        client: FinamGrpcClient,
        clock: Clock,
        config: InstrumentProviderConfig | None = None,
    ) -> None:
        super().__init__(config=config)

        self._client = client
        self._clock = clock
        
    async def load_all_async(
        self,
        filters: dict | None = None,
    ) -> None:
        """
        Load all instruments from Finam API via gRPC AssetsService.Assets().

        Parameters
        ----------
        filters : dict, optional
            Currently not used (reserved for future filtering)
        """
        self._log.info("Loading all instruments from Finam gRPC API...")

        try:
            # Call gRPC AssetsService.Assets()
            request = AssetsRequest()
            metadata = await self._client.get_metadata()
            response = await self._client.assets.Assets(request, metadata=metadata)

            # Parse each Protobuf Asset -> Nautilus Instrument
            ts_init = self._clock.timestamp_ns()

            parsed_count = 0
            error_count = 0

            for protobuf_asset in response.assets:
                try:
                    nautilus_instrument = parse_instrument(
                        finam_asset=protobuf_asset,
                        ts_init=ts_init,
                    )

                    # Add to provider cache
                    self.add(nautilus_instrument)
                    parsed_count += 1

                except Exception as e:
                    error_count += 1
                    # Protobuf Asset has 'code' field (not 'symbol')
                    asset_code = getattr(protobuf_asset, 'code', 'UNKNOWN')
                    self._log.error(
                        f"Failed to parse instrument {asset_code}: {e}"
                    )

            self._log.info(
                f"Loaded {self.count} instruments "
                f"(parsed: {parsed_count}, errors: {error_count})"
            )

        except Exception as e:
            self._log.error(f"Failed to load instruments from Finam gRPC API: {e}")
            raise
    
    async def load_ids_async(
        self,
        instrument_ids: list[InstrumentId],
        filters: dict | None = None,
    ) -> None:
        """
        Load specific  insruments by IDs.

        Parameters
        ----------
        insrument_ids : list[InstrumentId]
            The insrument IDs to load
        filters : dict, optional
            Currently not used

        Notes
        -----
        Currently loads ALL instruments and filters locally.
        In future: could use GET /asset?symbol={symbol} fro individual  loading.
        """
        PyCondition.not_none(instrument_ids, "instrument_ids")
        PyCondition.not_empty(instrument_ids, "instrument_ids")

        self._log.info(f"Loading {len(instrument_ids)} instruments...")

        # Временная реализация: загружаем все и фильтруем
        # TODO:  Оптимизировать через GET /asset?symbol={symbol}
        await self.load_all_async(filters)

        # Фильтруем только запрошенные IDs
        requested_symbols = {instrument_id.symbol.value for instrument_id in instrument_ids}

        # Удаляем незапрошенные инструменты
        all_ids = list(self._instruments.keys())
        for instrument_id in all_ids:
            if instrument_id.symbol.value not in requested_symbols:
                del self._instruments[instrument_id]
 
        self._log.info(f"Loaded {self.count} instruments (filtered)")

    async def load_async(
        self,
        instrument_id: InstrumentId,
        filters: dict | None = None,
    ) -> None:
        """
        Load a single instrument by ID.

        Parameters
        ----------
        instrument_id : InstrumentId
            The instrument ID to load
        filters : dict, optional
            Currently not used

        """
        PyCondition.not_none(instrument_id, "instrument_id")

        await self.load_ids_async([instrument_id], filters)
# %%
