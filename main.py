from fastapi import FastAPI, Path, Query, Depends, HTTPException, Response
from typing import Annotated, List, Dict, Optional
import json

from sqlalchemy import func, select

from database import Base, engine, session_local
from sqlalchemy.orm import Session, joinedload
from models import Client, Licence, Object, Service, History, Note, ClientEdits
from datetime import datetime, timedelta
from publisher import send_license_expiration_notification

from schemas import LicenceResponse, LicenceCreate, ClientResponse, ClientCreate, NoteCreate, NoteResponse, \
    ObjectResponse, \
    ObjectCreate, \
    ServiceResponse, ServiceCreate, HistoryResponse, Status, EditsResponse, LicenseInfo
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


def get_active_licenses_count(db_session, start_date, end_date, period: str):
    query = db_session.query(
        func.count(Licence.id).label('count_licences_count')
    ).filter(
        Licence.status == 'active',
        Licence.date_begin >= start_date,
        Licence.date_end <= end_date
    ).group_by(
        func.date_trunc(period, Licence.date_begin)
    ).all()

    return query


def get_new_clients(db_session, start_date, end_date, period: str):
    query = db_session.query(
        func.count(Client.id).label('count_new_clients')
    ).filter(
        Client.date_registration >= start_date,
        Client.date_registration <= end_date
    ).group_by(
        func.date_trunc(period, Client.date_registration)
    ).all()

    return query


def edit_licences(array):
    for licence in array:
        licence.date_end = licence.date_end.isoformat()
        licence.date_begin = licence.date_begin.isoformat()
        licence.status = licence.status.value
    return array

@app.get('/general-statistics')
async def get_general_statistics(period: str = Query('week', title="Period of search"),
                                 start_date: datetime = Query(datetime.now(), example="2025-01-01T00:00:00"),
                                 db: Session = Depends(get_db)) -> Response:
    translate = {
        'day': 1,
        'week': 7,
        'month': 30,
        'year': 366
    }
    days_check = translate[period]
    date_now = datetime.now()
    month = date_now.month
    licences_active = db.query(Licence).filter(Licence.date_end >= date_now, Licence.status == 'active').all()
    licences_list = [LicenceResponse.from_orm(licence) for licence in licences_active]
    licences_list = edit_licences(licences_list)
    count_active_licences = len(licences_list)
    licence_inactive = db.query(Licence).filter(Licence.date_end >= date_now, Licence.status == 'inactive').all()
    licences_list_inactive = [LicenceResponse.from_orm(licence) for licence in licence_inactive]
    licences_list_inactive = edit_licences(licences_list_inactive)
    count_inactive_licences = len(licences_list_inactive)
    licences_expiring = db.query(Licence).filter(func.extract('month', Licence.date_end) == month and Licence.date_end >= date_now).all()
    licences_list_expiring = [LicenceResponse.from_orm(licence) for licence in licences_expiring]
    licences_list_expiring = edit_licences(licences_list_expiring)
    count_expiring_licences = len(licences_list_expiring)
    licences_expired = db.query(Licence).filter(Licence.date_end < date_now).all()
    licences_list_expired = [LicenceResponse.from_orm(licence) for licence in licences_expired]
    licences_list_expired = edit_licences(licences_list_expired)
    count_expired_licences = len(licences_list_expired)
    end_date_check = start_date + timedelta(days=days_check)
    start_date_check = start_date
    licenses_count = get_active_licenses_count(db, start_date_check, end_date_check, period)
    counts = [licence_count.count_licences_count for licence_count in licenses_count]
    changes = []
    for i in range(1, len(counts)):
        change = counts[i] - counts[i - 1]
        changes.append(change)
    date_check = datetime.now() + timedelta(days=days_check)
    clients_count = get_new_clients(db, start_date_check, end_date_check, period)
    changes_clients = []
    for i in range(1, len(clients_count)):
        changes_client = clients_count[i] - clients_count[i - 1]
        changes_clients.append(changes_client)
    licence_inactive_expiring_soon = db.query(Licence).filter(Licence.date_end >= date_now, Licence.date_end <= date_check).all()
    licences_list_expiring_soon = [LicenceResponse.from_orm(licence) for licence in licence_inactive_expiring_soon]
    licences_list_expiring_soon = edit_licences(licences_list_expiring_soon)
    licences_expiring_soon = [licence.dict() for licence in licences_list_expiring_soon]
    data = {
        'amount_active_licences': count_active_licences,
        'amount_inactive_licences': count_inactive_licences,
        'amount_expiring_licences': count_expiring_licences,
        'amount_expired_licences': count_expired_licences,
        'graphic_licence': counts,
        'graghic_clients': clients_count,
        'table_expiring_licences_soon': licences_expiring_soon
    }
    return Response(content=json.dumps(data), status_code=200, media_type='application/json')


