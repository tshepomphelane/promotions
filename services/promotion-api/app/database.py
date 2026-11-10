import os

from sqlalchemy import create_engine
from slqalchemy.orm import declarative_base, sessionmaker

DATABASE_URL = os.getenv (
    "DATABASE_URL",
    "postgresql+psycopg://promotion:promotion@localhost:5432/promotions"
)

engine = create_engine (
    DATABASE_URL, 
    pool_size=5, # allow 5 persistent db connections
    max_overflow=0, # no additional temp connections
    pool_timeout=2, # request will not wait for connections
    pool_pre_ping=True, # check connection before using it
)

SessionLocal = sessionmaker (
    autocommit=False,
    autoflush=False,
    bind=engine,
)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close() # return the connection to the pool