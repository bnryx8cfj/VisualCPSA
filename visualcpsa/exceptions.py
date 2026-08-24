"""Domain-specific exception hierarchy for VisualCPSA."""


class VisualCPSAError(Exception):
    """Base class for recoverable VisualCPSA failures."""


class ConfigurationError(VisualCPSAError):
    """Raised when settings or logging configuration is invalid or inaccessible."""


class PersistenceError(VisualCPSAError):
    """Raised when project persistence fails."""


class ResourceError(VisualCPSAError):
    """Raised when an application resource is missing or unusable."""


class IncompleteModelError(VisualCPSAError):
    """Raised when an operation requires information absent from a draft object."""


class UnresolvedReferenceError(VisualCPSAError):
    """Raised when a model identifier cannot be resolved."""


class ModelInvariantError(VisualCPSAError):
    """Raised when a required model invariant is violated."""


class CPSAExportError(VisualCPSAError):
    """Raised when strict CPSA generation cannot complete."""


class MarkupError(VisualCPSAError):
    """Raised when math-lite markup is malformed."""
