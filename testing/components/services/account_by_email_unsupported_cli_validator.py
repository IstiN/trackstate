from __future__ import annotations

from testing.core.config.account_by_email_unsupported_cli_config import (
    AccountByEmailUnsupportedCliConfig,
)
from testing.core.interfaces.account_by_email_unsupported_cli_probe import (
    AccountByEmailUnsupportedCliProbe,
)
from testing.core.models.account_by_email_unsupported_cli_result import (
    AccountByEmailUnsupportedCliValidationResult,
)


class AccountByEmailUnsupportedCliValidator:
    def __init__(self, probe: AccountByEmailUnsupportedCliProbe) -> None:
        self._probe = probe

    def validate(
        self,
        *,
        config: AccountByEmailUnsupportedCliConfig,
    ) -> AccountByEmailUnsupportedCliValidationResult:
        return AccountByEmailUnsupportedCliValidationResult(
            account_by_email_unsupported=self._probe.account_by_email_unsupported(
                config=config
            ),
        )
