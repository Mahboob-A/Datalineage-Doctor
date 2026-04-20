import asyncio
from urllib.parse import quote

import httpx
import structlog

from om_client.client import OMClient

logger = structlog.get_logger(__name__)


def _to_om_table_fqn(table_fqn: str) -> str:
    """Normalize legacy 3-part table FQNs to OM's 4-part format."""
    parts = table_fqn.split(".")
    if len(parts) == 3:
        service, database, table = parts
        return f"{service}.{database}.default.{table}"
    return table_fqn


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

LINEAGE_EDGES = [
    ("mysql.default.raw_orders", "dbt.default.stg_orders"),
    ("mysql.default.raw_products", "dbt.default.stg_products"),
    ("dbt.default.stg_orders", "dbt.default.fct_orders"),
    ("dbt.default.stg_products", "dbt.default.fct_revenue"),
    ("dbt.default.fct_orders", "dbt.default.fct_revenue"),
]

TEST_CASES = [
    {
        "fqn": "mysql.default.raw_orders.null_check_order_id",
        "name": "null_check_order_id",
        "entity_link": "<#E::table::mysql.default.raw_orders>",
        "test_definition": "columnValuesToBeNotNull",
    },
    {
        "fqn": "mysql.default.raw_orders.row_count_orders",
        "name": "row_count_orders",
        "entity_link": "<#E::table::mysql.default.raw_orders>",
        "test_definition": "tableRowCountToBeBetween",
    },
    {
        "fqn": "dbt.default.fct_orders.unique_order_id",
        "name": "unique_order_id",
        "entity_link": "<#E::table::dbt.default.fct_orders>",
        "test_definition": "columnValuesToBeUnique",
    },
    {
        "fqn": "dbt.default.fct_revenue.freshness_check",
        "name": "freshness_check",
        "entity_link": "<#E::table::dbt.default.fct_revenue>",
        "test_definition": "tableLastModifiedTimeToBeBetween",
    },
]


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

    summary["created"] += 1
    logger.info("seed_entity_created", kind=kind, path=create_path)
    return created


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
            payload={
                "name": "default",
                "service": service_name,
            },
            summary=summary,
        )

        await _ensure_entity(
            om,
            kind="database_schema",
            get_path=f"/databaseSchemas/name/{quote(schema_fqn, safe='')}",
            create_path="/databaseSchemas",
            payload={
                "name": "default",
                "database": database_fqn,
            },
            summary=summary,
        )


async def _ensure_tables(om: OMClient, summary: dict[str, int]) -> None:
    for legacy_fqn, columns in TABLES.items():
        table_fqn = _to_om_table_fqn(legacy_fqn)
        parts = table_fqn.split(".")
        table_name = parts[-1]
        database_schema = ".".join(parts[:3])
        await _ensure_entity(
            om,
            kind="table",
            get_path=f"/tables/name/{quote(table_fqn, safe='')}",
            create_path="/tables",
            payload={
                "name": table_name,
                "databaseSchema": database_schema,
                "columns": columns,
            },
            summary=summary,
        )


async def _get_table_id(om: OMClient, table_fqn: str) -> str | None:
    normalized_fqn = _to_om_table_fqn(table_fqn)
    try:
        table = await om._get(f"/tables/name/{quote(normalized_fqn, safe='')}")
    except httpx.HTTPError as exc:
        logger.warning(
            "seed_table_lookup_failed",
            table_fqn=table_fqn,
            normalized_fqn=normalized_fqn,
            error=str(exc),
        )
        return None
    table_id = table.get("id")
    return str(table_id) if table_id else None


async def _ensure_lineage(om: OMClient, summary: dict[str, int]) -> None:
    for upstream_fqn, downstream_fqn in LINEAGE_EDGES:
        upstream_id = await _get_table_id(om, upstream_fqn)
        downstream_id = await _get_table_id(om, downstream_fqn)
        if upstream_id is None or downstream_id is None:
            summary["failed"] += 1
            logger.warning(
                "seed_lineage_skipped_missing_table",
                upstream_fqn=upstream_fqn,
                downstream_fqn=downstream_fqn,
            )
            continue

        try:
            assert om.client is not None
            response = await om.client.put(
                "/lineage",
                json={
                    "edge": {
                        "fromEntity": {"id": upstream_id, "type": "table"},
                        "toEntity": {"id": downstream_id, "type": "table"},
                    }
                },
            )
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            if exc.response is not None and exc.response.status_code in {400, 409}:
                summary["existing"] += 1
                logger.info(
                    "seed_lineage_exists",
                    upstream_fqn=upstream_fqn,
                    downstream_fqn=downstream_fqn,
                )
                continue
            summary["failed"] += 1
            logger.warning(
                "seed_lineage_failed",
                upstream_fqn=upstream_fqn,
                downstream_fqn=downstream_fqn,
                status_code=(
                    exc.response.status_code if exc.response is not None else None
                ),
                error=str(exc),
            )
            continue

        summary["created"] += 1
        logger.info(
            "seed_lineage_created",
            upstream_fqn=upstream_fqn,
            downstream_fqn=downstream_fqn,
        )


async def _ensure_pipeline_status(om: OMClient, summary: dict[str, int]) -> None:
    pipeline_fqn = "airflow.ingest_orders_daily"
    get_path = f"/pipelines/name/{quote(pipeline_fqn, safe='')}"
    try:
        existing = await om._get(get_path)
    except httpx.HTTPError as exc:
        summary["failed"] += 1
        logger.warning(
            "seed_pipeline_lookup_failed", pipeline_fqn=pipeline_fqn, error=str(exc)
        )
        return
    if existing.get("found", True):
        summary["existing"] += 1
        logger.info("seed_pipeline_exists", pipeline_fqn=pipeline_fqn)
        return

    try:
        await om._post(
            "/pipelines",
            payload={
                "name": "ingest_orders_daily",
                "service": "airflow",
            },
        )
    except httpx.HTTPStatusError as exc:
        summary["failed"] += 1
        logger.warning(
            "seed_pipeline_failed",
            pipeline_fqn=pipeline_fqn,
            status_code=exc.response.status_code if exc.response is not None else None,
            error=str(exc),
        )
        return

    summary["created"] += 1
    logger.info("seed_pipeline_created", pipeline_fqn=pipeline_fqn)


async def _ensure_test_cases(om: OMClient, summary: dict[str, int]) -> None:
    _ = om
    _ = summary
    logger.info(
        "seed_test_cases_skipped",
        reason=(
            "OpenMetadata requires executable test suites for test case creation; "
            "skip bootstrap test cases in demo seed"
        ),
    )


async def seed_demo_data() -> dict[str, int]:
    """Seed OpenMetadata demo entities in an idempotent best-effort manner."""
    summary = {"created": 0, "existing": 0, "failed": 0}
    async with OMClient() as om:
        for step in (
            _ensure_services,
            _ensure_databases_and_schemas,
            _ensure_tables,
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
