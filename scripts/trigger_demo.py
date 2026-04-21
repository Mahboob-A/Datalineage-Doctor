from datetime import UTC, datetime

import httpx
import structlog

logger = structlog.get_logger(__name__)

payload = {
    "eventType": "testCaseFailed",
    "entityType": "testCase",
    "timestamp": int(datetime.now(tz=UTC).timestamp() * 1000),
    "entity": {
        "id": "demo-test-case-id",
        "name": "null_check_order_id",
        "fullyQualifiedName": "mysql.default.raw_orders",
        "entityType": "table",
    },
    "changeDescription": {
        "fieldsUpdated": [
            {
                "name": "testCaseResult",
                "oldValue": "Passed",
                "newValue": "Failed",
            }
        ]
    },
}


if __name__ == "__main__":
    response = httpx.post(
        "http://localhost:8000/webhook/openmetadata",
        json=payload,
        timeout=30,
    )
    logger.info(
        "trigger_demo_response",
        status_code=response.status_code,
        body=response.text,
    )
