from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class DataType(str, Enum):
    TABULAR = "tabular"
    NLP = "nlp"
    TIMESERIES = "timeseries"
    LOG = "log"


class ExportFormat(str, Enum):
    CSV = "csv"
    JSONL = "jsonl"
    PARQUET = "parquet"
    TXT = "txt"
    SQL = "sql"
    XLSX = "xlsx"


@dataclass
class FieldSpec:
    name: str
    dtype: str                        # int, float, str, bool, datetime, category
    nullable: bool = False
    unique: bool = False
    min_val: Any = None
    max_val: Any = None
    categories: list[str] = field(default_factory=list)
    pattern: str | None = None        # regex for str fields
    foreign_key: str | None = None    # "table.column" reference
    description: str = ""


@dataclass
class DataSpec:
    """Intent parser'dan çıkan ham spec — generator'a girer."""
    data_type: DataType
    name: str
    row_count: int
    fields: list[FieldSpec]
    constraints: list[str] = field(default_factory=list)   # cross-field kurallar
    context: str = ""                                       # domain bilgisi
    locale: str = "en_US"


@dataclass
class GeneratedDataset:
    spec: DataSpec
    records: list[dict[str, Any]]
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ValidationResult:
    passed: bool
    issues: list[str] = field(default_factory=list)
    suggestions: list[str] = field(default_factory=list)
    score: float = 1.0   # 0.0 – 1.0


@dataclass
class PipelineResult:
    dataset: GeneratedDataset
    validation: ValidationResult
    iterations: int
    export_path: str | None = None
