from __future__ import annotations
import math
import random
import re
from datetime import datetime, timedelta
from typing import Any

from core.types import DataSpec, FieldSpec, GeneratedDataset

# ── Sabitler ────────────────────────────────────────────────────────────────

# Gerçekçi örnekleme aralıkları (saniye)
INTERVAL_PRESETS = {
    "realtime":  15,       # 15 saniye
    "minute":    60,       # 1 dakika
    "5min":      300,
    "15min":     900,
    "hourly":    3600,
}

DEFAULT_INTERVAL_SEC = 60   # 1 dakika varsayılan


# ── Ana generator ───────────────────────────────────────────────────────────

def generate(spec: DataSpec) -> GeneratedDataset:
    """
    Gerçekçi zaman serisi verisi üretir.

    Özellikler:
    - Her entity (server, sensor, vs.) kendi bağımsız sinyal serisine sahip
    - Kayıtlar gerçekçi örnekleme aralığında (default: 1 dk) üretilir
    - Cross-field korelasyon: matematiksel olarak tutarlı türetilmiş alanlar
    - Anomali enjeksiyonu: %3 olasılıkla spike/drop
    """
    ts_field = _find_timestamp_field(spec)
    entity_field = _find_entity_field(spec)
    entities = _get_entities(entity_field, spec)

    interval_sec = _infer_interval(spec)
    rows_per_entity = max(1, spec.row_count // len(entities))

    # Her entity için bağımsız sinyal parametreleri
    numeric_fields = [
        f for f in spec.fields
        if f.dtype in ("int", "float") and f.name != ts_field.name
    ]
    entity_params: dict[str, dict[str, dict]] = {
        entity: {f.name: _signal_params_for_field(f) for f in numeric_fields}
        for entity in entities
    }

    records: list[dict[str, Any]] = []
    start = _parse_start(ts_field)

    for entity in entities:
        ts = start + timedelta(seconds=random.randint(0, interval_sec))  # hafif jitter
        params = entity_params[entity]

        for step in range(rows_per_entity):
            row: dict[str, Any] = {ts_field.name: ts.isoformat()}

            if entity_field:
                row[entity_field.name] = entity

            # Numeric alanlar — sinyal üret
            generated_numeric: dict[str, float] = {}
            for field in numeric_fields:
                # "total", "max", "capacity" gibi sabit alanlar entity başına sabittir
                if _is_static_field(field.name):
                    if step == 0:
                        val = _static_value(field)
                        params[field.name]["_static"] = val
                    else:
                        val = params[field.name].get("_static", _static_value(field))
                else:
                    val = _signal_value(step, rows_per_entity, params[field.name], field)
                generated_numeric[field.name] = val
                row[field.name] = val

            # Cross-field korelasyon düzeltmesi
            row = _apply_correlations(row, generated_numeric, spec.fields)

            # Diğer alan tipleri
            for field in spec.fields:
                if field.name in row:
                    continue
                if field.dtype == "category" and field.categories:
                    row[field.name] = random.choice(field.categories)
                elif field.dtype == "bool":
                    row[field.name] = random.random() > 0.5
                elif field.dtype == "str":
                    row[field.name] = f"{field.name}_{step}"

            records.append(row)

            # Gerçekçi timestamp artışı: sabit interval + küçük jitter
            jitter = random.gauss(0, interval_sec * 0.02)
            ts += timedelta(seconds=max(1, interval_sec + jitter))

    # Tüm entity'leri timestamp'e göre sırala
    records.sort(key=lambda r: r.get(ts_field.name, ""))

    return GeneratedDataset(
        spec=spec,
        records=records[: spec.row_count],
        metadata={
            "generator": "timeseries",
            "entities": entities,
            "interval_sec": interval_sec,
            "rows_per_entity": rows_per_entity,
        },
    )


# ── Yardımcı fonksiyonlar ───────────────────────────────────────────────────

def _find_timestamp_field(spec: DataSpec) -> FieldSpec:
    for f in spec.fields:
        if f.dtype == "datetime":
            return f
    return FieldSpec(
        name="timestamp",
        dtype="datetime",
        min_val="2024-01-01T00:00:00",
        max_val="2025-01-01T00:00:00",
    )


def _find_entity_field(spec: DataSpec) -> FieldSpec | None:
    """server_id, device_id, sensor_id gibi entity tanımlayıcı alanı bul."""
    entity_keywords = ("_id", "_name", "server", "device", "sensor", "host", "node", "instance")
    for f in spec.fields:
        if f.dtype in ("str", "category") and any(kw in f.name.lower() for kw in entity_keywords):
            return f
    return None


def _get_entities(field: FieldSpec | None, spec: DataSpec) -> list[str]:
    if field is None:
        return ["entity_1"]
    if field.categories:
        return field.categories
    # Kategori yoksa spec'ten entity sayısını tahmin et
    n = max(1, min(10, spec.row_count // 20))
    prefix = field.name.replace("_id", "").replace("_name", "")
    return [f"{prefix}-{str(i+1).zfill(3)}" for i in range(n)]


def _infer_interval(spec: DataSpec) -> int:
    """Context'ten örnekleme aralığını tahmin et."""
    ctx = spec.context.lower()
    if any(w in ctx for w in ("realtime", "real-time", "streaming", "15s")):
        return INTERVAL_PRESETS["realtime"]
    if any(w in ctx for w in ("5 min", "5min", "5-min")):
        return INTERVAL_PRESETS["5min"]
    if any(w in ctx for w in ("15 min", "15min")):
        return INTERVAL_PRESETS["15min"]
    if any(w in ctx for w in ("hour", "saatlik")):
        return INTERVAL_PRESETS["hourly"]
    return DEFAULT_INTERVAL_SEC


def _parse_start(ts_field: FieldSpec) -> datetime:
    lo_str = ts_field.min_val or "2024-01-01T00:00:00"
    try:
        return datetime.fromisoformat(lo_str)
    except ValueError:
        return datetime(2024, 1, 1)


def _signal_params_for_field(field: FieldSpec) -> dict:
    """Alan ismine göre domain-aware sinyal parametreleri."""
    name = field.name.lower()
    lo = float(field.min_val) if field.min_val is not None else 0.0
    hi = float(field.max_val) if field.max_val is not None else 100.0
    mid = (lo + hi) / 2

    # CPU / yük metrikleri: 20-80 arası dalgalı
    if any(k in name for k in ("cpu", "load", "util")):
        return {"base": mid * 0.6, "trend": 0.0, "amplitude": mid * 0.3,
                "period": 288, "noise_std": mid * 0.08, "lo": lo, "hi": hi}

    # Bellek: daha yavaş değişim
    if any(k in name for k in ("mem", "memory", "ram", "heap")):
        return {"base": mid * 0.5, "trend": 0.001, "amplitude": mid * 0.1,
                "period": 1440, "noise_std": mid * 0.03, "lo": lo, "hi": hi}

    # Latency / response time: sağa çarpık, spike'lı
    if any(k in name for k in ("latency", "response", "duration", "ms", "rtt")):
        return {"base": lo + (hi - lo) * 0.15, "trend": 0.0, "amplitude": (hi - lo) * 0.1,
                "period": 288, "noise_std": (hi - lo) * 0.05, "lo": lo, "hi": hi,
                "spike_prob": 0.05}

    # Genel
    return {"base": mid, "trend": random.uniform(-0.01, 0.01), "amplitude": (hi - lo) * 0.2,
            "period": 288, "noise_std": (hi - lo) * 0.05, "lo": lo, "hi": hi}


def _signal_value(idx: int, total: int, params: dict, field: FieldSpec) -> float | int:
    base = params["base"]
    trend = params.get("trend", 0) * idx
    seasonal = params["amplitude"] * math.sin(2 * math.pi * idx / max(params["period"], 1))
    noise = random.gauss(0, params["noise_std"])

    # Spike enjeksiyonu
    if random.random() < params.get("spike_prob", 0.03):
        noise *= random.uniform(3, 8) * random.choice([-1, 1])

    val = base + trend + seasonal + noise
    val = max(params["lo"], min(params["hi"], val))

    return int(round(val)) if field.dtype == "int" else round(val, 2)


def _apply_correlations(
    row: dict[str, Any],
    numeric: dict[str, float],
    fields: list[FieldSpec],
) -> dict[str, Any]:
    """
    Matematiksel olarak tutarlı türetilmiş alanları düzelt.
    Örnek: memory_usage_percent = memory_used_gb / memory_total_gb * 100
    """
    field_names = {f.name for f in fields}

    # memory_used / memory_total → memory_usage_percent
    used_key = _find_key(numeric, ("memory_used", "mem_used", "used_gb", "memory_used_gb"))
    total_key = _find_key(row, ("memory_total", "mem_total", "total_gb", "memory_total_gb"))
    pct_key = _find_key(row, ("memory_usage_percent", "mem_percent", "memory_percent"))

    if used_key and total_key and pct_key:
        total = float(row[total_key])
        if total > 0:
            row[pct_key] = round(float(row[used_key]) / total * 100, 1)

    # cpu_usage ↔ load_average korelasyonu (yüksek CPU → yüksek load)
    cpu_key = _find_key(numeric, ("cpu_usage", "cpu_percent", "cpu_util"))
    load_key = _find_key(row, ("load_average", "load_avg", "load1"))
    if cpu_key and load_key:
        cpu_val = float(numeric[cpu_key])
        # load ≈ cpu/100 * core_count (varsay 4 core)
        row[load_key] = round(cpu_val / 100 * 4 * random.uniform(0.8, 1.2), 2)

    # memory_used clamp: used asla total'ı geçemez
    if used_key and total_key:
        total_val = float(row[total_key])
        used_val = float(row[used_key])
        # used, total'ın %5 ile %95'i arasında olsun
        used_clamped = round(max(total_val * 0.05, min(total_val * 0.95, used_val)), 2)
        row[used_key] = used_clamped
        # pct'yi güncel used ile yeniden hesapla
        if pct_key and total_val > 0:
            row[pct_key] = round(used_clamped / total_val * 100, 1)

    return row


def _find_key(d: dict, candidates: tuple) -> str | None:
    for c in candidates:
        for k in d:
            if c in k.lower():
                return k
    return None


def _is_static_field(name: str) -> bool:
    """Entity başına sabit olan alanlar — zaman içinde değişmez."""
    static_keywords = ("total", "max", "capacity", "limit", "allocated", "provisioned")
    name_lower = name.lower()
    return any(kw in name_lower for kw in static_keywords)


def _static_value(field: FieldSpec) -> float:
    """Sabit alan için gerçekçi bir değer seç."""
    # Tanınan preset değerler (bellek boyutları, disk kapasiteleri)
    name = field.name.lower()
    if "memory" in name or "ram" in name or "mem" in name:
        presets = [4.0, 8.0, 16.0, 32.0, 64.0, 128.0]
    elif "disk" in name or "storage" in name:
        presets = [50.0, 100.0, 200.0, 500.0, 1000.0]
    else:
        presets = None

    lo = float(field.min_val) if field.min_val is not None else 0.0
    hi = float(field.max_val) if field.max_val is not None else 100.0

    if presets:
        valid = [p for p in presets if lo <= p <= hi]
        if valid:
            return random.choice(valid)

    # Bounds içinde round bir sayı seç
    return round(random.uniform(lo * 0.5 + hi * 0.5, hi * 0.9), 1)
