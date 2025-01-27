from sqlalchemy import Column, Integer, String, Enum, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from database import Base
from schemas import Status


class Client(Base):
    __tablename__ = "clients"

    id = Column(Integer, primary_key=True, index=True)
    nameCompany = Column(String, index=True)
    tin = Column(String, index=True)
    contact = Column(String, index=True)
    email = Column(String)
    num_phone = Column(String)
    status = Column(Enum(Status))
    count_licence = Column(Integer)
    date_registration = Column(DateTime)
    description = Column(String)
    role = Column(String)
    objects = relationship('Object', back_populates='client')


class Object(Base):
    __tablename__ = "objects"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    client_id = Column(Integer, ForeignKey('clients.id'))
    client = relationship('Client', back_populates='objects')
    services = relationship('Service', back_populates='object')


class Service(Base):
    __tablename__ = "services"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    object_id = Column(Integer, ForeignKey('objects.id'))
    object = relationship('Object', back_populates='services')
    licences = relationship('Licence', back_populates='service')


class Licence(Base):
    __tablename__ = "licences"

    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(Integer)
    status = Column(Enum(Status))
    date_begin = Column(DateTime, index=True)
    date_end = Column(DateTime, index=True)
    service_id = Column(Integer, ForeignKey('services.id'))
    service = relationship('Service', back_populates='licences')
