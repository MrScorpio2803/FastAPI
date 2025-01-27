from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

SQL_DB_URL = "postgresql+psycopg2://postgres:MissLisa2803@localhost:5432/postgres"
engine = create_engine(SQL_DB_URL)
session_local = sessionmaker(autoflush=False, autocommit=False, bind=engine)
Base = declarative_base()
