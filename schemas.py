from pydantic import BaseModel, EmailStr
from typing import Optional, Annotated, List
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
    count_licence: Annotated[int, Path(title='The count of licences of contact person of this company')]
    date_registration: Annotated[datetime, Path(title='The date registration of contact person of this company')]
    description: Annotated[Optional[str], Path(title='The date registration of contact person of this company')]
    role: Annotated[
        str, Path(title='The role for example administrator or moderator of contact person of this company')]


class LicenceBase(BaseModel):
    client_id: Annotated[int, Path(title="A link to the client with this ID", ge=1)]
    status: Annotated[Status, Path(title="The status(active or inactive) of this licence")]
    date_begin: Annotated[datetime, Path(title="Date begin of this licence")]
    date_end: Annotated[datetime, Path(title="Date end of this licence")]
    service_id: int


class ObjectBase(BaseStruct):
    client_id: int


class ServiceBase(BaseStruct):
    object_id: int


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
    description: Annotated[Optional[str], Path(title='The date registration of contact person of this company')]
    role: Annotated[
        str, Path(title='The role for example administrator or moderator of contact person of this company')]


class ClientResponse(ClientBase):
    id: Annotated[int, Path(title="Unique identificator for items of models of this class.")]
    objects: List[ObjectResponse] = []

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
    date_end: Annotated[datetime, Path(title="Date end of this licence")]
    client_id: Annotated[int, Path(title="Client ID who edit this licence", ge=1)]
