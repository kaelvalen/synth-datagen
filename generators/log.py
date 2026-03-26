from __future__ import annotations
import random
from datetime import datetime, timedelta
from typing import Any

from core.types import DataSpec, GeneratedDataset

LOG_LEVELS = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
HTTP_METHODS = ["GET", "POST", "PUT", "DELETE", "PATCH"]
HTTP_STATUS = [200, 200, 200, 201, 204, 301, 400, 401, 403, 404, 500, 502, 503]

SERVICES = [
    "auth-service", "api-gateway", "user-service", "payment-service",
    "notification-service", "search-service", "cache-layer", "db-proxy",
]

PATHS = [
    "/api/v1/users", "/api/v1/auth/login", "/api/v1/products",
    "/api/v1/orders", "/health", "/metrics", "/api/v1/search",
    "/api/v1/payments", "/api/v1/notifications",
]

ERROR_MESSAGES = {
    "DEBUG": ["Cache hit for key {key}", "Query executed in {ms}ms", "Connection pool size: {n}"],
    "INFO": ["Request processed successfully", "User {id} authenticated", "Session created: {sid}"],
    "WARNING": ["High memory usage: {pct}%", "Slow query detected: {ms}ms", "Retry attempt {n}/3"],
    "ERROR": ["Database connection failed", "Timeout after {ms}ms", "Invalid token: {reason}"],
    "CRITICAL": ["Service unavailable", "Out of memory", "Disk full: {pct}% used"],
}


def generate(spec: DataSpec) -> GeneratedDataset:
    context = spec.context.lower()

    # Context'ten servis türü tahmin et
    if "http" in context or "web" in context or "api" in context:
        generator = _http_log
    elif "auth" in context or "security" in context:
        generator = _auth_log
    else:
        generator = _app_log

    start = datetime(2024, 1, 1)
    records: list[dict[str, Any]] = []
    current_ts = start

    for i in range(spec.row_count):
        # Gerçekçi zaman aralığı: bazı eventler çok yakın, bazıları uzak
        gap = random.choices(
            [timedelta(milliseconds=random.randint(1, 500)),
             timedelta(seconds=random.randint(1, 30)),
             timedelta(minutes=random.randint(1, 10))],
            weights=[0.6, 0.3, 0.1],
        )[0]
        current_ts += gap

        row = generator(current_ts, i)
        # Spec'teki custom alanlara da yer aç
        for field in spec.fields:
            if field.name not in row:
                if field.categories:
                    row[field.name] = random.choice(field.categories)
                elif field.dtype == "int":
                    row[field.name] = random.randint(
                        int(field.min_val or 0), int(field.max_val or 9999)
                    )
                elif field.dtype == "bool":
                    row[field.name] = random.choice([True, False])

        records.append(row)

    return GeneratedDataset(
        spec=spec,
        records=records,
        metadata={"generator": "log", "log_type": generator.__name__},
    )


def _app_log(ts: datetime, idx: int) -> dict:
    level = random.choices(LOG_LEVELS, weights=[10, 50, 20, 15, 5])[0]
    templates = ERROR_MESSAGES[level]
    msg_template = random.choice(templates)
    message = msg_template.format(
        key=f"key:{random.randint(1000, 9999)}",
        ms=random.randint(1, 5000),
        n=random.randint(1, 100),
        id=f"usr_{random.randint(1, 9999)}",
        sid=f"sess_{random.randint(10000, 99999)}",
        pct=random.randint(50, 99),
        reason=random.choice(["expired", "malformed", "revoked"]),
    )
    return {
        "timestamp": ts.isoformat(),
        "level": level,
        "service": random.choice(SERVICES),
        "message": message,
        "trace_id": f"trace-{random.randint(100000, 999999)}",
    }


def _http_log(ts: datetime, idx: int) -> dict:
    method = random.choices(HTTP_METHODS, weights=[50, 25, 10, 10, 5])[0]
    status = random.choice(HTTP_STATUS)
    return {
        "timestamp": ts.isoformat(),
        "method": method,
        "path": random.choice(PATHS),
        "status_code": status,
        "response_time_ms": random.randint(5, 3000),
        "ip": f"{random.randint(1,254)}.{random.randint(0,254)}.{random.randint(0,254)}.{random.randint(1,254)}",
        "user_agent": f"Mozilla/5.0 (compatible; bot/{random.randint(1,5)}.0)",
        "service": random.choice(SERVICES),
        "bytes_sent": random.randint(128, 65536),
    }


def _auth_log(ts: datetime, idx: int) -> dict:
    events = ["login_success", "login_failed", "logout", "token_refresh",
              "password_reset", "mfa_challenge", "session_expired"]
    weights = [40, 20, 15, 10, 5, 7, 3]
    event = random.choices(events, weights=weights)[0]
    return {
        "timestamp": ts.isoformat(),
        "event_type": event,
        "user_id": f"usr_{random.randint(1, 9999)}",
        "ip": f"{random.randint(1,254)}.{random.randint(0,254)}.{random.randint(0,254)}.{random.randint(1,254)}",
        "success": event not in ("login_failed", "session_expired"),
        "latency_ms": random.randint(10, 500),
        "service": "auth-service",
    }
