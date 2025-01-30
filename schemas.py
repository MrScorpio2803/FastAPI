from pydantic import BaseModel, EmailStr
from typing import Optional, Annotated, List, Dict
from datetime import datetime
from fastapi import Path
import enum


class Status(enum.Enum):
    active = 'active'
    inactive = 'inactive'


class BaseStruct(BaseModel):
    name: Annotated[str, "name for items of models created bases on this class."]


class ClientBase(BaseModel):
    nameCompany: Annotated[str, Path(title="The name of the company of this client")]
    tin: Annotated[str, Path(title="The tin of the company of this client", min_length=10, max_length=10)]
    contact: Annotated[str, Path(title="The contact person of the company of this company")]
    email: Annotated[EmailStr, Path(title="The email of the contact person of this company")]
    num_phone: Annotated[
        str, Path(title="The phone of the contact person of this company", min_length=11, max_length=12)]
    status: Annotated[str, Path(title="The status(active or inactive) of the contact person of this company")]
    count_licence: Annotated[int, Path(title='The count of licences of contact person of this company', ge=0)]
    date_registration: Annotated[datetime, Path(title='The date registration of contact person of this company')]
    role: Annotated[
        str, Path(title='The role for example administrator or moderator of contact person of this company')]


class LicenceBase(BaseModel):
    client_id: Annotated[int, Path(title="A link to the client with this ID", ge=1)]
    status: Annotated[Status, Path(title="The status(active or inactive) of this licence")]
    date_begin: Annotated[datetime, Path(title="Date begin of this licence")]
    date_end: Annotated[datetime, Path(title="Date end of this licence")]
    service_id: Annotated[int, Path(title="A link to the service with this ID", ge=1)]


class ObjectBase(BaseStruct):
    client_id: Annotated[int, Path(title="A link to the client with this ID", ge=1)]


class ServiceBase(BaseStruct):
    object_id: Annotated[int, Path(title="A link to the object with this ID", ge=1)]


class ObjectResponse(ObjectBase):
    id: Annotated[int, Path(title="Unique identificator for items of models created bases on this class.")]

    class Config:
        from_attributes = True


class ClientCreate(BaseModel):
    nameCompany: Annotated[str, Path(title="The name of the company of this client")]
    tin: Annotated[str, Path(title="The tin of the company of this client", min_length=10, max_length=10)]
    contact: Annotated[str, Path(title="The contact person of the company of this company")]
    email: Annotated[EmailStr, Path(title="The email of the contact person of this company")]
    num_phone: Annotated[
        str, Path(title="The phone of the contact person of this company", min_length=11, max_length=12)]
    date_registration: Annotated[datetime, Path(title='The date registration of contact person of this company')]
    role: Annotated[
        str, Path(title='The role for example administrator or moderator of contact person of this company')]


class ClientEdit(ClientBase):
    pass


class ClientResponse(ClientBase):
    id: Annotated[int, Path(title="Unique identificator for items of models of this class.")]

    class Config:
        from_attributes = True


class NoteBase(BaseModel):
    client_id: Annotated[int, Path(title="The client with this ID", ge=1)]
    name: Annotated[str, "name of the note of the client"]
    text: Annotated[str, Path(title="The text of the note of the client", min_length=10, max_length=100)]


class NoteCreate(NoteBase):
    pass


class NoteResponse(NoteBase):
    id: Annotated[int, Path(title="Unique identificator for items of models of this class.")]

    class Config:
        from_attributes = True


class LicenceResponse(LicenceBase):
    id: Annotated[int, Path(title="Unique identificator for items of models of this class.")]

    class Config:
        from_attributes = True


class LicenceCreate(LicenceBase):
    pass


class ObjectCreate(ObjectBase):
    pass


class ServiceResponse(ServiceBase):
    id: Annotated[int, Path(title="Unique identificator for items of models created bases on this class.")]

    class Config:
        from_attributes = True


class ServiceCreate(ServiceBase):
    pass


class HistoryResponse(BaseModel):
    licence_id: Annotated[int, Path(title="A link to the licence with this ID", ge=1)]
    prev_status: Annotated[Status, Path(title="The previous status(active or inactive) of this licence")]
    next_status: Annotated[Status, Path(title="The changed status(active or inactive) of this licence")]
    date: Annotated[datetime, Path(title="Date change of this licence")]
    client_id: Annotated[int, Path(title="Client ID who edit this licence", ge=1)]

    class Config:
        from_attributes = True


class EditsResponse(BaseModel):
    date: Annotated[datetime, Path(title="Date change of this licence")]
    client_id: Annotated[int, Path(title="Client ID who edit this licence", ge=1)]

    class Config:
        from_attributes = True


class LicenseInfo(BaseModel):
    client_id: int
    license_id: int
    expiry_date: datetime
    email: str
