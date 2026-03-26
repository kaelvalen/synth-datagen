"""Integration tests for the full pipeline."""
from __future__ import annotations

import os
import pytest
from unittest.mock import patch, MagicMock

from core.types import DataType, ExportFormat, PipelineResult
from pipeline import run, _generate


class TestPipelineIntegration:
    """Integration tests that run the full pipeline with mocked LLM."""

    def test_full_pipeline_tabular(self, mock_intent_parser_response, temp_output_dir):
        def side_effect(system, user, **kwargs):
            if "veri mühendisi" in system.lower():
                return mock_intent_parser_response
            elif "kalite mühendisi" in system.lower():
                return {"score": 0.95, "issues": [], "suggestions": []}
            elif "iyileştirme" in system.lower():
                return []
            return {}
        
        with patch("intent.parser.chat_json", side_effect=side_effect), \
             patch("validators.checker.chat_json", side_effect=side_effect), \
             patch("refiners.refiner.chat_json", side_effect=side_effect):
            
            result = run(
                prompt="E-commerce order data",
                data_type=DataType.TABULAR,
                row_count=50,
                export_format=ExportFormat.CSV,
                output_dir=temp_output_dir,
                validate=True,
            )
            
            assert isinstance(result, PipelineResult)
            assert len(result.dataset.records) == 50
            assert result.export_path is not None
            assert os.path.exists(result.export_path)

    def test_pipeline_no_validate(self, mock_intent_parser_response, temp_output_dir):
        with patch("intent.parser.chat_json") as mock:
            mock.return_value = mock_intent_parser_response
            
            result = run(
                prompt="Quick test data",
                data_type=DataType.TABULAR,
                row_count=10,
                export_format=ExportFormat.JSONL,
                output_dir=temp_output_dir,
                validate=False,
            )
            
            assert result.validation.passed is True
            assert result.iterations == 0

    def test_pipeline_respects_max_refine(self, temp_output_dir):
        """Test that max_refine_iterations is respected."""
        intent_response = {
            "name": "test",
            "data_type": "tabular",
            "row_count": 10,
            "fields": [{"name": "id", "dtype": "str"}]
        }
        
        validation_response = {
            "score": 0.5,
            "issues": ["Always fail"],
            "suggestions": []
        }
        
        def side_effect(system, user, **kwargs):
            if "veri mühendisi" in system.lower():
                return intent_response
            elif "kalite mühendisi" in system.lower():
                return validation_response
            elif "iyileştirme" in system.lower():
                return [{"id": f"refined-{i}"} for i in range(10)]
            return {}
        
        with patch("intent.parser.chat_json", side_effect=side_effect), \
             patch("validators.checker.chat_json", side_effect=side_effect), \
             patch("refiners.refiner.chat_json", side_effect=side_effect):
            
            result = run(
                prompt="Test",
                data_type=DataType.TABULAR,
                row_count=10,
                export_format=ExportFormat.JSONL,
                output_dir=temp_output_dir,
                max_refine_iterations=2,
                validate=True,
            )
            
            # Should have done at most max_refine_iterations
            assert result.iterations <= 2


class TestGenerateDispatch:
    """Test the _generate dispatcher function."""

    def test_dispatch_tabular(self, sample_tabular_spec):
        dataset = _generate(sample_tabular_spec)
        assert dataset.metadata["generator"] == "tabular"

    def test_dispatch_timeseries(self, sample_timeseries_spec):
        dataset = _generate(sample_timeseries_spec)
        assert dataset.metadata["generator"] == "timeseries"

    def test_dispatch_log(self, sample_log_spec):
        dataset = _generate(sample_log_spec)
        assert dataset.metadata["generator"] == "log"

    def test_dispatch_nlp(self, sample_nlp_spec, mock_chat_json):
        mock_chat_json.return_value = [
            {"review_id": "1", "product_name": "Test", "rating": 5,
             "review_text": "Great!", "sentiment": "positive"}
        ]
        
        sample_nlp_spec.row_count = 1
        dataset = _generate(sample_nlp_spec)
        assert dataset.metadata["generator"] == "nlp"

    def test_dispatch_invalid_type(self, sample_tabular_spec):
        from core.types import DataType
        
        # Create a spec with invalid type (shouldn't happen normally)
        sample_tabular_spec.data_type = "invalid"
        
        with pytest.raises((ValueError, KeyError)):
            _generate(sample_tabular_spec)