@app.get('/last-activities')
async def get_last_activities(db: Session = Depends(get_db)) -> Response:
    check_date = datetime.now() - timedelta(days=5)
    activate_licences = db.query(History).filter(History.next_status == Status['active'], History.date >= check_date).all()
    activate_licences = [HistoryResponse.from_orm(licence) for licence in activate_licences]
    inactivate_licences = db.query(History).filter(History.next_status == Status['inactive'], History.date >= check_date).all()
    inactivate_licences = [HistoryResponse.from_orm(licence) for licence in inactivate_licences]
    new_clients = db.query(Client).filter(Client.date_registration >= check_date).all()
    new_clients = [ClientResponse.from_orm(client) for client in new_clients]
    recent_clients_edits = db.query(ClientEdits).filter(ClientEdits.date >= check_date).all()
    recent_clients_edits = [EditsResponse.from_orm(edit) for edit in recent_clients_edits]
    activate_licences_list = [{'client': history.client_id, 'date': history.date.isoformat()} for history in activate_licences]
    inactivate_licences_list = [{'client': history.client_id, 'date': history.date.isoformat()} for history in inactivate_licences]
    new_clients_list = [{'client_id': client.id, 'date_registration': client.date_registration.isoformat()} for client in new_clients]
    recent_clients_edits_list = [{'client_id': edit.client_id, 'edit_date': edit.date.isoformat()} for edit in recent_clients_edits]
    data = {
        'recent_edits': recent_clients_edits_list,
        'activation_licences': activate_licences_list,
        'inactivation_licences': inactivate_licences_list,
        'recent_clients': new_clients_list
    }
    return Response(content=json.dumps(data), status_code=200, media_type='application/json')
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
                        role=client.role)
    db.add(new_client)
    db.commit()
    db.refresh(new_client)
    client_resp = ClientResponse.from_orm(new_client)
    return Response(content=client_resp.json(), status_code=201, media_type='application/json',
                    headers={"Location": f"/clients/{client_resp.id}"})


@app.post('/clients/note')
async def create_note(note: NoteCreate, db: Session = Depends(get_db)) -> Response:
    new_note = Note(client_id=note.client_id, name=note.name, text=note.text)
    db.add(new_note)
    db.commit()
    db.refresh(new_note)
    note_resp = NoteResponse.from_orm(new_note)
    return Response(content=note_resp.json(), status_code=201, media_type='application/json',
                    headers={"Location": f"/clients/{note_resp.client_id}"})


@app.get('/clients/{client_id}')
async def get_client(client_id: int, db: Session = Depends(get_db)) -> Response:
    client = db.query(Client).filter(Client.id == client_id).options(joinedload(Client.objects)).first()
    if client is None:
        raise HTTPException(status_code=404, detail="Client not found")
    licences = db.query(Licence).filter(Licence.client_id == client_id).all()
    licence_list = [LicenceResponse.from_orm(licence) for licence in licences]
    notes = db.query(Note).filter(Note.client_id == client_id).all()
    notes_list = [NoteResponse.from_orm(note).dict() for note in notes]
    query = select(Client.contact).where(client.nameCompany == Client.nameCompany)
    contacts = db.execute(query).scalars().all()
    final_history = []
    if len(licence_list) != 0:
        for licence in licence_list:
            histories = db.query(History).filter(History.client_id == client_id, History.licence_id == licence.id).all()
            print(123)
            histories_list = [HistoryResponse.from_orm(history) for history in histories]
            print(456)
            history_dict = {'licence_id': licence.id, 'history': []}
            for history in histories_list:
                prev_status = history.prev_status
                next_status = history.next_status
                date = history.date

                result = {
                    'next_status': next_status.value,
                    'prev_status': prev_status.value,
                    'date': date.isoformat(),
                }
                history_dict['history'].append(result)
            final_history.append(history_dict)
    licences_json = [licence.dict() for licence in licence_list]

    for licence in licences_json:
        licence['status'] = licence['status'].value
        licence['date_begin'] = licence['date_begin'].isoformat()
        licence['date_end'] = licence['date_end'].isoformat()
    data = {
        'id': client.id,
        'company': client.nameCompany,
        'tin': client.tin,
        'contact': contacts,
        'email': client.email,
        'num_phone': client.num_phone,
        'status': client.status.value,
        'count_licence': client.count_licence,
        'date_registration': client.date_registration.isoformat(),
        'role': client.role,
        'licences': licences_json,
        'history': final_history,
        'notes': notes_list
    }

    return Response(content=json.dumps(data), status_code=200, media_type='application/json')


