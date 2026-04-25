import asyncio
import importlib
import os
import socket
import sys
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import quote

import httpx
import structlog

sys.path.append(str(Path(__file__).resolve().parents[1]))


def _default_om_base_url() -> str:
    try:
        socket.gethostbyname("openmetadata_server")
    except OSError:
        return "http://localhost:8585/api/v1"
    return "http://openmetadata_server:8585/api/v1"


os.environ.setdefault("OM_BASE_URL", _default_om_base_url())

OMClient = importlib.import_module("om_client.client").OMClient

logger = structlog.get_logger(__name__)

PIPELINE_FAILED_AT_MS = int(datetime(2026, 4, 20, 3, 0, tzinfo=UTC).timestamp() * 1000)

PIPELINES = {
    "airflow.ingest_orders_daily": {
        "name": "ingest_orders_daily",
        "service": "airflow",
        "tasks": [{"name": "extract_orders"}, {"name": "load_orders"}],
        "status_timestamp": PIPELINE_FAILED_AT_MS,
        "execution_status": "Failed",
        "task_status": [
            {"name": "extract_orders", "executionStatus": "Successful"},
            {"name": "load_orders", "executionStatus": "Failed"},
        ],
    },
    "airflow.ingest_products_daily": {
        "name": "ingest_products_daily",
        "service": "airflow",
        "tasks": [{"name": "extract_products"}, {"name": "load_products"}],
        "status_timestamp": PIPELINE_FAILED_AT_MS,
        "execution_status": "Successful",
        "task_status": [
            {"name": "extract_products", "executionStatus": "Successful"},
            {"name": "load_products", "executionStatus": "Successful"},
        ],
    },
    "airflow.dbt_transform_daily": {
        "name": "dbt_transform_daily",
        "service": "airflow",
        "tasks": [{"name": "run_stg"}, {"name": "run_fct"}],
        "status_timestamp": PIPELINE_FAILED_AT_MS,
        "execution_status": "Failed",
        "task_status": [
            {"name": "run_stg", "executionStatus": "Successful"},
            {"name": "run_fct", "executionStatus": "Failed"},
        ],
    },
}

TABLES = {
    "mysql.default.raw_orders": [
        {"name": "order_id", "dataType": "INT"},
        {"name": "customer_id", "dataType": "INT"},
        {"name": "order_ts", "dataType": "TIMESTAMP"},
    ],
    "mysql.default.raw_products": [
        {"name": "product_id", "dataType": "INT"},
        {"name": "sku", "dataType": "VARCHAR", "dataLength": 255},
    ],
    "dbt.default.stg_orders": [
        {"name": "order_id", "dataType": "INT"},
        {"name": "customer_id", "dataType": "INT"},
    ],
    "dbt.default.stg_products": [
        {"name": "product_id", "dataType": "INT"},
        {"name": "sku", "dataType": "VARCHAR", "dataLength": 255},
    ],
    "dbt.default.fct_orders": [
        {"name": "order_id", "dataType": "INT"},
        {"name": "product_id", "dataType": "INT"},
        {"name": "revenue", "dataType": "DECIMAL"},
    ],
    "dbt.default.fct_revenue": [
        {"name": "order_date", "dataType": "DATE"},
        {"name": "daily_revenue", "dataType": "DECIMAL"},
    ],
}

DASHBOARDS = {
    "metabase.revenue_dashboard": {
        "name": "revenue_dashboard",
        "service": "metabase",
        "description": "Revenue trends powered by fct_orders and fct_revenue.",
    }
}

LINEAGE_EDGES = [
    ("pipeline", "airflow.ingest_orders_daily", "table", "mysql.default.raw_orders"),
    ("pipeline", "airflow.ingest_products_daily", "table", "mysql.default.raw_products"),
    ("table", "mysql.default.raw_orders", "table", "dbt.default.stg_orders"),
    ("table", "mysql.default.raw_products", "table", "dbt.default.stg_products"),
    ("pipeline", "airflow.dbt_transform_daily", "table", "dbt.default.stg_orders"),
    ("pipeline", "airflow.dbt_transform_daily", "table", "dbt.default.stg_products"),
    ("table", "dbt.default.stg_orders", "table", "dbt.default.fct_orders"),
    ("table", "dbt.default.stg_products", "table", "dbt.default.fct_revenue"),
    ("table", "dbt.default.fct_orders", "table", "dbt.default.fct_revenue"),
    ("table", "dbt.default.fct_orders", "dashboard", "metabase.revenue_dashboard"),
]

