from fastapi import FastAPI, Path, Query, Depends, HTTPException, Response
from typing import Annotated, List, Dict
import json

from sqlalchemy import func

from database import Base, engine, session_local
from sqlalchemy.orm import Session, joinedload
from models import Client, Licence, Object, Service, History
from datetime import datetime
from schemas import LicenceResponse, LicenceCreate, ClientResponse, ClientCreate, ClientEdit, ObjectResponse, \
    ObjectCreate, \
    ServiceResponse, ServiceCreate, HistoryResponse
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


@app.get('/general-statistics', response_model=Dict)
async def get_general_statistics(id: int = Query(30, title="Amount of days for the forecast", ge=1),
                                 db: Session = Depends(get_db)):
    date_now = datetime.now()
    clients = db.query(Client).filter(Client.id == id).first()
    return {'data': clients}


@app.post('/clients')
async def create_client(client: ClientCreate, db: Session = Depends(get_db)) -> Response:
    max_id = db.query(func.max(Client.id)).scalar()
    if max_id:
        next_id = max_id + 1
    else:
        next_id = 1
    licences = db.query(Licence).filter(Licence.client_id == next_id, Licence.status == 'active').all()
    count_licences = len(licences)
    if count_licences == 0:
        status = 'inactive'
    else:
        status = 'active'
    new_client = Client(nameCompany=client.nameCompany, tin=client.tin, contact=client.contact,
                        email=client.email, num_phone=client.num_phone, status=status,
                        count_licence=count_licences, date_registration=client.date_registration,
                        role=client.role, description=client.description)
    db.add(new_client)
    db.commit()
    db.refresh(new_client)
    client_resp = ClientResponse.from_orm(new_client)
    return Response(content=client_resp.json(), status_code=201, media_type='application/json',
                    headers={"Location": f"/clients/{client_resp.id}"})


@app.get('/clients/{client_id}')
async def get_client(client_id: int, db: Session = Depends(get_db)) -> Response:
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
        'status': client.status.value,
        'count_licence': client.count_licence,
        'date_registration': client.date_registration.isoformat(),
        'description': client.description,
        'role': client.role,
        'objects': client.objects
    }

    return Response(content=json.dumps(data), status_code=200, media_type='application/json')


@app.put('/clients/{client_id}')
async def edit_client(client_id: int, client: ClientCreate, db: Session = Depends(get_db)) -> Response:
    cur_client = db.query(Client).filter(Client.id == client_id).first()
    if not cur_client:
        raise HTTPException(status_code=404, detail='Client not found')
    cur_client.nameCompany = client.nameCompany
    cur_client.tin = client.tin
    cur_client.contact = client.contact
    cur_client.email = client.email
    cur_client.num_phone = client.num_phone
    cur_client.description = client.description
    cur_client.date_registration = client.date_registration
    db.commit()
    db.refresh(cur_client)
    cur_client = ClientResponse.from_orm(cur_client)
    return Response(content=cur_client.json(), status_code=200, media_type='application/json')


@app.delete('/clients/{client_id}')
async def delete_client(client_id: int, db: Session = Depends(get_db)):
    client = db.query(Client).filter(Client.id == client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail='Client not found')
    db.delete(client)
    db.commit()
    return Response(status_code=204)


@app.post('/objects')
async def create_object(object: ObjectCreate, db: Session = Depends(get_db)) -> Response:
    new_object = Object(name=object.name, client_id=object.client_id)
    db.add(new_object)
    db.commit()
    db.refresh(new_object)
    object_resp = ObjectResponse.from_orm(new_object)
    return Response(content=object_resp, status_code=201, media_type='application/json',
                    headers={"Location": f"/objects/{object_resp.id}"})


@app.get('/objects/{object_id}', response_model=Dict)
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


@app.put('/objects/{object_id}')
async def edit_object(object_id: int, object: ObjectCreate, db: Session = Depends(get_db)) -> Response:
    cur_object = db.query(Object).filter(Object.id == object_id).first()
    if not cur_object:
        raise HTTPException(status_code=404, detail='Object not found')
    cur_object.name = object.name
    cur_object.client_id = object.client_id
    db.commit()
    db.refresh(cur_object)
    cur_object = ObjectResponse.from_orm(cur_object)
    return Response(content=cur_object.json(), status_code=200, media_type='application/json')


@app.delete('/objects/{object_id}')
async def delete_object(object_id: int, db: Session = Depends(get_db)):
    object = db.query(Object).filter(Object.id == object_id).first()
    if not object:
        raise HTTPException(status_code=404, detail='Object not found')
    db.delete(object)
    db.commit()
    return Response(status_code=204)


@app.post('/services', response_model=Dict)
async def create_service(service: ServiceCreate, db: Session = Depends(get_db)) -> Dict:
    new_service = Service(name=service.name, object_id=service.object_id)
    db.add(new_service)
    db.commit()
    db.refresh(new_service)
    service_resp = ServiceResponse.from_orm(new_service)
    return {'id': service_resp.id, 'data': service_resp.dict(), 'status_code': 200}