@app.get('/companies')
async def get_clients(db: Session = Depends(get_db)) -> Response:
    query = select(Client.nameCompany, Client.tin).distinct()
    companies = db.execute(query).fetchall()
    companies_list = [(row.nameCompany, row.tin) for row in companies]
    result = []
    for data in companies_list:
        combined_data = {
            'company': data[0],
            'tin': data[1],
        }
        result.append(combined_data)
    data = {
        'companies': result
    }

    return Response(content=json.dumps(data), status_code=200, media_type='application/json')


@app.get('/searchClients')
async def get_searched_clients(company: Optional[str] = None, tin: Optional[str] = None, contact: Optional[str] = None,
                               db: Session = Depends(get_db)) -> Response:
    query = db.query(Client).options(joinedload(Client.notes))
    if company:
        query = query.filter(Client.nameCompany.ilike(f"%{company}%"))
    if tin:
        query = query.filter(Client.tin.ilike(f"%{tin}%"))
    if contact:
        query = query.filter(Client.contact.ilike(f"%{contact}%"))
    Clients = query.all()
    client_list = [ClientResponse.from_orm(client).dict() for client in Clients]
    for client in client_list:
        client['date_registration'] = client['date_registration'].isoformat()
    if len(client_list) > 0:
        data = {
            'clients': client_list
        }
        return Response(content=json.dumps(data), status_code=200, media_type='application/json')
    else:
        data = {
            'message': 'Not users for your request'
        }
        return Response(content=json.dumps(data), status_code=404, media_type='application/json')


@app.get('/searchLicences')
async def get_searched_licence(client_id: Optional[int] = None, status: Optional[str] = None, date_end: Optional[str] = None,
                               db: Session = Depends(get_db)) -> Response:
    date_end_edit = datetime.strptime(date_end, "%Y-%m-%dT%H:%M:%S.%f")
    query = db.query(Licence)
    if client_id:
        query = query.filter(Licence.client_id == client_id)
    if status:
        query = query.filter(Licence.status == Status[status])
    if date_end:
        query = query.filter(Licence.date_end == date_end_edit)
    Licences = query.all()
    licence_list = [LicenceResponse.from_orm(licence) for licence in Licences]
    for licence in licence_list:

        licence.status = licence.status.value
        licence.date_end = licence.date_end.isoformat()
        licence.date_begin = licence.date_begin.isoformat()
    licence_json = [licence.dict() for licence in licence_list]
    if len(licence_list) > 0:
        data = {
            'licences': licence_json
        }
        return Response(content=json.dumps(data), status_code=200, media_type='application/json')
    else:
        data = {
            'message': 'Not users for your request'
        }
        return Response(content=json.dumps(data), status_code=404, media_type='application/json')


@app.get('/objects')
async def get_objects(db: Session = Depends(get_db)) -> Response:
    query = select(Client.id)
    ids = db.execute(query).scalars().all()
    result = []
    for obj_id in ids:
        objects = db.query(Object).filter(Object.client_id == obj_id).options(joinedload(Object.services))
        obj_list = {obj_id: []}
        for obj in objects:
            services_list = [ServiceResponse.from_orm(service).dict() for service in obj.services]
            obj_cur = {
                'object_id': obj.id,
                'name': obj.name,
                'services': services_list
            }
            obj_list[obj_id].append(obj_cur)
        result.append(obj_list)
    data = {
        'objects': result
    }
    return Response(content=json.dumps(data), status_code=200, media_type='application/json')