TEST_CASES = [
    {
        "name": "null_check_order_id",
        "table_fqn": "mysql.default.raw_orders",
        "test_definition": "columnValuesToBeNotNull",
    },
    {
        "name": "row_count_orders",
        "table_fqn": "mysql.default.raw_orders",
        "test_definition": "tableRowCountToBeBetween",
    },
    {
        "name": "unique_order_id",
        "table_fqn": "dbt.default.fct_orders",
        "test_definition": "columnValuesToBeUnique",
    },
    {
        "name": "freshness_check",
        "table_fqn": "dbt.default.fct_revenue",
        "test_definition": "tableLastModifiedTimeToBeBetween",
    },
    {
        "name": "null_check_product_id",
        "table_fqn": "mysql.default.raw_products",
        "test_definition": "columnValuesToBeNotNull",
    },
    {
        "name": "freshness_check_products",
        "table_fqn": "dbt.default.stg_products",
        "test_definition": "tableLastModifiedTimeToBeBetween",
    },
    {
        "name": "anomaly_detection_revenue",
        "table_fqn": "dbt.default.fct_revenue",
        "test_definition": "tableRowCountToBeBetween",
    },
]

CUSTOM_TEST_DEFINITIONS = {
    "tableLastModifiedTimeToBeBetween": {
        "description": "Validate table freshness by checking last modified time.",
        "entityType": "TABLE",
        "testPlatforms": ["OpenMetadata"],
    }
}


def _to_om_table_fqn(table_fqn: str) -> str:
    parts = table_fqn.split(".")
    if len(parts) == 3:
        service, database, table = parts
        return f"{service}.{database}.default.{table}"
    return table_fqn


def _table_fqn_candidates(table_fqn: str) -> list[str]:
    normalized = _to_om_table_fqn(table_fqn)
    if normalized == table_fqn:
        return [table_fqn]
    return [normalized, table_fqn]


def _test_case_fqn_candidates(table_fqn: str, name: str) -> list[str]:
    candidates = []
    for candidate in _table_fqn_candidates(table_fqn):
        candidates.append(f"{candidate}.{name}")
    unique: list[str] = []
    seen: set[str] = set()
    for candidate in candidates:
        if candidate in seen:
            continue
        seen.add(candidate)
        unique.append(candidate)
    return unique


async def _put_json(om: OMClient, path: str, payload: dict[str, object]) -> httpx.Response:
    assert om.client is not None
    response = await om.client.put(path, json=payload)
    response.raise_for_status()
    return response


async def _ensure_entity(
    om: OMClient,
    *,
    kind: str,
    get_path: str,
    create_path: str,
    payload: dict[str, object],
    summary: dict[str, int],
) -> dict[str, object]:
    try:
        existing = await om._get(get_path)
    except httpx.HTTPError as exc:
        summary["failed"] += 1
        logger.warning(
            "seed_entity_lookup_failed",
            kind=kind,
            path=get_path,
            error=str(exc),
        )
        return {}

    if existing.get("found", True):
        summary["existing"] += 1
        logger.info("seed_entity_exists", kind=kind, path=get_path)
        return existing

    try:
        created = await om._post(create_path, payload=payload)
    except httpx.HTTPStatusError as exc:
        summary["failed"] += 1
        logger.warning(
            "seed_entity_create_failed",
            kind=kind,
            path=create_path,
            status_code=exc.response.status_code if exc.response is not None else None,
            error=str(exc),
        )
        return {}

    if created.get("found") is False:
        summary["failed"] += 1
        logger.warning("seed_entity_create_not_found", kind=kind, path=create_path)
        return {}

    summary["created"] += 1
    logger.info("seed_entity_created", kind=kind, path=create_path)
    return created


