"""Tests for validator module."""
from __future__ import annotations

import pytest
from unittest.mock import patch

from core.types import DataSpec, DataType, FieldSpec, GeneratedDataset, ValidationResult
from validators.checker import validate, _rule_based_check


class TestRuleBasedValidation:
    def test_empty_records_fails(self, sample_tabular_spec):
        issues = _rule_based_check(sample_tabular_spec, [])
        assert any("Hiç kayıt üretilmedi" in i for i in issues)

    def test_nullable_violation(self):
        spec = DataSpec(
            data_type=DataType.TABULAR,
            name="test",
            row_count=3,
            fields=[
                FieldSpec(name="required_field", dtype="str", nullable=False),
            ]
        )
        records = [
            {"required_field": "value1"},
            {"required_field": None},  # Violation
            {"required_field": "value3"},
        ]
        issues = _rule_based_check(spec, records)
        assert any("null değer" in i for i in issues)

    def test_unique_violation(self):
        spec = DataSpec(
            data_type=DataType.TABULAR,
            name="test",
            row_count=3,
            fields=[
                FieldSpec(name="id", dtype="str", unique=True),
            ]
        )
        records = [
            {"id": "1"},
            {"id": "2"},
            {"id": "1"},  # Duplicate
        ]
        issues = _rule_based_check(spec, records)
        assert any("unique=true" in i for i in issues)

    def test_type_mismatch(self):
        spec = DataSpec(
            data_type=DataType.TABULAR,
            name="test",
            row_count=2,
            fields=[
                FieldSpec(name="count", dtype="int"),
            ]
        )
        records = [
            {"count": 42},
            {"count": "not an int"},  # Type mismatch
        ]
        issues = _rule_based_check(spec, records)
        assert any("beklenen tip" in i for i in issues)

    def test_range_violation_min(self):
        spec = DataSpec(
            data_type=DataType.TABULAR,
            name="test",
            row_count=3,
            fields=[
                FieldSpec(name="score", dtype="int", min_val=0, max_val=100),
            ]
        )
        records = [
            {"score": 50},
            {"score": -10},  # Below min
            {"score": 75},
        ]
        issues = _rule_based_check(spec, records)
        assert any("min" in i for i in issues)

    def test_range_violation_max(self):
        spec = DataSpec(
            data_type=DataType.TABULAR,
            name="test",
            row_count=3,
            fields=[
                FieldSpec(name="score", dtype="int", min_val=0, max_val=100),
            ]
        )
        records = [
            {"score": 50},
            {"score": 150},  # Above max
            {"score": 75},
        ]
        issues = _rule_based_check(spec, records)
        assert any("max" in i for i in issues)

    def test_category_violation(self):
        spec = DataSpec(
            data_type=DataType.TABULAR,
            name="test",
            row_count=3,
            fields=[
                FieldSpec(name="status", dtype="category", categories=["a", "b", "c"]),
            ]
        )
        records = [
            {"status": "a"},
            {"status": "x"},  # Invalid category
            {"status": "b"},
        ]
        issues = _rule_based_check(spec, records)
        assert any("kategoriler dışında" in i for i in issues)

    def test_datetime_format_check(self):
        spec = DataSpec(
            data_type=DataType.TABULAR,
            name="test",
            row_count=2,
            fields=[
                FieldSpec(name="created_at", dtype="datetime"),
            ]
        )
        records = [
            {"created_at": "2024-01-15T10:30:00"},
            {"created_at": "invalid-date"},  # Invalid format
        ]
        issues = _rule_based_check(spec, records)
        assert any("datetime" in i.lower() for i in issues)

    def test_diversity_check(self):
        spec = DataSpec(
            data_type=DataType.TABULAR,
            name="test",
            row_count=10,
            fields=[
                FieldSpec(name="category", dtype="str"),
            ]
        )
        # 80% same value
        records = [{"category": "same"} for _ in range(8)]
        records.extend([{"category": "other"}, {"category": "another"}])
        
        issues = _rule_based_check(spec, records)
        assert any("çeşitlilik düşük" in i for i in issues)


class TestValidateWithLLM:
    def test_validate_passes_good_data(self, sample_dataset, mock_chat_json):
        mock_chat_json.return_value = {
            "score": 0.95,
            "issues": [],
            "suggestions": []
        }
        
        result = validate(sample_dataset)
        assert isinstance(result, ValidationResult)
        assert result.score >= 0.7

    def test_validate_fails_bad_data(self, sample_tabular_spec, mock_chat_json):
        mock_chat_json.return_value = {
            "score": 0.4,
            "issues": ["Data lacks diversity", "Unrealistic values"],
            "suggestions": ["Add more variation"]
        }
        
        # Create dataset with issues
        bad_dataset = GeneratedDataset(
            spec=sample_tabular_spec,
            records=[
                {"order_id": "1", "customer_name": None, "email": "bad",
                 "amount": -100, "quantity": 0, "status": "invalid",
                 "created_at": "2024-01-01"},
            ]
        )
        
        result = validate(bad_dataset)
        assert result.passed is False
        assert len(result.issues) > 0

    def test_validate_handles_llm_failure(self, sample_dataset, mock_chat_json):
        mock_chat_json.side_effect = ValueError("LLM error")
        
        # Should still return a result using fallback
        result = validate(sample_dataset)
        assert isinstance(result, ValidationResult)
