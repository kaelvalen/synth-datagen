"""Tests for core.types module."""
from __future__ import annotations

import pytest
from core.types import (
    DataType, ExportFormat, FieldSpec, DataSpec, 
    GeneratedDataset, ValidationResult, PipelineResult
)


class TestDataType:
    def test_enum_values(self):
        assert DataType.TABULAR.value == "tabular"
        assert DataType.NLP.value == "nlp"
        assert DataType.TIMESERIES.value == "timeseries"
        assert DataType.LOG.value == "log"

    def test_from_string(self):
        assert DataType("tabular") == DataType.TABULAR
        assert DataType("nlp") == DataType.NLP

    def test_invalid_type_raises(self):
        with pytest.raises(ValueError):
            DataType("invalid")


class TestExportFormat:
    def test_enum_values(self):
        assert ExportFormat.CSV.value == "csv"
        assert ExportFormat.JSONL.value == "jsonl"
        assert ExportFormat.PARQUET.value == "parquet"
        assert ExportFormat.TXT.value == "txt"


class TestFieldSpec:
    def test_defaults(self):
        field = FieldSpec(name="test", dtype="str")
        assert field.nullable is False
        assert field.unique is False
        assert field.min_val is None
        assert field.max_val is None
        assert field.categories == []
        assert field.pattern is None
        assert field.foreign_key is None
        assert field.description == ""

    def test_full_spec(self):
        field = FieldSpec(
            name="price",
            dtype="float",
            nullable=True,
            unique=False,
            min_val=0.01,
            max_val=9999.99,
            categories=[],
            pattern=None,
            foreign_key=None,
            description="Product price in USD"
        )
        assert field.min_val == 0.01
        assert field.max_val == 9999.99
        assert field.description == "Product price in USD"

    def test_category_field(self):
        field = FieldSpec(
            name="status",
            dtype="category",
            categories=["active", "inactive", "pending"]
        )
        assert len(field.categories) == 3
        assert "active" in field.categories


class TestDataSpec:
    def test_minimal_spec(self):
        spec = DataSpec(
            data_type=DataType.TABULAR,
            name="test",
            row_count=10,
            fields=[]
        )
        assert spec.constraints == []
        assert spec.context == ""
        assert spec.locale == "en_US"

    def test_full_spec(self, sample_tabular_spec):
        assert sample_tabular_spec.data_type == DataType.TABULAR
        assert sample_tabular_spec.name == "orders"
        assert sample_tabular_spec.row_count == 50
        assert len(sample_tabular_spec.fields) == 7


class TestGeneratedDataset:
    def test_creation(self, sample_tabular_spec):
        dataset = GeneratedDataset(
            spec=sample_tabular_spec,
            records=[{"id": "1", "value": 42}],
            metadata={"generator": "test"}
        )
        assert len(dataset.records) == 1
        assert dataset.metadata["generator"] == "test"

    def test_empty_records(self, sample_tabular_spec):
        dataset = GeneratedDataset(
            spec=sample_tabular_spec,
            records=[]
        )
        assert dataset.records == []
        assert dataset.metadata == {}


class TestValidationResult:
    def test_passing_result(self):
        result = ValidationResult(passed=True, score=1.0)
        assert result.passed is True
        assert result.issues == []
        assert result.suggestions == []

    def test_failing_result(self):
        result = ValidationResult(
            passed=False,
            issues=["Error 1", "Error 2"],
            suggestions=["Fix 1"],
            score=0.3
        )
        assert result.passed is False
        assert len(result.issues) == 2
        assert result.score == 0.3


class TestPipelineResult:
    def test_creation(self, sample_dataset, passing_validation):
        result = PipelineResult(
            dataset=sample_dataset,
            validation=passing_validation,
            iterations=1,
            export_path="/tmp/test.csv"
        )
        assert result.iterations == 1
        assert result.export_path == "/tmp/test.csv"
