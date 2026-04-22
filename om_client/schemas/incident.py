from pydantic import BaseModel


class OMIncidentPayload(BaseModel):
    name: str
    entityReference: dict[str, str]
    incidentType: str
    description: str
    severity: str
