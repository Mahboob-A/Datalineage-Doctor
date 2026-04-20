from app.models import IncidentStatus
from app.services.incident_store import status_to_badge


def test_status_to_badge_complete():
    assert status_to_badge(IncidentStatus.COMPLETE) == "complete"


def test_status_to_badge_failed():
    assert status_to_badge(IncidentStatus.FAILED) == "failed"