async def _lookup_table(om: OMClient, table_fqn: str) -> dict[str, object]:
    response = {"found": False}
    for candidate in _table_fqn_candidates(table_fqn):
        response = await om._get(f"/tables/name/{quote(candidate, safe='')}")
        if response.get("found", True):
            break
    return response


async def _lookup_test_case(om: OMClient, table_fqn: str, name: str) -> dict[str, object]:
    response = {"found": False}
    for candidate in _test_case_fqn_candidates(table_fqn, name):
        response = await om._get(f"/dataQuality/testCases/name/{quote(candidate, safe='')}")
        if response.get("found", True):
            break
    return response


async def _lookup_dashboard(om: OMClient, dashboard_fqn: str) -> dict[str, object]:
    return await om._get(f"/dashboards/name/{quote(dashboard_fqn, safe='')}")


async def _lookup_pipeline(om: OMClient, pipeline_fqn: str) -> dict[str, object]:
    return await om._get(f"/pipelines/name/{quote(pipeline_fqn, safe='')}")


def _extract_edge_node_id(edge: dict[str, object], key: str) -> str:
    value = edge.get(key)
    if isinstance(value, dict):
        return str(value.get("id") or "")
    if isinstance(value, str):
        return value
    return ""


async def _lookup_lineage_graph(
    om: OMClient,
    *,
    entity_type: str,
    entity_id: str,
) -> dict[str, object]:
    return await om._get(
        f"/lineage/{entity_type}/{quote(entity_id, safe='')}",
        params={"upstreamDepth": 3, "downstreamDepth": 3},
    )


def _lineage_edge_exists(
    raw: dict[str, object],
    *,
    from_id: str,
    to_id: str,
) -> bool:
    edge_groups = []
    for key in ("edges", "upstreamEdges", "downstreamEdges"):
        value = raw.get(key)
        if isinstance(value, list):
            edge_groups.extend(value)

    for edge in edge_groups:
        if not isinstance(edge, dict):
            continue
        if (
            _extract_edge_node_id(edge, "fromEntity") == from_id
            and _extract_edge_node_id(edge, "toEntity") == to_id
        ):
            return True
    return False


def _extract_latest_pipeline_status(raw_status: object) -> dict[str, object]:
    if isinstance(raw_status, dict):
        return raw_status
    if isinstance(raw_status, list):
        candidates = [item for item in raw_status if isinstance(item, dict)]
        if not candidates:
            return {}
        return max(
            candidates,
            key=lambda item: int(item.get("timestamp") or 0),
        )
    return {}


def _pipeline_status_matches(
    latest_status: dict[str, object],
    *,
    timestamp: int,
    execution_status: str,
) -> bool:
    if not latest_status:
        return False
    latest_timestamp = latest_status.get("timestamp")
    latest_execution = latest_status.get("executionStatus")
    return latest_timestamp == timestamp and latest_execution == execution_status


async def _ensure_test_definition(
    om: OMClient,
    *,
    test_definition: str,
    summary: dict[str, int],
) -> bool:
    try:
        existing = await om._get(
            f"/dataQuality/testDefinitions/name/{quote(test_definition, safe='')}"
        )
    except httpx.HTTPError as exc:
        summary["failed"] += 1
        logger.warning(
            "seed_test_definition_lookup_failed",
            test_definition=test_definition,
            error=str(exc),
        )
        return False

    if existing.get("found", True):
        summary["existing"] += 1
        logger.info("seed_test_definition_exists", test_definition=test_definition)
        return True

    custom_definition = CUSTOM_TEST_DEFINITIONS.get(test_definition)
    if custom_definition is None:
        summary["failed"] += 1
        logger.warning(
            "seed_test_definition_missing",
            test_definition=test_definition,
            error="Definition not found and no custom bootstrap payload configured",
        )
        return False

    payload = {"name": test_definition, **custom_definition}
    try:
        created = await om._post("/dataQuality/testDefinitions", payload=payload)
    except httpx.HTTPStatusError as exc:
        if exc.response is not None and exc.response.status_code == 409:
            summary["existing"] += 1
            logger.info("seed_test_definition_exists", test_definition=test_definition)
            return True
        summary["failed"] += 1
        logger.warning(
            "seed_test_definition_create_failed",
            test_definition=test_definition,
            status_code=exc.response.status_code if exc.response is not None else None,
            error=str(exc),
        )
        return False

    if created.get("found") is False:
        summary["failed"] += 1
        logger.warning("seed_test_definition_create_not_found", test_definition=test_definition)
        return False

    summary["created"] += 1
    logger.info("seed_test_definition_created", test_definition=test_definition)
    return True


