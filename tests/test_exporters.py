"""Tests for exporter module."""
from __future__ import annotations

import csv
import json
import os
import pytest

from core.types import ExportFormat
from exporters.writer import export


class TestCSVExport:
    def test_export_csv(self, sample_dataset, temp_output_dir):
        path = export(sample_dataset, ExportFormat.CSV, output_dir=temp_output_dir)
        
        assert path.endswith(".csv")
        assert os.path.exists(path)
        
        with open(path, "r") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        
        assert len(rows) == len(sample_dataset.records)
        assert "order_id" in rows[0]

    def test_csv_has_header(self, sample_dataset, temp_output_dir):
        path = export(sample_dataset, ExportFormat.CSV, output_dir=temp_output_dir)
        
        with open(path, "r") as f:
            first_line = f.readline()
        
        assert "order_id" in first_line
        assert "customer_name" in first_line


class TestJSONLExport:
    def test_export_jsonl(self, sample_dataset, temp_output_dir):
        path = export(sample_dataset, ExportFormat.JSONL, output_dir=temp_output_dir)
        
        assert path.endswith(".jsonl")
        assert os.path.exists(path)
        
        with open(path, "r") as f:
            lines = f.readlines()
        
        assert len(lines) == len(sample_dataset.records)
        
        # Each line should be valid JSON
        for line in lines:
            obj = json.loads(line)
            assert "order_id" in obj

    def test_jsonl_unicode_support(self, sample_tabular_spec, temp_output_dir):
        from core.types import GeneratedDataset
        
        dataset = GeneratedDataset(
            spec=sample_tabular_spec,
            records=[
                {"order_id": "1", "customer_name": "Müşteri Türkçe", 
                 "email": "test@test.com", "amount": 100.0, "quantity": 1,
                 "status": "pending", "created_at": "2024-01-01T00:00:00"},
            ]
        )
        
        path = export(dataset, ExportFormat.JSONL, output_dir=temp_output_dir)
        
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
        
        assert "Müşteri Türkçe" in content


class TestParquetExport:
    def test_export_parquet(self, sample_dataset, temp_output_dir):
        path = export(sample_dataset, ExportFormat.PARQUET, output_dir=temp_output_dir)
        
        # Should either be .parquet or fallback to .jsonl
        assert os.path.exists(path)
        
        if path.endswith(".parquet"):
            import pandas as pd
            df = pd.read_parquet(path)
            assert len(df) == len(sample_dataset.records)


class TestTXTExport:
    def test_export_txt(self, sample_nlp_spec, temp_output_dir, mock_chat_json):
        from core.types import GeneratedDataset
        
        dataset = GeneratedDataset(
            spec=sample_nlp_spec,
            records=[
                {"review_id": "1", "review_text": "This is a long review text that should appear in the output file as plain text content."},
                {"review_id": "2", "review_text": "Another detailed review with enough characters to be included in txt output."},
            ]
        )
        
        path = export(dataset, ExportFormat.TXT, output_dir=temp_output_dir)
        
        assert path.endswith(".txt")
        assert os.path.exists(path)
        
        with open(path, "r") as f:
            content = f.read()
        
        assert "review" in content.lower() or "---" in content


class TestExportGeneral:
    def test_creates_output_directory(self, sample_dataset, tmp_path):
        output_dir = str(tmp_path / "nested" / "output")
        assert not os.path.exists(output_dir)
        
        path = export(sample_dataset, ExportFormat.CSV, output_dir=output_dir)
        
        assert os.path.exists(output_dir)
        assert os.path.exists(path)

    def test_custom_filename(self, sample_dataset, temp_output_dir):
        path = export(
            sample_dataset, 
            ExportFormat.CSV, 
            output_dir=temp_output_dir,
            filename="custom_name"
        )
        
        assert "custom_name.csv" in path

    def test_empty_records_export(self, sample_tabular_spec, temp_output_dir):
        from core.types import GeneratedDataset
        
        empty_dataset = GeneratedDataset(
            spec=sample_tabular_spec,
            records=[]
        )
        
        # CSV with empty records should still work
        path = export(empty_dataset, ExportFormat.JSONL, output_dir=temp_output_dir)
        assert os.path.exists(path)
        
        with open(path, "r") as f:
            content = f.read()
        assert content == ""  # Empty file
