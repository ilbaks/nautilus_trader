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


class JwtTokenResponse(BaseModel):
    """Response from POST /sessions endpoint."""

    token: str = Field(..., description="JWT token for authentication")


class TokenDetailsResponse(BaseModel):
    """Response from POST /sessions/details endpoint."""

    account_id: str = Field(..., description="Account ID associated with token")
    expires_at: str = Field(..., description="Token expiration timestamp (ISO 8601)")
    scopes: list[str] = Field(default_factory=list, description="Access scopes")