from __future__ import annotations

from types import TracebackType

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from .sqlalchemy import (
    SqlAlchemyAnalyticsRepository,
    SqlAlchemyChecklistRepository,
    SqlAlchemyConversationStateRepository,
    SqlAlchemyFeedbackRepository,
    SqlAlchemyInvestorRepository,
    SqlAlchemyMeasureRepository,
    SqlAlchemyProfileRepository,
    SqlAlchemyReminderRepository,
)


class RepoBundle:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.profiles = SqlAlchemyProfileRepository(session)
        self.states = SqlAlchemyConversationStateRepository(session)
        self.measures = SqlAlchemyMeasureRepository(session)
        self.checklists = SqlAlchemyChecklistRepository(session)
        self.feedback = SqlAlchemyFeedbackRepository(session)
        self.investors = SqlAlchemyInvestorRepository(session)
        self.analytics = SqlAlchemyAnalyticsRepository(session)
        self.reminders = SqlAlchemyReminderRepository(session)


class SqlAlchemyRepositories:
    def __init__(self, sessionmaker: async_sessionmaker[AsyncSession]) -> None:
        self._sessionmaker = sessionmaker

    def session(self) -> _RepoSession:
        return _RepoSession(self._sessionmaker)


class _RepoSession:
    def __init__(self, sessionmaker: async_sessionmaker[AsyncSession]) -> None:
        self._sessionmaker = sessionmaker
        self._session: AsyncSession | None = None

    async def __aenter__(self) -> RepoBundle:
        self._session = self._sessionmaker()
        return RepoBundle(self._session)

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        if self._session is None:
            return
        if exc_type is None:
            await self._session.commit()
        else:
            await self._session.rollback()
        await self._session.close()


__all__ = [
    "SqlAlchemyAnalyticsRepository",
    "SqlAlchemyChecklistRepository",
    "SqlAlchemyConversationStateRepository",
    "SqlAlchemyFeedbackRepository",
    "SqlAlchemyInvestorRepository",
    "SqlAlchemyMeasureRepository",
    "SqlAlchemyProfileRepository",
    "SqlAlchemyReminderRepository",
    "SqlAlchemyRepositories",
]
