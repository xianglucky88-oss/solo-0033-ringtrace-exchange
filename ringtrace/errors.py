class DomainError(Exception):
    """A request rejected with a stable machine code and a Chinese explanation."""

    def __init__(self, code, message, status=400):
        super().__init__(message)
        self.code = code
        self.status = status
