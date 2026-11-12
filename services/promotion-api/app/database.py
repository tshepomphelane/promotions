import os

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

DATABASE_URL = os.getenv (
    "DATABASE_URL",
    "postgresql+psycopg://promotion:promotion@localhost:5432/promotions"
)

# set env variables 
DB_POOL_SIZE = int(os.getenv("DB_POOL_SIZE", "5"))
DB_MAX_OVERFLOW = int(os.getenv("DB_MAX_OVERFLOW", "0"))
DB_POOL_TIMEOUT_SECONDS = float(os.getenv("DB_POOL_TIMEOUT_SECONDS", "0.2"))

engine = create_engine (
    DATABASE_URL, 
    pool_size=DB_POOL_SIZE, # allow 5 persistent db connections
    max_overflow=DB_MAX_OVERFLOW, # no additional temp connections
    pool_timeout=DB_POOL_TIMEOUT_SECONDS, # request will not wait for connections
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