@app.get('/services/{service_id}', response_model=Dict)
async def get_service(service_id: int, db: Session = Depends(get_db)):
    service = db.query(Service).filter(Service.id == service_id).options(joinedload(Service.licences)).first()
    if service is None:
        raise HTTPException(status_code=404, detail="Service not found")
    data = {
        'id': service.id,
        'name': service.name,
        'object_id': service.object_id,
        'licences': service.licences
    }
    return {'id': service_id, 'data': data, "status_code": 200}


@app.put('/services/{service_id}')
async def edit_service(service_id: int, service: ServiceCreate, db: Session = Depends(get_db)) -> Response:
    cur_service = db.query(Service).filter(Service.id == service_id).first()
    if not cur_service:
        raise HTTPException(status_code=404, detail='Service not found')
    cur_service.name = service.name
    cur_service.object_id = service.object_id
    db.commit()
    db.refresh(cur_service)
    cur_service = ServiceResponse.from_orm(cur_service)
    return Response(content=cur_service.json(), status_code=200, media_type='application/json')


@app.delete('/services/{service_id}')
async def delete_service(service_id: int, db: Session = Depends(get_db)):
    service = db.query(Service).filter(Service.id == service_id).first()
    if not service:
        raise HTTPException(status_code=404, detail='Service not found')
    db.delete(service)
    db.commit()
    return Response(status_code=204)


@app.post('/licences', response_model=Dict)
async def create_licence(licence: LicenceCreate, db: Session = Depends(get_db)) -> Dict:
    new_licence = Licence(client_id=licence.client_id, status=licence.status, date_begin=licence.date_begin,
                          date_end=licence.date_end, service_id=licence.service_id)
    db.add(new_licence)
    db.commit()
    db.refresh(new_licence)
    if new_licence.status.value == 'active':
        client = db.query(Client).filter(Client.id == licence.client_id).first()
        if client is not None:
            client.status = 'active'
            client.count_licence += 1
            db.commit()
            db.refresh(client)
    licence_resp = LicenceResponse.from_orm(new_licence)
    return {'id': licence_resp.id, 'data': licence_resp.dict(), 'status_code': 200}


@app.get('/licences/{licence_id}', response_model=Dict)
async def get_licence(licence_id: int, db: Session = Depends(get_db)):
    licence = db.query(Licence).filter(Licence.id == licence_id).first()
    if licence is None:
        raise HTTPException(status_code=404, detail="Licence not found")
    client = db.query(Client).filter(Client.id == licence.client_id).first()
    date_start = licence.date_begin
    date_end = licence.date_end
    changes = db.query(History).filter(History.licence_id == licence_id).all()
    if changes:
        edited_changes = [HistoryResponse.from_orm(change) for change in changes]
    else:
        edited_changes = []
    return {'client': client, 'date_start': date_start, 'date_end': date_end, 'history': edited_changes}


@app.put('/licences/{licence_id}')
async def edit_licence(licence_id: int, licence: LicenceCreate, db: Session = Depends(get_db)) -> Response:
    cur_licence = db.query(Licence).filter(Licence.id == licence_id).first()
    if cur_licence is None:
        raise HTTPException(status_code=404, detail="Licence not found")
    cur_licence.date_begin = licence.date_begin
    cur_licence.date_end = licence.date_end
    cur_licence.service_id = licence.service_id
    cur_licence.status = licence.status
    if cur_licence.status.value == 'active':
        prev_client = db.query(Client).filter(Client.id == cur_licence.client_id).first()
        if prev_client:
            prev_client.count_licence -= 1
            if prev_client.count_licence == 0:
                prev_client.status = 'inactive'
            db.commit()
            db.refresh(prev_client)
        cur_licence.client_id = licence.client_id
        next_client = db.query(Client).filter(Client.id == cur_licence.client_id).first()
        if next_client:
            if next_client.status.value == 'inactive':
                next_client.status = 'active'
            next_client.count_licence += 1
            db.commit()
            db.refresh(next_client)
    else:
        cur_licence.client_id = licence.client_id

    db.commit()
    db.refresh(cur_licence)
    cur_licence = LicenceResponse.from_orm(cur_licence)
    return Response(content=cur_licence.json(), status_code=200, media_type='application/json')


@app.delete('/licences/{licence_id}')
async def delete_licence(licence_id: int, db: Session = Depends(get_db)) -> Response:
    cur_licence = db.query(Licence).filter(Licence.id == licence_id).first()
    if cur_licence is None:
        raise HTTPException(status_code=404, detail="Licence not found")
    if cur_licence.status.value == 'active':
        client = db.query(Client).filter(Client.id == cur_licence.client_id).first()
        if client:
            client.count_licence -= 1
            if client.count_licence == 0:
                client.status = 'inactive'
            db.commit()
            db.refresh(client)
    db.delete(cur_licence)
    db.commit()
    return Response(status_code=204)
