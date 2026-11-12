"""Palazzetti client configuration"""


class PalazzettiClientConfig:
    """A client configuration.

    Attributes
    ----------
    pellet_quantity_sanitize: bool
        When set to `True` the pellet quantity will be sanitized when updated: it's value will be updated only if it is greater or equal to the previously known value.
    request_timeout: float
        HTTP request timeout in seconds (defaults to 25.0).
    """

    def __init__(
        self,
        pellet_quantity_sanitize: bool = False,
        request_timeout: float = 25.0,
    ) -> None:
        self.pellet_quantity_sanitize: bool = pellet_quantity_sanitize
        self.request_timeout: float = request_timeout