@app.get('/services')
async def get_services(db: Session = Depends(get_db)) -> Response:
    query = select(Client.id)
    ids = db.execute(query).scalars().all()
    result = []
    for obj_id in ids:
        objects = db.query(Object).filter(Object.client_id == obj_id).options(joinedload(Object.services))
        service_list = {obj_id: []}
        for obj in objects:
            services_list = [ServiceResponse.from_orm(service).dict() for service in obj.services]
            service_list[obj_id] = services_list
        result.append(service_list)
    data = {
        'objects': result
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
    cur_client.date_registration = client.date_registration
    cur_client.role = client.role
    new_edit = ClientEdits(client_id=client_id, date=datetime.now())
    db.add(new_edit)
    db.commit()
    db.refresh(cur_client)
    db.refresh(new_edit)
    cur_client = ClientResponse.from_orm(cur_client)
    return Response(content=cur_client.json(), status_code=200, media_type='application/json')


@app.delete('/clients/{client_id}')
async def delete_client(client_id: int, db: Session = Depends(get_db)) -> Response:
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
    return Response(content=object_resp.json(), status_code=201, media_type='application/json',
                    headers={"Location": f"/objects/{object_resp.id}"})


@app.get('/objects/{object_id}')
async def get_object(object_id: int, db: Session = Depends(get_db)) -> Response:
    obj = db.query(Object).filter(Object.id == object_id).options(joinedload(Object.services)).first()
    if obj is None:
        raise HTTPException(status_code=404, detail="Object not found")
    services_list = [ServiceResponse.from_orm(service).dict() for service in obj.services]
    data = {
        'id': obj.id,
        'name': obj.name,
        'client_id': obj.client_id,
        'services': services_list
    }
    return Response(content=json.dumps(data), status_code=200, media_type='application/json')


@app.put('/objects/{object_id}')
async def edit_object(object_id: int, obj: ObjectCreate, db: Session = Depends(get_db)) -> Response:
    cur_object = db.query(Object).filter(Object.id == object_id).first()
    if not cur_object:
        raise HTTPException(status_code=404, detail='Object not found')
    cur_object.name = obj.name
    cur_object.client_id = obj.client_id
    db.commit()
    db.refresh(cur_object)
    cur_object = ObjectResponse.from_orm(cur_object)
    return Response(content=cur_object.json(), status_code=200, media_type='application/json')


@app.delete('/objects/{object_id}')
async def delete_object(object_id: int, db: Session = Depends(get_db)) -> Response:
    obj = db.query(Object).filter(Object.id == object_id).first()
    if not obj:
        raise HTTPException(status_code=404, detail='Object not found')
    db.delete(obj)
    db.commit()
    return Response(status_code=204)


@app.post('/services')
async def create_service(service: ServiceCreate, db: Session = Depends(get_db)) -> Response:
    new_service = Service(name=service.name, object_id=service.object_id)
    db.add(new_service)
    db.commit()
    db.refresh(new_service)
    service_resp = ServiceResponse.from_orm(new_service)
    return Response(content=service_resp.json(), status_code=201, media_type='application/json',
                    headers={"Location": f"/services/{service_resp.id}"})


@app.get('/services/{service_id}')
async def get_service(service_id: int, db: Session = Depends(get_db)) -> Response:
    service = db.query(Service).filter(Service.id == service_id).options(joinedload(Service.licences)).first()
    if service is None:
        raise HTTPException(status_code=404, detail="Service not found")
    licences_list = [LicenceResponse.from_orm(licence).dict() for licence in service.licences]
    for licence in licences_list:
        licence['status'] = licence['status'].value
        licence['date_begin'] = licence['date_begin'].isoformat()
        licence['date_end'] = licence['date_end'].isoformat()

    data = {
        'id': service.id,
        'name': service.name,
        'object_id': service.object_id,
        'licences': licences_list
    }
    return Response(content=json.dumps(data), status_code=200, media_type='application/json')


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
async def delete_service(service_id: int, db: Session = Depends(get_db)) -> Response:
    service = db.query(Service).filter(Service.id == service_id).first()
    if not service:
        raise HTTPException(status_code=404, detail='Service not found')
    db.delete(service)
    db.commit()
    return Response(status_code=204)


@app.post('/licences')
async def create_licence(licence: LicenceCreate, db: Session = Depends(get_db)) -> Response:
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
    return Response(content=licence_resp.json(), status_code=201, media_type='application/json',
                    headers={"Location": f"/licences/{licence_resp.id}"})


@app.get('/licences/{licence_id}')
async def get_licence(licence_id: int, db: Session = Depends(get_db)) -> Response:
    licence = db.query(Licence).filter(Licence.id == licence_id).first()
    if licence is None:
        raise HTTPException(status_code=404, detail="Licence not found")
    client = db.query(Client).filter(Client.id == licence.client_id).first()

    date_start = licence.date_begin
    date_end = licence.date_end
    changes = db.query(History).filter(History.licence_id == licence_id).all()
    if changes:
        edited_changes = [HistoryResponse.from_orm(change).dict() for change in changes]
    else:
        edited_changes = []
    data = {
        'client': ClientResponse.from_orm(client).dict() if client is not None else None,
        'date_start': date_start.isoformat(),
        'date_end': date_end.isoformat(),
        'edited_changes': edited_changes
    }
    return Response(content=json.dumps(data), status_code=200, media_type='application/json')


@app.get('/licence')
async def get_licences(db: Session = Depends(get_db)) -> Response:
    licences = db.query(Licence).all()
    licences_list = [LicenceResponse.from_orm(licence) for licence in licences]
    for licence in licences_list:
        licence.status = licence.status.value
        licence.date_end = licence.date_end.isoformat()
        licence.date_begin = licence.date_begin.isoformat()
    licence_json = [licence.dict() for licence in licences_list]
    data = {
        'licences': licence_json
    }
    return Response(content=json.dumps(data), status_code=200, media_type='application/json')

@app.put('/licences/{licence_id}')
async def edit_licence(licence_id: int, licence: LicenceCreate, db: Session = Depends(get_db)) -> Response:
    cur_licence = db.query(Licence).filter(Licence.id == licence_id).first()
    if cur_licence is None:
        raise HTTPException(status_code=404, detail="Licence not found")
    cur_licence.date_begin = licence.date_begin
    cur_licence.date_end = licence.date_end
    cur_licence.service_id = licence.service_id
    if cur_licence.status != licence.status or cur_licence.client_id != licence.client_id:
        if cur_licence.client_id == licence.client_id:
            if cur_licence.status != licence.status:
                client = db.query(Client).filter(Client.id == cur_licence.client_id).first()
                if client:
                    new_history_entry = History(
                        licence_id=licence_id,
                        prev_status=cur_licence.status,
                        next_status=licence.status,
                        date=datetime.now().isoformat(),
                        client_id=licence.client_id,
                    )
                    db.add(new_history_entry)
                    db.commit()
                    db.refresh(new_history_entry)
                    if licence.status.value == 'active':
                        client.count_licence += 1
                        client.status = 'active'
                        db.commit()
                        db.refresh(client)
                    else:
                        client.count_licence -= 1
                        if client.count_licence == 0:
                            client.status = 'inactive'
                        db.commit()
                        db.refresh(client)
        else:
            cur_client = db.query(Client).filter(Client.id == cur_licence.client_id).first()
            new_client = db.query(Client).filter(Client.id == licence.client_id).first()
            if cur_licence.status != licence.status:
                if licence.status.value == 'active':
                    if new_client:
                        new_client.count_licence += 1
                        new_client.status = 'active'
                        db.commit()
                        db.refresh(new_client)
                else:
                    if cur_client:
                        cur_client.count_licence -= 1
                        if cur_client.count_licence == 0:
                            cur_client.status = 'inactive'
                        db.commit()
                        db.refresh(cur_client)
            else:
                if licence.status.value == 'active':
                    if new_client:
                        new_client.count_licence += 1
                        new_client.status = 'active'
                        db.commit()
                        db.refresh(new_client)
                    if cur_client:
                        cur_client.count_licence -= 1
                        if cur_client.count_licence == 0:
                            cur_client.status = 'inactive'
                        db.commit()
                        db.refresh(cur_client)

    cur_licence.status = licence.status
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
            if client.count_licence != 0:
                client.count_licence -= 1
            if client.count_licence == 0:
                client.status = 'inactive'
            db.commit()
            db.refresh(client)
    db.delete(cur_licence)
    db.commit()
    return Response(status_code=204)


@app.post("/notify_expiration/")
async def notify_expiration(license_info: LicenseInfo):
    try:
        # Публикуем сообщение о сроке действия лицензии
        send_license_expiration_notification(license_info.dict())
        return {"message": "Notification sent successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

