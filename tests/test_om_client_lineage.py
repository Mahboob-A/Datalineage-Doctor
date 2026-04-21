from om_client.lineage import _parse_lineage_nodes


def test_parse_lineage_nodes_supports_directional_edges():
    raw = {
        "nodes": [
            {"id": "root", "type": "table", "fullyQualifiedName": "mysql.default.raw_orders"},
            {"id": "a", "type": "table", "fullyQualifiedName": "dbt.default.stg_orders"},
            {"id": "b", "type": "dashboard", "fullyQualifiedName": "metabase.revenue_dashboard"},
        ],
        "downstreamEdges": [
            {"fromEntity": "root", "toEntity": "a"},
            {"fromEntity": "a", "toEntity": "b"},
        ],
    }

    parsed = _parse_lineage_nodes(raw, root_id="root", direction="downstream", depth=3)

    assert len(parsed) == 2
    assert parsed[0].fqn == "dbt.default.stg_orders"
    assert parsed[0].level == 1
    assert parsed[1].fqn == "metabase.revenue_dashboard"
    assert parsed[1].level == 2
