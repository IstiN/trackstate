from __future__ import annotations

from typing import Protocol

from testing.core.config.account_by_email_unsupported_cli_config import (
    AccountByEmailUnsupportedCliConfig,
)
from testing.core.models.account_by_email_unsupported_cli_result import (
    AccountByEmailUnsupportedCliObservation,
)


class AccountByEmailUnsupportedCliProbe(Protocol):
    def account_by_email_unsupported(
        self,
        *,
        config: AccountByEmailUnsupportedCliConfig,
    ) -> AccountByEmailUnsupportedCliObservation: ...
