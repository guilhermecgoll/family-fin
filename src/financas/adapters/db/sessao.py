from sqlalchemy import Engine, create_engine


def criar_engine(url: str) -> Engine:
    return create_engine(url, pool_pre_ping=True)
