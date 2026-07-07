class DeriveCadError(Exception):
    """Base class for errors that should be shown to the user as a clean message,
    not a raw Python traceback."""


class ConfigError(DeriveCadError):
    pass


class SecretsError(DeriveCadError):
    pass


class GenerationError(DeriveCadError):
    """Raised when a build123d script fails to execute or times out."""


class ExportError(DeriveCadError):
    pass
