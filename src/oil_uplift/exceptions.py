class OilUpliftError(Exception):
    """Base exception for expected, user-actionable failures."""


class ConfigurationError(OilUpliftError):
    """Raised when configuration is missing or inconsistent."""


class PolicyBlockedError(OilUpliftError):
    """Raised when an unconfirmed official rule blocks an operation."""


class DataContractError(OilUpliftError):
    """Raised when input data violates the configured schema."""


class SubmissionError(OilUpliftError):
    """Raised when a candidate submission violates the official contract."""
