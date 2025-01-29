from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import configparser

config = configparser.ConfigParser()
config.read('config.ini')
SQL_DB_USER = config['database']['user']
SQL_DB_PASSWORD = config['database']['password']
SQL_DB_HOST = config['database']['host']
SQL_DB_PORT = config['database']['port']
SQL_DB_NAME = config['database']['database']

SQL_DB_URL = f"postgresql+psycopg2://{SQL_DB_USER}:{SQL_DB_PASSWORD}@{SQL_DB_HOST}:{SQL_DB_PORT}/{SQL_DB_NAME}"
engine = create_engine(SQL_DB_URL)
session_local = sessionmaker(autoflush=False, autocommit=False, bind=engine)
Base = declarative_base()
