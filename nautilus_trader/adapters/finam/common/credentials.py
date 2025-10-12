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

from pydantic import BaseModel, Field


class FinamCredentials(BaseModel):
    """
    Credentials for Finam API authentication.

    Parameters
    ----------
    secret_token : str
        Secret token from Finam API settings (used to obtain JWT token)
    account_id : str
        Trading account ID

    """

    secret_token: str = Field(
        ...,
        description="Secret token for JWT authentication",
        min_length=1,
    )
    account_id: str = Field(
        ...,
        description="Trading account identifier",
        min_length=1,
    )

    class Config:
        """Pydantic configuration."""

        frozen = True  # Make immutable
        extra = "forbid"  # Forbid extra fields