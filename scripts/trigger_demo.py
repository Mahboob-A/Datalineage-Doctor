import os
import random
from datetime import UTC, datetime

import httpx
import structlog

logger = structlog.get_logger(__name__)

SCENARIOS = [
    {"name": "null_check_order_id", "fullyQualifiedName": "mysql.default.raw_orders"},
    {"name": "row_count_orders", "fullyQualifiedName": "mysql.default.raw_orders"},
    {"name": "unique_order_id", "fullyQualifiedName": "dbt.default.fct_orders"},
    {"name": "freshness_check", "fullyQualifiedName": "dbt.default.fct_revenue"},
    {"name": "null_check_product_id", "fullyQualifiedName": "mysql.default.raw_products"},
    {"name": "freshness_check_products", "fullyQualifiedName": "dbt.default.stg_products"},
    {"name": "anomaly_detection_revenue", "fullyQualifiedName": "dbt.default.fct_revenue"},
    {"name": "null_check_user_id", "fullyQualifiedName": "mysql.default.users"},
    {"name": "duplicate_subs", "fullyQualifiedName": "mysql.default.subscriptions"},
    {"name": "row_count_dim_users", "fullyQualifiedName": "dbt.default.dim_users"},
    {"name": "anomaly_detection_growth", "fullyQualifiedName": "dbt.default.dim_users"},
]


def get_scenario() -> dict[str, str]:
    override_name = os.getenv("DEMO_TEST_CASE")
    if override_name:
        for scenario in SCENARIOS:
            if scenario["name"] == override_name:
                return scenario
        logger.warning("override_scenario_not_found", name=override_name)
    return random.choice(SCENARIOS)


if __name__ == "__main__":
    scenario = get_scenario()
    logger.info("triggering_incident", scenario=scenario)

    payload = {
        "eventType": "testCaseFailed",
        "entityType": "testCase",
        "timestamp": int(datetime.now(tz=UTC).timestamp() * 1000),
        "entity": {
            "id": "demo-test-case-id",
            "name": scenario["name"],
            "fullyQualifiedName": scenario["fullyQualifiedName"],
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
