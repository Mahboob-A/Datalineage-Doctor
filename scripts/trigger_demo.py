from datetime import UTC, datetime

import httpx

payload = {
    "eventType": "testCaseFailed",
    "entityType": "testCase",
    "timestamp": int(datetime.now(tz=UTC).timestamp() * 1000),
    "entity": {
        "id": "demo-id",
        "name": "orders_row_count_check",
        "fullyQualifiedName": "mysql.default.default.raw_orders",
        "entityType": "table",
    },
}


if __name__ == "__main__":
    response = httpx.post(
        "http://localhost:8000/webhook/openmetadata", json=payload, timeout=30
    )
    print(response.status_code)
    print(response.text)