async def _ensure_executable_test_suite(
    om: OMClient,
    *,
    table_fqn: str,
    summary: dict[str, int],
) -> str | None:
    normalized_table_fqn = _to_om_table_fqn(table_fqn)
    suite_fqn = f"{normalized_table_fqn}.testSuite"
    try:
        existing_suite = await om._get(
            f"/dataQuality/testSuites/name/{quote(suite_fqn, safe='')}"
        )
    except httpx.HTTPError as exc:
        summary["failed"] += 1
        logger.warning(
            "seed_test_suite_lookup_failed",
            table_fqn=table_fqn,
            suite_fqn=suite_fqn,
            error=str(exc),
        )
        return None

    if existing_suite.get("found", True):
        summary["existing"] += 1
        logger.info("seed_test_suite_exists", table_fqn=table_fqn, suite_fqn=suite_fqn)
        return str(existing_suite.get("fullyQualifiedName") or suite_fqn)

    table_name = normalized_table_fqn.split(".")[-1]
    payload = {
        "name": f"{table_name}_test_suite",
        "displayName": f"{table_name}_test_suite",
        "executableEntityReference": normalized_table_fqn,
    }
    try:
        created_suite = await om._post("/dataQuality/testSuites/executable", payload=payload)
    except httpx.HTTPStatusError as exc:
        if exc.response is not None and exc.response.status_code == 409:
            summary["existing"] += 1
            logger.info("seed_test_suite_exists", table_fqn=table_fqn, suite_fqn=suite_fqn)
            return suite_fqn
        summary["failed"] += 1
        logger.warning(
            "seed_test_suite_failed",
            table_fqn=table_fqn,
            suite_fqn=suite_fqn,
            status_code=exc.response.status_code if exc.response is not None else None,
            error=str(exc),
        )
        return None

    if created_suite.get("found") is False:
        summary["failed"] += 1
        logger.warning("seed_test_suite_create_not_found", table_fqn=table_fqn)
        return None

    summary["created"] += 1
    created_fqn = str(created_suite.get("fullyQualifiedName") or suite_fqn)
    logger.info(
        "seed_test_suite_created",
        table_fqn=table_fqn,
        suite_fqn=created_fqn,
    )
    return created_fqn


async def _ensure_services(om: OMClient, summary: dict[str, int]) -> None:
    await _ensure_entity(
        om,
        kind="database_service",
        get_path="/services/databaseServices/name/mysql",
        create_path="/services/databaseServices",
        payload={
            "name": "mysql",
            "serviceType": "Mysql",
            "connection": {"config": {"type": "Mysql"}},
        },
        summary=summary,
    )
    await _ensure_entity(
        om,
        kind="database_service",
        get_path="/services/databaseServices/name/dbt",
        create_path="/services/databaseServices",
        payload={
            "name": "dbt",
            "serviceType": "Mysql",
            "connection": {"config": {"type": "Mysql"}},
        },
        summary=summary,
    )
    await _ensure_entity(
        om,
        kind="pipeline_service",
        get_path="/services/pipelineServices/name/airflow",
        create_path="/services/pipelineServices",
        payload={
            "name": "airflow",
            "serviceType": "Airflow",
            "connection": {"config": {"type": "Airflow"}},
        },
        summary=summary,
    )
    await _ensure_entity(
        om,
        kind="dashboard_service",
        get_path="/services/dashboardServices/name/metabase",
        create_path="/services/dashboardServices",
        payload={
            "name": "metabase",
            "serviceType": "Metabase",
            "connection": {"config": {"type": "Metabase"}},
        },
        summary=summary,
    )


