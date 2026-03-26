"""Pytest fixtures for SynthForge tests."""
from __future__ import annotations

import json
import pytest
from typing import Any
from unittest.mock import MagicMock, patch

from core.types import DataSpec, DataType, FieldSpec, GeneratedDataset, ValidationResult


# ── Sample Specs ────────────────────────────────────────────────────────────

@pytest.fixture
def sample_tabular_spec() -> DataSpec:
    """E-commerce orders spec."""
    return DataSpec(
        data_type=DataType.TABULAR,
        name="orders",
        row_count=50,
        fields=[
            FieldSpec(name="order_id", dtype="str", unique=True, description="Unique order identifier"),
            FieldSpec(name="customer_name", dtype="str", description="Customer full name"),
            FieldSpec(name="email", dtype="str", description="Customer email"),
            FieldSpec(name="amount", dtype="float", min_val=10.0, max_val=5000.0),
            FieldSpec(name="quantity", dtype="int", min_val=1, max_val=20),
            FieldSpec(name="status", dtype="category", categories=["pending", "shipped", "delivered", "cancelled"]),
            FieldSpec(name="created_at", dtype="datetime", min_val="2024-01-01T00:00:00", max_val="2024-12-31T23:59:59"),
        ],
        constraints=["amount > 0 when quantity > 0"],
        context="E-commerce order data for a retail store",
        locale="en_US",
    )


@pytest.fixture
def sample_timeseries_spec() -> DataSpec:
    """Server metrics spec."""
    return DataSpec(
        data_type=DataType.TIMESERIES,
        name="server_metrics",
        row_count=100,
        fields=[
            FieldSpec(name="timestamp", dtype="datetime", min_val="2024-01-01T00:00:00", max_val="2024-01-02T00:00:00"),
            FieldSpec(name="server_id", dtype="category", categories=["srv-001", "srv-002", "srv-003"]),
            FieldSpec(name="cpu_usage", dtype="float", min_val=0, max_val=100),
            FieldSpec(name="memory_used_gb", dtype="float", min_val=0, max_val=32),
            FieldSpec(name="memory_total_gb", dtype="float", min_val=16, max_val=64),
        ],
        context="Real-time server monitoring data",
        locale="en_US",
    )


@pytest.fixture
def sample_nlp_spec() -> DataSpec:
    """Product reviews spec."""
    return DataSpec(
        data_type=DataType.NLP,
        name="product_reviews",
        row_count=20,
        fields=[
            FieldSpec(name="review_id", dtype="str", unique=True),
            FieldSpec(name="product_name", dtype="str", description="Product being reviewed"),
            FieldSpec(name="rating", dtype="int", min_val=1, max_val=5),
            FieldSpec(name="review_text", dtype="str", description="Detailed user review"),
            FieldSpec(name="sentiment", dtype="category", categories=["positive", "negative", "neutral"]),
        ],
        context="E-commerce product reviews with sentiment",
        locale="en_US",
    )


@pytest.fixture
def sample_log_spec() -> DataSpec:
    """API access logs spec."""
    return DataSpec(
        data_type=DataType.LOG,
        name="api_access_logs",
        row_count=100,
        fields=[
            FieldSpec(name="timestamp", dtype="datetime"),
            FieldSpec(name="method", dtype="category", categories=["GET", "POST", "PUT", "DELETE"]),
            FieldSpec(name="path", dtype="str"),
            FieldSpec(name="status_code", dtype="int", min_val=100, max_val=599),
            FieldSpec(name="response_time_ms", dtype="int", min_val=1, max_val=5000),
        ],
        context="HTTP API access logs",
        locale="en_US",
    )


@pytest.fixture
def sample_dataset(sample_tabular_spec: DataSpec) -> GeneratedDataset:
    """Sample generated dataset."""
    return GeneratedDataset(
        spec=sample_tabular_spec,
        records=[
            {"order_id": "ORD-001", "customer_name": "John Doe", "email": "john@example.com",
             "amount": 150.0, "quantity": 2, "status": "pending", "created_at": "2024-03-15T10:30:00"},
            {"order_id": "ORD-002", "customer_name": "Jane Smith", "email": "jane@example.com",
             "amount": 299.99, "quantity": 1, "status": "shipped", "created_at": "2024-03-16T14:20:00"},
            {"order_id": "ORD-003", "customer_name": "Bob Wilson", "email": "bob@example.com",
             "amount": 75.50, "quantity": 3, "status": "delivered", "created_at": "2024-03-17T09:15:00"},
        ],
        metadata={"generator": "tabular", "locale": "en_US"},
    )


# ── LLM Mocking ─────────────────────────────────────────────────────────────

@pytest.fixture
def mock_llm_response():
    """Factory fixture for mocking LLM responses."""
    def _mock(response_data: Any):
        with patch("core.llm.chat_json") as mock:
            mock.return_value = response_data
            yield mock
    return _mock


@pytest.fixture
def mock_chat_json():
    """Mock core.llm.chat_json for testing."""
    with patch("core.llm.chat_json") as mock:
        yield mock


@pytest.fixture
def mock_intent_parser_response() -> dict:
    """Standard response from intent parser."""
    return {
        "name": "test_dataset",
        "data_type": "tabular",
        "row_count": 50,
        "locale": "en_US",
        "context": "Test data for unit tests",
        "constraints": [],
        "fields": [
            {"name": "id", "dtype": "str", "unique": True, "nullable": False,
             "min_val": None, "max_val": None, "categories": [], "pattern": None,
             "foreign_key": None, "description": "Unique identifier"},
            {"name": "value", "dtype": "float", "unique": False, "nullable": False,
             "min_val": 0.0, "max_val": 100.0, "categories": [], "pattern": None,
             "foreign_key": None, "description": "Numeric value"},
        ],
    }


# ── Validation Fixtures ─────────────────────────────────────────────────────

@pytest.fixture
def passing_validation() -> ValidationResult:
    return ValidationResult(passed=True, score=0.95, issues=[], suggestions=[])


@pytest.fixture
def failing_validation() -> ValidationResult:
    return ValidationResult(
        passed=False,
        score=0.5,
        issues=["'amount': 5 değer min (10.0) altında.", "'status': geçersiz kategori değerleri var."],
        suggestions=["Amount değerlerini min/max aralığına çekin.", "Status alanı için geçerli kategoriler kullanın."],
    )


# ── Temp Directory ──────────────────────────────────────────────────────────

@pytest.fixture
def temp_output_dir(tmp_path):
    """Temporary directory for export tests."""
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    return str(output_dir)
