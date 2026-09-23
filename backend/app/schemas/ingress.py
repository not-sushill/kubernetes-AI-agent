from __future__ import annotations

from pydantic import BaseModel

from app.schemas.event import EventResponse


class IngressResponse(BaseModel):
    namespace: str
    name: str
    ingress_class: str
    hosts: list[str]
    address: str
    ports: str
    age: str


class IngressRule(BaseModel):
    host: str
    path: str
    service: str
    port: int | str


class IngressTLS(BaseModel):
    hosts: list[str]
    secret_name: str


class IngressDetailResponse(BaseModel):
    namespace: str
    name: str
    ingress_class: str
    address: str

    rules: list[IngressRule]
    tls: list[IngressTLS]

    labels: dict[str, str]
    annotations: dict[str, str]


class IngressYamlResponse(BaseModel):
    namespace: str
    name: str
    yaml: str


class IngressEventsResponse(BaseModel):
    namespace: str
    name: str

    total_events: int

    events: list[EventResponse]