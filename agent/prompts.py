SYSTEM_PROMPT = """You are the DataLineage Doctor RCA assistant.
Use available tools and provide structured evidence-backed output.
"""


def build_user_message(table_fqn: str, test_case_fqn: str, triggered_at: str) -> str:
    return f"Investigate table={table_fqn}, test_case={test_case_fqn}, triggered_at={triggered_at}."
