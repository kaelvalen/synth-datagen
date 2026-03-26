from __future__ import annotations
import csv
import json
import os
from pathlib import Path
from typing import Any

from core.types import ExportFormat, GeneratedDataset


def export(
    dataset: GeneratedDataset,
    fmt: ExportFormat,
    output_dir: str = "./output",
    filename: str | None = None,
) -> str:
    """
    GeneratedDataset'i belirtilen formata kaydeder.
    Kaydedilen dosyanın yolunu döner.
    """
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    base_name = filename or dataset.spec.name
    ext = fmt.value
    path = os.path.join(output_dir, f"{base_name}.{ext}")

    records = dataset.records

    if fmt == ExportFormat.CSV:
        _to_csv(records, path)
    elif fmt == ExportFormat.JSONL:
        _to_jsonl(records, path)
    elif fmt == ExportFormat.PARQUET:
        _to_parquet(records, path)
    elif fmt == ExportFormat.TXT:
        _to_txt(records, dataset.spec, path)
    else:
        raise ValueError(f"Desteklenmeyen format: {fmt}")

    size_kb = os.path.getsize(path) / 1024
    print(f"[exporter] ✓ {path} ({len(records)} kayıt, {size_kb:.1f} KB)")
    return path


def _to_csv(records: list[dict], path: str) -> None:
    if not records:
        return
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=records[0].keys())
        writer.writeheader()
        writer.writerows(records)


def _to_jsonl(records: list[dict], path: str) -> None:
    with open(path, "w", encoding="utf-8") as f:
        for record in records:
            f.write(json.dumps(record, ensure_ascii=False, default=str) + "\n")


def _to_parquet(records: list[dict], path: str) -> None:
    try:
        import pandas as pd
        df = pd.DataFrame(records)
        df.to_parquet(path, index=False)
    except ImportError:
        # pandas/pyarrow yoksa JSONL'e düş
        fallback = path.replace(".parquet", ".jsonl")
        print(f"[exporter] pandas/pyarrow bulunamadı, JSONL'e düşülüyor: {fallback}")
        _to_jsonl(records, fallback)
        return


def _to_txt(records: list[dict], spec: Any, path: str) -> None:
    """NLP veri setleri için düz metin çıktısı."""
    with open(path, "w", encoding="utf-8") as f:
        for i, record in enumerate(records, 1):
            # Her kaydı alan adı olmadan tek blok yaz (metin verisi için)
            text_fields = [
                str(v)
                for k, v in record.items()
                if isinstance(v, str) and len(str(v)) > 20
            ]
            if text_fields:
                f.write("\n".join(text_fields) + "\n\n---\n\n")
            else:
                f.write(json.dumps(record, ensure_ascii=False, default=str) + "\n")
