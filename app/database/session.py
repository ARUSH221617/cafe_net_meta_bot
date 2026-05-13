from collections.abc import Generator

from sqlmodel import Session, create_engine

from app.core.config import Settings, get_settings


def build_engine(settings: Settings | None = None):
    active_settings = settings or get_settings()
    connect_args = {"check_same_thread": False} if active_settings.database_url.startswith("sqlite") else {}
    return create_engine(active_settings.database_url, echo=False, connect_args=connect_args)


engine = build_engine()


def get_session() -> Generator[Session, None, None]:
    with Session(engine) as session:
        yield session
