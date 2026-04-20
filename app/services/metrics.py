from prometheus_client import CONTENT_TYPE_LATEST, Counter, Gauge, Histogram, generate_latest

rca_requests_total = Counter("rca_requests_total", "Total RCA requests", ["status"])
rca_duration_seconds = Histogram("rca_duration_seconds", "RCA run duration")
rca_tool_calls_total = Counter("rca_tool_calls_total", "Total tool calls", ["tool_name"])
rca_confidence_score = Gauge("rca_confidence_score", "Latest RCA confidence score")
blast_radius_size = Histogram("blast_radius_size", "Blast radius size")
rca_errors_total = Counter("rca_errors_total", "Total RCA errors", ["error_type"])


def get_metrics_payload() -> tuple[bytes, str]:
    return generate_latest(), CONTENT_TYPE_LATEST
