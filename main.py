from fastapi import FastAPI, Path, Query, Depends, HTTPException
from typing import Annotated, List, Dict
from database import Base, engine, session_local
from sqlalchemy.orm import Session, joinedload
from models import Client, Licence, Object, Service
from datetime import datetime
from schemas import LicenceResponse, LicenceCreate, ClientResponse, ClientCreate, ObjectResponse, ObjectCreate, \
    ServiceResponse, ServiceCreate
import logging

logger = logging.getLogger(__name__)
app = FastAPI()

Base.metadata.create_all(bind=engine)


def get_db():
    db = session_local()
    try:
        yield db
    finally:
        db.close()


@app.get('/general-statistics')
async def get_general_statistics(id: int = Query(30, title="Amount of days for the forecast", ge=1),
                                 db: Session = Depends(get_db)):
    date_now = datetime.now()
    clients = db.query(Client).filter(Client.id == id).first()
    print(clients)
    return {'data': clients}


@app.post('/clients')
async def create_client(client: ClientCreate, db: Session = Depends(get_db)) -> Dict:
    logger.info("Starting")
    print(1111)
    clients = db.query(Client).all()
    new_client_id = len(clients) + 1
    licences = db.query(Licence).filter(Licence.client_id == new_client_id, Licence.status == 'active').all()
    if len(licences) > 0:
        status = 'active'
    else:
        status = 'inactive'
    print(len(licences))
    print(status)
    new_client = Client(nameCompany=client.nameCompany, tin=client.tin, contact=client.contact,
                        email=client.email, num_phone=client.num_phone, status=status,
                        count_licence=len(licences), date_registration=client.date_registration,
                        role=client.role)
    db.add(new_client)
    db.commit()
    db.refresh(new_client)
    client_resp = ClientResponse.from_orm(new_client)
    return {'id': client_resp.id, 'data': client_resp.dict(), 'status_code': 200}


@app.get('/clients/{client_id}')
async def get_client(client_id: int, db: Session = Depends(get_db)):
    client = db.query(Client).filter(Client.id == client_id).options(joinedload(Client.objects)).first()
    if client is None:
        raise HTTPException(status_code=404, detail="Client not found")
    data = {
        'id': client.id,
        'company': client.nameCompany,
        'tin': client.tin,
        'contact': client.contact,
        'email': client.email,
        'num_phone': client.num_phone,
        'status': client.status,
        'count_licence': client.count_licence,
        'date_registration': client.date_registration,
        'role': client.role,
        'objects': client.objects
    }
    return {'id': client_id, 'data': data, "status_code": 200}


@app.post('/objects')
async def create_object(object: ObjectCreate, db: Session = Depends(get_db)) -> Dict:
    new_object = Object(name=object.name, client_id=object.client_id)
    db.add(new_object)
    db.commit()
    db.refresh(new_object)
    object_resp = ObjectResponse.from_orm(new_object)
    return {'id': object_resp.id, 'data': object_resp.dict(), 'status_code': 200}


@app.get('/objects/{object_id}')
async def get_object(object_id: int, db: Session = Depends(get_db)):
    object = db.query(Object).filter(Object.id == object_id).options(joinedload(Object.services)).first()
    if object is None:
        raise HTTPException(status_code=404, detail="Object not found")
    data = {
        'id': object.id,
        'name': object.name,
        'client_id': object.client_id,
        'services': object.services
    }
    return {'id': object_id, 'data': data, "status_code": 200}

@app.post('/services')
async def create_service(service: ServiceCreate, db: Session = Depends(get_db)) -> Dict:
    new_service = Service(name=service.name, object_id=service.object_id)
    db.add(new_service)
    db.commit()
    db.refresh(new_service)
    service_resp = ServiceResponse.from_orm(new_service)
    return {'id': service_resp.id, 'data': service_resp.dict(), 'status_code': 200}


@app.post('/licences')
async def create_licence(licence: LicenceCreate, db: Session = Depends(get_db)) -> Dict:
    new_licence = Licence(client_id=licence.client_id, status=licence.status, date_begin=licence.date_begin,
                          date_end=licence.date_end, service_id=licence.service_id)
    db.add(new_licence)
    db.commit()
    db.refresh(new_licence)
    licence_resp = LicenceResponse.from_orm(new_licence)
    return {'id': licence_resp.id, 'data': licence_resp.dict(), 'status_code': 200}
