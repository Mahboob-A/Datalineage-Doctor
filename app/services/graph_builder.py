from __future__ import annotations

from dataclasses import dataclass

from app.models import BlastRadiusConsumer, Incident, TimelineEvent


@dataclass(frozen=True)
class _GraphNode:
    node_id: str
    label: str
    service: str
    is_root_cause: bool
    direction: str


def _label_from_fqn(fqn: str) -> str:
    parts = fqn.split(".")
    if parts:
        return parts[-1]
    return fqn


def _build_nodes_for_events(
    events: list[TimelineEvent],
    *,
    root_fqn: str,
    downstream_ids: set[str],
) -> list[_GraphNode]:
    nodes: list[_GraphNode] = []
    for event in events:
        if event.entity_fqn == root_fqn:
            continue
        if event.entity_fqn in downstream_ids:
            continue
        nodes.append(
            _GraphNode(
                node_id=event.entity_fqn,
                label=_label_from_fqn(event.entity_fqn),
                service=(
                    event.entity_fqn.split(".")[0]
                    if "." in event.entity_fqn
                    else "unknown"
                ),
                is_root_cause=False,
                direction="upstream",
            )
        )
    return nodes


def build_graph_data(
    incident: Incident,
    timeline_events: list[TimelineEvent],
    blast_radius: list[BlastRadiusConsumer],
) -> dict[str, list[dict[str, object]]]:
    """Build the React Flow graph payload for an incident detail view."""
    root_node = _GraphNode(
        node_id=incident.table_fqn,
        label=_label_from_fqn(incident.table_fqn),
        service=(
            incident.table_fqn.split(".")[0] if "." in incident.table_fqn else "unknown"
        ),
        is_root_cause=True,
        direction="root",
    )
    downstream_nodes = [
        _GraphNode(
            node_id=consumer.entity_fqn,
            label=_label_from_fqn(consumer.entity_fqn),
            service=consumer.service,
            is_root_cause=False,
            direction="downstream",
        )
        for consumer in blast_radius
    ]
    downstream_ids = {node.node_id for node in downstream_nodes}
    upstream_nodes = _build_nodes_for_events(
        timeline_events, root_fqn=incident.table_fqn, downstream_ids=downstream_ids
    )

    nodes = [root_node] + upstream_nodes + downstream_nodes
    unique_nodes: dict[str, _GraphNode] = {}
    for node in nodes:
        unique_nodes.setdefault(node.node_id, node)
    nodes = list(unique_nodes.values())

    column_index = {
        "upstream": -1,
        "root": 0,
        "downstream": 1,
    }
    offsets = {"upstream": 0, "root": 0, "downstream": 0}
    positioned_nodes: list[dict[str, object]] = []

    for node in nodes:
        column = column_index.get(node.direction, 0)
        row = offsets[node.direction]
        offsets[node.direction] += 1
        positioned_nodes.append(
            {
                "id": node.node_id,
                "data": {
                    "label": node.label,
                    "service": node.service,
                    "is_root_cause": node.is_root_cause,
                    "direction": node.direction,
                },
                "type": "custom",
                "position": {"x": column * 240, "y": row * 120},
            }
        )

    edges: list[dict[str, object]] = []
    for node in upstream_nodes:
        edges.append(
            {
                "id": f"e-{node.node_id}-root",
                "source": node.node_id,
                "target": root_node.node_id,
            }
        )
    for node in downstream_nodes:
        edges.append(
            {
                "id": f"e-root-{node.node_id}",
                "source": root_node.node_id,
                "target": node.node_id,
            }
        )

    return {"nodes": positioned_nodes, "edges": edges}
