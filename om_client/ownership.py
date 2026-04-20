from urllib.parse import quote

from om_client.client import OMClient, get_table_fqn_candidates
from om_client.schemas.ownership import EntityOwner

ENTITY_TYPE_PATH = {
    "table": "tables",
    "pipeline": "pipelines",
    "dashboard": "dashboards",
}


def _normalize_owner_type(value: object) -> str:
    text = str(value or "").lower()
    if "team" in text:
        return "team"
    return "user"


async def get_entity_owners(entity_fqn: str, entity_type: str) -> list[EntityOwner]:
    """Return owner entries for a supported OpenMetadata entity type and FQN."""
    normalized_type = entity_type.lower()
    if normalized_type not in ENTITY_TYPE_PATH:
        raise ValueError(f"Unsupported entity_type: {entity_type}")

    async with OMClient() as om:
        response = {"found": False}
        candidates = (
            get_table_fqn_candidates(entity_fqn)
            if normalized_type == "table"
            else [entity_fqn]
        )
        for candidate in candidates:
            response = await om._get(
                f"/{ENTITY_TYPE_PATH[normalized_type]}/name/{quote(candidate, safe='')}",
                params={"fields": "owners"},
            )
            if response.get("found", True):
                break

    if not response.get("found", True):
        return []

    owners = response.get("owners", [])
    if not isinstance(owners, list):
        return []

    parsed: list[EntityOwner] = []
    for owner in owners:
        if not isinstance(owner, dict):
            continue
        owner_ref = owner.get("owner")
        owner_data = owner_ref if isinstance(owner_ref, dict) else owner
        parsed.append(
            EntityOwner(
                name=str(
                    owner_data.get("displayName") or owner_data.get("name") or "unknown"
                ),
                email=str(owner_data.get("email") or ""),
                type=_normalize_owner_type(owner.get("type") or owner_data.get("type")),
            )
        )

    return parsed
