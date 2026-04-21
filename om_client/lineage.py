from collections import defaultdict, deque
from urllib.parse import quote

from app.config import settings
from om_client.client import OMClient, get_table_fqn_candidates
from om_client.schemas.lineage import LineageNode


def _extract_edge_node_id(edge: dict[str, object], key: str) -> str:
    value = edge.get(key)
    if isinstance(value, dict):
        return str(value.get("id", ""))
    if isinstance(value, str):
        return value
    return ""


def _extract_service_name(node: dict[str, object], fqn: str) -> str:
    service = node.get("service")
    if isinstance(service, dict):
        name = service.get("name")
        if isinstance(name, str) and name:
            return name
    if isinstance(service, str) and service:
        return service
    if "." in fqn:
        return fqn.split(".", 1)[0]
    return "unknown"


def _build_levels(
    root_id: str,
    edges: list[dict[str, object]],
    *,
    direction: str,
    depth: int,
) -> dict[str, int]:
    downstream_graph: dict[str, list[str]] = defaultdict(list)
    upstream_graph: dict[str, list[str]] = defaultdict(list)

    for edge in edges:
        upstream_id = _extract_edge_node_id(edge, "fromEntity")
        downstream_id = _extract_edge_node_id(edge, "toEntity")
        if not upstream_id or not downstream_id:
            continue
        downstream_graph[upstream_id].append(downstream_id)
        upstream_graph[downstream_id].append(upstream_id)

    graph = upstream_graph if direction == "upstream" else downstream_graph

    levels: dict[str, int] = {}
    visited = {root_id}
    queue = deque([(root_id, 0)])

    while queue:
        current, level = queue.popleft()
        if level >= depth:
            continue
        for neighbor in graph.get(current, []):
            if neighbor in visited:
                continue
            visited.add(neighbor)
            levels[neighbor] = level + 1
            queue.append((neighbor, level + 1))

    return levels


def _parse_lineage_nodes(
    raw: dict[str, object],
    *,
    root_id: str,
    direction: str,
    depth: int,
) -> list[LineageNode]:
    raw_nodes = raw.get("nodes", [])
    raw_edges = raw.get("edges")
    if not isinstance(raw_edges, list):
        raw_edges = raw.get(f"{direction}Edges", [])
    if not isinstance(raw_nodes, list) or not isinstance(raw_edges, list):
        return []

    nodes_by_id: dict[str, dict[str, object]] = {}
    for node in raw_nodes:
        if not isinstance(node, dict):
            continue
        node_id = str(node.get("id", ""))
        if node_id:
            nodes_by_id[node_id] = node

    levels = _build_levels(
        root_id=root_id, edges=raw_edges, direction=direction, depth=depth
    )

    parsed: list[LineageNode] = []
    for node_id, level in levels.items():
        node = nodes_by_id.get(node_id)
        if node is None:
            continue
        fqn = str(
            node.get("fullyQualifiedName") or node.get("fqn") or node.get("name") or ""
        )
        entity_type = str(
            node.get("type") or node.get("entityType") or "unknown"
        ).lower()
        parsed.append(
            LineageNode(
                fqn=fqn,
                entity_type=entity_type,
                service=_extract_service_name(node, fqn=fqn),
                level=level,
            )
        )

    return sorted(parsed, key=lambda item: (item.level, item.fqn))


async def get_upstream_lineage(table_fqn: str, depth: int = 3) -> list[LineageNode]:
    """Resolve and return upstream lineage nodes for a table FQN."""
    capped_depth = max(1, min(depth, settings.om_max_lineage_depth))
    async with OMClient() as om:
        table = {"found": False}
        for candidate in get_table_fqn_candidates(table_fqn):
            table = await om._get(f"/tables/name/{quote(candidate, safe='')}")
            if table.get("found", True):
                break
        if not table.get("found", True) or "id" not in table:
            return []

        table_id = str(table["id"])
        raw = await om._get(
            f"/lineage/table/{table_id}",
            params={"upstreamDepth": capped_depth, "downstreamDepth": 0},
        )
        return _parse_lineage_nodes(
            raw,
            root_id=table_id,
            direction="upstream",
            depth=capped_depth,
        )


async def get_downstream_lineage(table_fqn: str, depth: int = 3) -> list[LineageNode]:
    """Resolve and return downstream lineage nodes for a table FQN."""
    capped_depth = max(1, min(depth, settings.om_max_lineage_depth))
    async with OMClient() as om:
        table = {"found": False}
        for candidate in get_table_fqn_candidates(table_fqn):
            table = await om._get(f"/tables/name/{quote(candidate, safe='')}")
            if table.get("found", True):
                break
        if not table.get("found", True) or "id" not in table:
            return []

        table_id = str(table["id"])
        raw = await om._get(
            f"/lineage/table/{table_id}",
            params={"upstreamDepth": 0, "downstreamDepth": capped_depth},
        )
        return _parse_lineage_nodes(
            raw,
            root_id=table_id,
            direction="downstream",
            depth=capped_depth,
        )
