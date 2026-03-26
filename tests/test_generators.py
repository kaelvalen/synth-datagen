"""Tests for generator modules."""
from __future__ import annotations

import pytest
from datetime import datetime
from unittest.mock import patch

from core.types import DataSpec, DataType, FieldSpec, GeneratedDataset
from generators import tabular, timeseries, log


class TestTabularGenerator:
    def test_generate_returns_dataset(self, sample_tabular_spec):
        dataset = tabular.generate(sample_tabular_spec)
        assert isinstance(dataset, GeneratedDataset)
        assert len(dataset.records) == sample_tabular_spec.row_count

    def test_respects_row_count(self, sample_tabular_spec):
        sample_tabular_spec.row_count = 25
        dataset = tabular.generate(sample_tabular_spec)
        assert len(dataset.records) == 25

    def test_unique_field_has_unique_values(self, sample_tabular_spec):
        dataset = tabular.generate(sample_tabular_spec)
        order_ids = [r["order_id"] for r in dataset.records]
        assert len(order_ids) == len(set(order_ids))

    def test_category_field_uses_categories(self, sample_tabular_spec):
        dataset = tabular.generate(sample_tabular_spec)
        valid_statuses = {"pending", "shipped", "delivered", "cancelled"}
        for record in dataset.records:
            assert record["status"] in valid_statuses

    def test_int_field_respects_range(self, sample_tabular_spec):
        dataset = tabular.generate(sample_tabular_spec)
        for record in dataset.records:
            assert 1 <= record["quantity"] <= 20

    def test_float_field_respects_range(self, sample_tabular_spec):
        dataset = tabular.generate(sample_tabular_spec)
        for record in dataset.records:
            assert 10.0 <= record["amount"] <= 5000.0

    def test_datetime_field_is_valid_iso(self, sample_tabular_spec):
        dataset = tabular.generate(sample_tabular_spec)
        for record in dataset.records:
            dt = datetime.fromisoformat(record["created_at"])
            assert dt.year == 2024

    def test_semantic_email_generation(self, sample_tabular_spec):
        dataset = tabular.generate(sample_tabular_spec)
        for record in dataset.records:
            assert "@" in record["email"]

    def test_locale_support(self, sample_tabular_spec):
        sample_tabular_spec.locale = "tr_TR"
        dataset = tabular.generate(sample_tabular_spec)
        assert dataset.metadata["locale"] == "tr_TR"
        assert len(dataset.records) == sample_tabular_spec.row_count


class TestTimeseriesGenerator:
    def test_generate_returns_dataset(self, sample_timeseries_spec):
        dataset = timeseries.generate(sample_timeseries_spec)
        assert isinstance(dataset, GeneratedDataset)

    def test_timestamps_are_ordered(self, sample_timeseries_spec):
        dataset = timeseries.generate(sample_timeseries_spec)
        timestamps = [r["timestamp"] for r in dataset.records]
        assert timestamps == sorted(timestamps)

    def test_entities_are_distributed(self, sample_timeseries_spec):
        dataset = timeseries.generate(sample_timeseries_spec)
        server_ids = set(r["server_id"] for r in dataset.records)
        assert len(server_ids) >= 2

    def test_cpu_usage_in_range(self, sample_timeseries_spec):
        dataset = timeseries.generate(sample_timeseries_spec)
        for record in dataset.records:
            assert 0 <= record["cpu_usage"] <= 100

    def test_memory_correlation(self, sample_timeseries_spec):
        """Memory used should not exceed total."""
        dataset = timeseries.generate(sample_timeseries_spec)
        for record in dataset.records:
            if "memory_used_gb" in record and "memory_total_gb" in record:
                assert record["memory_used_gb"] <= record["memory_total_gb"]

    def test_metadata_contains_entities(self, sample_timeseries_spec):
        dataset = timeseries.generate(sample_timeseries_spec)
        assert "entities" in dataset.metadata
        assert "interval_sec" in dataset.metadata


class TestLogGenerator:
    def test_generate_returns_dataset(self, sample_log_spec):
        dataset = log.generate(sample_log_spec)
        assert isinstance(dataset, GeneratedDataset)
        assert len(dataset.records) == sample_log_spec.row_count

    def test_timestamps_are_sequential(self, sample_log_spec):
        dataset = log.generate(sample_log_spec)
        timestamps = [r["timestamp"] for r in dataset.records]
        for i in range(1, len(timestamps)):
            assert timestamps[i] >= timestamps[i-1]

    def test_log_levels_distribution(self):
        """Log levels should follow realistic distribution."""
        spec = DataSpec(
            data_type=DataType.LOG,
            name="app_logs",
            row_count=500,
            fields=[
                FieldSpec(name="timestamp", dtype="datetime"),
                FieldSpec(name="level", dtype="category", 
                         categories=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]),
                FieldSpec(name="message", dtype="str"),
            ],
            context="Application logs",
        )
        dataset = log.generate(spec)
        levels = [r.get("level") for r in dataset.records if r.get("level")]
        
        # INFO should be most common in app logs
        if levels:
            from collections import Counter
            counts = Counter(levels)
            assert counts.get("INFO", 0) >= counts.get("CRITICAL", 0)

    def test_http_log_generation(self):
        spec = DataSpec(
            data_type=DataType.LOG,
            name="http_logs",
            row_count=100,
            fields=[
                FieldSpec(name="timestamp", dtype="datetime"),
                FieldSpec(name="status_code", dtype="int", min_val=100, max_val=599),
            ],
            context="HTTP API access logs",
        )
        dataset = log.generate(spec)
        assert "method" in dataset.records[0] or "status_code" in dataset.records[0]


class TestNLPGenerator:
    """NLP generator requires LLM, so we mock it."""
    
    def test_generate_with_mock(self, sample_nlp_spec, mock_chat_json):
        mock_chat_json.return_value = [
            {"review_id": "rev-1", "product_name": "Widget", "rating": 5,
             "review_text": "Great product!", "sentiment": "positive"},
            {"review_id": "rev-2", "product_name": "Gadget", "rating": 2,
             "review_text": "Not worth it.", "sentiment": "negative"},
        ]
        
        from generators import nlp
        sample_nlp_spec.row_count = 2
        dataset = nlp.generate(sample_nlp_spec)
        
        assert isinstance(dataset, GeneratedDataset)
        assert len(dataset.records) == 2
        assert dataset.records[0]["rating"] == 5

    def test_batch_generation(self, sample_nlp_spec):
        """Test that NLP generator handles batching."""
        with patch("generators.nlp.chat_json") as mock:
            mock.return_value = [
                {"review_id": f"rev-{i}", "product_name": "Product", "rating": 4,
                 "review_text": f"Review {i}", "sentiment": "positive"}
                for i in range(10)
            ]
            
            from generators import nlp
            sample_nlp_spec.row_count = 25
            dataset = nlp.generate(sample_nlp_spec)
            
            # Should have called LLM multiple times for batching
            assert mock.call_count >= 2