async def _ensure_databases_and_schemas(om: OMClient, summary: dict[str, int]) -> None:
    for service_name in ("mysql", "dbt"):
        database_fqn = f"{service_name}.default"
        schema_fqn = f"{database_fqn}.default"
        await _ensure_entity(
            om,
            kind="database",
            get_path=f"/databases/name/{quote(database_fqn, safe='')}",
            create_path="/databases",
            payload={"name": "default", "service": service_name},
            summary=summary,
        )
        await _ensure_entity(
            om,
            kind="database_schema",
            get_path=f"/databaseSchemas/name/{quote(schema_fqn, safe='')}",
            create_path="/databaseSchemas",
            payload={"name": "default", "database": database_fqn},
            summary=summary,
        )


async def _ensure_tables(om: OMClient, summary: dict[str, int]) -> None:
    for table_fqn, columns in TABLES.items():
        normalized = _to_om_table_fqn(table_fqn)
        parts = normalized.split(".")
        table_name = parts[-1]
        database_schema = ".".join(parts[:3])
        await _ensure_entity(
            om,
            kind="table",
            get_path=f"/tables/name/{quote(normalized, safe='')}",
            create_path="/tables",
            payload={
                "name": table_name,
                "databaseSchema": database_schema,
                "columns": columns,
            },
            summary=summary,
        )


async def _ensure_dashboards(om: OMClient, summary: dict[str, int]) -> None:
    for dashboard_fqn, config in DASHBOARDS.items():
        await _ensure_entity(
            om,
            kind="dashboard",
            get_path=f"/dashboards/name/{quote(dashboard_fqn, safe='')}",
            create_path="/dashboards",
            payload={
                "name": str(config["name"]),
                "service": str(config["service"]),
                "description": str(config["description"]),
            },
            summary=summary,
        )


async def _ensure_pipeline(om: OMClient, summary: dict[str, int]) -> None:
    for pipeline_fqn, config in PIPELINES.items():
        get_path = f"/pipelines/name/{quote(pipeline_fqn, safe='')}?fields=tasks"
        payload = {
            "name": config["name"],
            "service": config["service"],
            "tasks": config["tasks"],
        }
        try:
            existing = await om._get(get_path)
        except httpx.HTTPError as exc:
            summary["failed"] += 1
            logger.warning("seed_pipeline_lookup_failed", pipeline_fqn=pipeline_fqn, error=str(exc))
            continue

        has_tasks = isinstance(existing.get("tasks"), list) and len(existing["tasks"]) > 0
        if existing.get("found", True) and has_tasks:
            summary["existing"] += 1
            logger.info("seed_pipeline_exists", pipeline_fqn=pipeline_fqn)
            continue

        try:
            response = await _put_json(om, "/pipelines", payload)
            body = response.json()
        except httpx.HTTPStatusError as exc:
            summary["failed"] += 1
            logger.warning(
                "seed_pipeline_upsert_failed",
                pipeline_fqn=pipeline_fqn,
                status_code=exc.response.status_code if exc.response is not None else None,
                error=str(exc),
            )
            continue

        if isinstance(body, dict) and body.get("found") is False:
            summary["failed"] += 1
            logger.warning("seed_pipeline_upsert_not_found", pipeline_fqn=pipeline_fqn)
            continue

        summary["created"] += 1
        logger.info("seed_pipeline_upserted", pipeline_fqn=pipeline_fqn)


