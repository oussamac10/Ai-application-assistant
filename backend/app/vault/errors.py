class VaultError(Exception):
    """Base exception for Profile Vault operations."""


class VaultValidationError(VaultError):
    def __init__(self, message: str, error_code: str = "invalid_vault_value"):
        super().__init__(message)
        self.error_code = error_code


class VaultNotFoundError(VaultError):
    pass
