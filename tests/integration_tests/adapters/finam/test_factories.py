# -------------------------------------------------------------------------------------------------
#  Copyright (C) 2015-2025 Nautech Systems Pty Ltd. All rights reserved.
#  https://nautechsystems.io
#
#  Licensed under the GNU Lesser General Public License Version 3.0 (the "License");
#  You may not use this file except in compliance with the License at https://www.gnu.org/licenses/lgpl-3.0.en.html
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
# -------------------------------------------------------------------------------------------------

"""
Tests for Finam factory classes.
"""

import os

import pytest

from nautilus_trader.adapters.finam.config import (
    FinamDataClientConfig,
    FinamExecClientConfig,
)
from nautilus_trader.adapters.finam.factories import (
    FinamLiveDataClientFactory,
    FinamLiveExecClientFactory,
    get_access_token,
    get_account_id,
)


class TestFinamHelperFunctions:
    """Tests for helper functions in factories module."""

    def test_get_access_token_explicit(self):
        """
        Test get_access_token with explicitly provided token.
        """
        # Arrange
        token = "explicit_token_abc123"

        # Act
        result = get_access_token(access_token=token)

        # Assert
        assert result == token

    def test_get_access_token_from_env(self, monkeypatch):
        """
        Test get_access_token from environment variable.
        """
        # Arrange
        expected_token = "env_token_xyz789"
        monkeypatch.setenv("FINAM_SECRET_TOKEN", expected_token)

        # Act
        result = get_access_token(access_token=None)

        # Assert
        assert result == expected_token

    def test_get_access_token_missing_raises_error(self, monkeypatch):
        """
        Test get_access_token raises error when token not provided.
        """
        # Arrange
        monkeypatch.delenv("FINAM_SECRET_TOKEN", raising=False)

        # Act, Assert
        with pytest.raises(ValueError, match="FINAM_SECRET_TOKEN"):
            get_access_token(access_token=None)

    def test_get_account_id_explicit(self):
        """
        Test get_account_id with explicitly provided ID.
        """
        # Arrange
        account_id = "12345678"

        # Act
        result = get_account_id(account_id=account_id)

        # Assert
        assert result == account_id

    def test_get_account_id_from_env(self, monkeypatch):
        """
        Test get_account_id from environment variable.
        """
        # Arrange
        expected_id = "87654321"
        monkeypatch.setenv("FINAM_ACCOUNT_ID", expected_id)

        # Act
        result = get_account_id(account_id=None)

        # Assert
        assert result == expected_id

    def test_get_account_id_missing_raises_error(self, monkeypatch):
        """
        Test get_account_id raises error when ID not provided.
        """
        # Arrange
        monkeypatch.delenv("FINAM_ACCOUNT_ID", raising=False)

        # Act, Assert
        with pytest.raises(ValueError, match="FINAM_ACCOUNT_ID"):
            get_account_id(account_id=None)


class TestFinamLiveDataClientFactory:
    """Tests for FinamLiveDataClientFactory."""

    def test_finam_live_data_client_factory_initialization(self):
        """
        Test that FinamLiveDataClientFactory can be initialized.
        """
        # Arrange
        config = FinamDataClientConfig(
            client_id="DATA_FACTORY_TEST",
            access_token="test_token",
        )

        # Act
        factory = FinamLiveDataClientFactory(
            name="FINAM",
            config=config,
            msgbus=None,  # Would be MessageBus in real usage
            cache=None,  # Would be Cache in real usage
            clock=None,  # Would be Clock in real usage
        )

        # Assert
        assert factory is not None
        assert factory.name == "FINAM"

    def test_finam_live_data_client_factory_repr(self):
        """
        Test FinamLiveDataClientFactory __repr__.
        """
        # Arrange
        config = FinamDataClientConfig(
            client_id="DATA_FACTORY_TEST",
            access_token="test_token",
        )

        factory = FinamLiveDataClientFactory(
            name="FINAM",
            config=config,
            msgbus=None,
            cache=None,
            clock=None,
        )

        # Act
        result = repr(factory)

        # Assert
        assert "FinamLiveDataClientFactory" in result


class TestFinamLiveExecClientFactory:
    """Tests for FinamLiveExecClientFactory."""

    def test_finam_live_exec_client_factory_initialization(self):
        """
        Test that FinamLiveExecClientFactory can be initialized.
        """
        # Arrange
        config = FinamExecClientConfig(
            client_id="EXEC_FACTORY_TEST",
            access_token="test_exec_token",
            account_id="12345678",
        )

        # Act
        factory = FinamLiveExecClientFactory(
            name="FINAM",
            config=config,
            msgbus=None,  # Would be MessageBus in real usage
            cache=None,  # Would be Cache in real usage
            clock=None,  # Would be Clock in real usage
        )

        # Assert
        assert factory is not None
        assert factory.name == "FINAM"

    def test_finam_live_exec_client_factory_repr(self):
        """
        Test FinamLiveExecClientFactory __repr__.
        """
        # Arrange
        config = FinamExecClientConfig(
            client_id="EXEC_FACTORY_TEST",
            access_token="test_exec_token",
            account_id="87654321",
        )

        factory = FinamLiveExecClientFactory(
            name="FINAM",
            config=config,
            msgbus=None,
            cache=None,
            clock=None,
        )

        # Act
        result = repr(factory)

        # Assert
        assert "FinamLiveExecClientFactory" in result