async def _ensure_lineage(om: OMClient, summary: dict[str, int]) -> None:
    for from_type, from_fqn, to_type, to_fqn in LINEAGE_EDGES:
        try:
            if from_type == "table":
                from_entity = await _lookup_table(om, from_fqn)
            elif from_type == "pipeline":
                from_entity = await _lookup_pipeline(om, from_fqn)
            else:
                from_entity = await _lookup_dashboard(om, from_fqn)

            if to_type == "table":
                to_entity = await _lookup_table(om, to_fqn)
            elif to_type == "pipeline":
                to_entity = await _lookup_pipeline(om, to_fqn)
            else:
                to_entity = await _lookup_dashboard(om, to_fqn)
        except httpx.HTTPError as exc:
            summary["failed"] += 1
            logger.warning(
                "seed_lineage_lookup_failed",
                from_type=from_type,
                from_fqn=from_fqn,
                to_type=to_type,
                to_fqn=to_fqn,
                error=str(exc),
            )
            continue

        from_id = from_entity.get("id")
        to_id = to_entity.get("id")
        if not from_id or not to_id:
            summary["failed"] += 1
            logger.warning(
                "seed_lineage_skipped_missing_entity",
                from_type=from_type,
                from_fqn=from_fqn,
                to_type=to_type,
                to_fqn=to_fqn,
            )
            continue

        try:
            existing_lineage = await _lookup_lineage_graph(
                om,
                entity_type=from_type,
                entity_id=str(from_id),
            )
        except httpx.HTTPError as exc:
            summary["failed"] += 1
            logger.warning(
                "seed_lineage_lookup_failed",
                from_type=from_type,
                from_fqn=from_fqn,
                to_type=to_type,
                to_fqn=to_fqn,
                error=str(exc),
            )
            continue

        if _lineage_edge_exists(
            existing_lineage,
            from_id=str(from_id),
            to_id=str(to_id),
        ):
            summary["existing"] += 1
            logger.info(
                "seed_lineage_exists",
                from_type=from_type,
                from_fqn=from_fqn,
                to_type=to_type,
                to_fqn=to_fqn,
            )
            continue

        try:
            await _put_json(
                om,
                "/lineage",
                {
                    "edge": {
                        "fromEntity": {"id": str(from_id), "type": from_type},
                        "toEntity": {"id": str(to_id), "type": to_type},
                    }
                },
            )
            summary["created"] += 1
            logger.info(
                "seed_lineage_created",
                from_type=from_type,
                from_fqn=from_fqn,
                to_type=to_type,
                to_fqn=to_fqn,
            )
        except httpx.HTTPStatusError as exc:
            if exc.response is not None and exc.response.status_code in {400, 409}:
                summary["existing"] += 1
                logger.info(
                    "seed_lineage_exists",
                    from_type=from_type,
                    from_fqn=from_fqn,
                    to_type=to_type,
                    to_fqn=to_fqn,
                )
                continue
            summary["failed"] += 1
            logger.warning(
                "seed_lineage_failed",
                from_type=from_type,
                from_fqn=from_fqn,
                to_type=to_type,
                to_fqn=to_fqn,
                status_code=exc.response.status_code if exc.response is not None else None,
                error=str(exc),
            )


async def _ensure_pipeline_status(om: OMClient, summary: dict[str, int]) -> None:
    for pipeline_fqn, config in PIPELINES.items():
        try:
            pipeline = await om._get(
                f"/pipelines/name/{quote(pipeline_fqn, safe='')}",
                params={"fields": "pipelineStatus"},
            )
        except httpx.HTTPError as exc:
            summary["failed"] += 1
            logger.warning("seed_pipeline_lookup_failed", pipeline_fqn=pipeline_fqn, error=str(exc))
            continue

        if not pipeline.get("found", True):
            summary["failed"] += 1
            logger.warning("seed_pipeline_missing", pipeline_fqn=pipeline_fqn)
            continue

        status_payload = {
            "timestamp": config["status_timestamp"],
            "executionStatus": config["execution_status"],
            "taskStatus": config["task_status"],
        }
        status_path = f"/pipelines/{quote(pipeline_fqn, safe='')}/status"
        latest_status = _extract_latest_pipeline_status(pipeline.get("pipelineStatus"))

        if _pipeline_status_matches(
            latest_status,
            timestamp=config["status_timestamp"],
            execution_status=config["execution_status"],
        ):
            summary["existing"] += 1
            logger.info(
                "seed_pipeline_status_exists",
                pipeline_fqn=pipeline_fqn,
                timestamp=config["status_timestamp"],
            )
            continue

        try:
            await _put_json(om, status_path, status_payload)
            summary["created"] += 1
            logger.info(
                "seed_pipeline_status_created",
                pipeline_fqn=pipeline_fqn,
                timestamp=config["status_timestamp"],
            )
        except httpx.HTTPStatusError as exc:
            if exc.response is not None and exc.response.status_code == 409:
                summary["existing"] += 1
                logger.info(
                    "seed_pipeline_status_exists",
                    pipeline_fqn=pipeline_fqn,
                    timestamp=config["status_timestamp"],
                )
                continue
            summary["failed"] += 1
            logger.warning(
                "seed_pipeline_status_failed",
                pipeline_fqn=pipeline_fqn,
                status_code=exc.response.status_code if exc.response is not None else None,
                error=str(exc),
            )


