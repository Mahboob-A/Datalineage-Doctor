import json
import re

from pydantic import ValidationError

from agent.schemas.report import RCAReport
from app.models import ConfidenceLabel

FENCED_JSON_PATTERN = re.compile(
    r"```(?:json)?\s*(\{.*?\})\s*```", re.IGNORECASE | re.DOTALL
)


class RCAParseError(ValueError):
    """Raised when the final LLM message cannot be parsed into an RCAReport."""

    def __init__(self, content: str):
        super().__init__("Failed to parse RCA report from model output")
        self.content = content


def derive_confidence_label(confidence_score: float) -> ConfidenceLabel:
    """Map confidence score to the canonical confidence label."""
    if confidence_score >= 0.85:
        return ConfidenceLabel.HIGH
    if confidence_score >= 0.60:
        return ConfidenceLabel.MEDIUM
    return ConfidenceLabel.LOW


def extract_json_from_content(content: str) -> dict[str, object]:
    """Extract a JSON object from plain text or markdown-fenced model output."""
    text = content.strip()
    fenced_match = FENCED_JSON_PATTERN.search(text)
    if fenced_match is not None:
        candidate = fenced_match.group(1)
    else:
        start = text.find("{")
        end = text.rfind("}")
        if start == -1 or end == -1 or end < start:
            raise ValueError("No JSON object found in content")
        candidate = text[start : end + 1]

    parsed = json.loads(candidate)
    if not isinstance(parsed, dict):
        raise ValueError("Extracted JSON content must be an object")
    return parsed


def parse_rca_report(content: str) -> RCAReport:
    """Validate and normalize the model output into an RCAReport instance."""
    try:
        data = extract_json_from_content(content)
        report = RCAReport.model_validate(data)
    except (ValidationError, ValueError, json.JSONDecodeError) as exc:
        raise RCAParseError(content) from exc

    report.confidence_label = derive_confidence_label(report.confidence_score)
    return report
