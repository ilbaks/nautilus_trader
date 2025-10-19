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
Tests for Finam configuration classes.
"""

import pytest

from nautilus_trader.adapters.finam.config import (
    FinamDataClientConfig,
    FinamExecClientConfig,
)


class TestFinamDataClientConfig:
    """Tests for FinamDataClientConfig."""

    def test_finam_data_client_config_defaults(self):
        """
        Test that FinamDataClientConfig has correct default values.
        """
        # Arrange, Act
        config = FinamDataClientConfig(
            client_id="TEST_CLIENT",
            access_token="test_token_123",
        )

        # Assert
        assert config.client_id == "TEST_CLIENT"
        assert config.access_token == "test_token_123"
        assert config.account_id is None
        assert config.grpc_host == "trade-api.finam.ru"
        assert config.grpc_port == 443
        assert config.use_ssl is True
        assert config.rate_limit_requests == 100
        assert config.rate_limit_window == 60.0
        assert config.auto_refresh_token is True
        assert config.update_instruments_interval_mins == 60

    def test_finam_data_client_config_custom_values(self):
        """
        Test that FinamDataClientConfig accepts custom values.
        """
        # Arrange, Act
        config = FinamDataClientConfig(
            client_id="CUSTOM_CLIENT",
            access_token="custom_token",
            account_id="12345678",
            grpc_host="custom-host.finam.ru",
            grpc_port=9443,
            use_ssl=False,
            rate_limit_requests=50,
            rate_limit_window=30.0,
            auto_refresh_token=False,
            update_instruments_interval_mins=30,
        )

        # Assert
        assert config.client_id == "CUSTOM_CLIENT"
        assert config.access_token == "custom_token"
        assert config.account_id == "12345678"
        assert config.grpc_host == "custom-host.finam.ru"
        assert config.grpc_port == 9443
        assert config.use_ssl is False
        assert config.rate_limit_requests == 50
        assert config.rate_limit_window == 30.0
        assert config.auto_refresh_token is False
        assert config.update_instruments_interval_mins == 30

    def test_finam_data_client_config_immutable(self):
        """
        Test that FinamDataClientConfig is immutable (frozen).
        """
        # Arrange
        config = FinamDataClientConfig(
            client_id="TEST_CLIENT",
            access_token="test_token",
        )

        # Act, Assert
        with pytest.raises(Exception):  # FrozenInstanceError or AttributeError
            config.grpc_host = "evil-host.com"


class TestFinamExecClientConfig:
    """Tests for FinamExecClientConfig."""

    def test_finam_exec_client_config_defaults(self):
        """
        Test that FinamExecClientConfig has correct default values.
        """
        # Arrange, Act
        config = FinamExecClientConfig(
            client_id="EXEC_CLIENT",
            access_token="exec_token_123",
            account_id="87654321",
        )

        # Assert
        assert config.client_id == "EXEC_CLIENT"
        assert config.access_token == "exec_token_123"
        assert config.account_id == "87654321"
        assert config.grpc_host == "trade-api.finam.ru"
        assert config.grpc_port == 443
        assert config.use_ssl is True
        assert config.rate_limit_requests == 100
        assert config.rate_limit_window == 60.0
        assert config.auto_refresh_token is True

    def test_finam_exec_client_config_custom_values(self):
        """
        Test that FinamExecClientConfig accepts custom values.
        """
        # Arrange, Act
        config = FinamExecClientConfig(
            client_id="CUSTOM_EXEC",
            access_token="custom_exec_token",
            account_id="11223344",
            grpc_host="custom-exec.finam.ru",
            grpc_port=8443,
            use_ssl=False,
            rate_limit_requests=25,
            rate_limit_window=15.0,
            auto_refresh_token=False,
        )

        # Assert
        assert config.client_id == "CUSTOM_EXEC"
        assert config.access_token == "custom_exec_token"
        assert config.account_id == "11223344"
        assert config.grpc_host == "custom-exec.finam.ru"
        assert config.grpc_port == 8443
        assert config.use_ssl is False
        assert config.rate_limit_requests == 25
        assert config.rate_limit_window == 15.0
        assert config.auto_refresh_token is False

    def test_finam_exec_client_config_immutable(self):
        """
        Test that FinamExecClientConfig is immutable (frozen).
        """
        # Arrange
        config = FinamExecClientConfig(
            client_id="EXEC_CLIENT",
            access_token="exec_token",
            account_id="12345678",
        )

        # Act, Assert
        with pytest.raises(Exception):  # FrozenInstanceError or AttributeError
            config.account_id = "99999999"
