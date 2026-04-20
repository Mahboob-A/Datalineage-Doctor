from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class DQTestResult(BaseModel):
    """Normalized DQ test execution result."""

    test_case_fqn: str
    result: Literal["Passed", "Failed", "Aborted"]
    timestamp: datetime
    test_type: str
