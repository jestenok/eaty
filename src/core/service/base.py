from core.repository import BaseRepository


class BaseService[TRepository: BaseRepository]:
    """Business logic over repositories that are handed in from outside (DI).

    A service never opens, commits or rolls back a transaction: several services
    called in one request share its unit of work and either all succeed or none do.
    """

    def __init__(self, repository: TRepository):
        self.repository = repository