async def _ensure_test_cases(om: OMClient, summary: dict[str, int]) -> None:
    for test_case in TEST_CASES:
        name = str(test_case["name"])
        table_fqn = str(test_case["table_fqn"])
        test_definition = str(test_case["test_definition"])
        has_definition = await _ensure_test_definition(
            om, test_definition=test_definition, summary=summary
        )
        if not has_definition:
            continue
        suite_fqn = await _ensure_executable_test_suite(
            om, table_fqn=table_fqn, summary=summary
        )
        if suite_fqn is None:
            continue

        try:
            existing = await _lookup_test_case(om, table_fqn=table_fqn, name=name)
        except httpx.HTTPError as exc:
            summary["failed"] += 1
            logger.warning(
                "seed_test_case_lookup_failed",
                name=name,
                table_fqn=table_fqn,
                error=str(exc),
            )
            continue

        if existing.get("found", True):
            summary["existing"] += 1
            logger.info("seed_test_case_exists", name=name, table_fqn=table_fqn)
            continue

        entity_link = f"<#E::table::{_to_om_table_fqn(table_fqn)}>"
        payload = {
            "name": name,
            "displayName": name,
            "entityLink": entity_link,
            "testDefinition": test_definition,
            "testSuite": suite_fqn,
            "computePassedFailedRowCount": False,
            "useDynamicAssertion": False,
        }
        try:
            created = await om._post("/dataQuality/testCases", payload=payload)
            if created.get("found") is False:
                summary["failed"] += 1
                logger.warning(
                    "seed_test_case_create_not_found",
                    name=name,
                    table_fqn=table_fqn,
                    test_definition=test_definition,
                )
                continue
            summary["created"] += 1
            logger.info("seed_test_case_created", name=name, table_fqn=table_fqn)
        except httpx.HTTPStatusError as exc:
            if exc.response is not None and exc.response.status_code == 409:
                summary["existing"] += 1
                logger.info("seed_test_case_exists", name=name, table_fqn=table_fqn)
                continue
            summary["failed"] += 1
            logger.warning(
                "seed_test_case_failed",
                name=name,
                table_fqn=table_fqn,
                test_definition=test_definition,
                status_code=exc.response.status_code if exc.response is not None else None,
                error=str(exc),
            )


async def seed_demo_data() -> dict[str, int]:
    summary = {"created": 0, "existing": 0, "failed": 0}
    async with OMClient() as om:
        for step in (
            _ensure_services,
            _ensure_databases_and_schemas,
            _ensure_tables,
            _ensure_dashboards,
            _ensure_pipeline,
            _ensure_lineage,
            _ensure_pipeline_status,
            _ensure_test_cases,
        ):
            try:
                await step(om, summary)
            except Exception as exc:
                summary["failed"] += 1
                logger.warning("seed_step_failed", step=step.__name__, error=str(exc))
    return summary


if __name__ == "__main__":
    results = asyncio.run(seed_demo_data())
    logger.info("seed_demo_summary", **results)
    if results["failed"] > 0:
        raise SystemExit(1)
