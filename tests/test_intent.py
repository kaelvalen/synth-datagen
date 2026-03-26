"""Tests for intent parser module."""
from __future__ import annotations

import pytest
from unittest.mock import patch

from core.types import DataSpec, DataType, FieldSpec
from intent.parser import parse_intent, _raw_to_spec


class TestRawToSpec:
    def test_minimal_raw(self):
        raw = {
            "name": "test",
            "data_type": "tabular",
            "fields": []
        }
        spec = _raw_to_spec(raw)
        
        assert spec.name == "test"
        assert spec.data_type == DataType.TABULAR
        assert spec.row_count == 100  # Default
        assert spec.locale == "en_US"  # Default
        assert spec.fields == []

    def test_full_raw(self, mock_intent_parser_response):
        spec = _raw_to_spec(mock_intent_parser_response)
        
        assert spec.name == "test_dataset"
        assert spec.data_type == DataType.TABULAR
        assert spec.row_count == 50
        assert len(spec.fields) == 2
        
        id_field = spec.fields[0]
        assert id_field.name == "id"
        assert id_field.unique is True

    def test_field_defaults(self):
        raw = {
            "name": "test",
            "data_type": "tabular",
            "fields": [
                {"name": "simple", "dtype": "str"}
            ]
        }
        spec = _raw_to_spec(raw)
        field = spec.fields[0]
        
        assert field.nullable is False
        assert field.unique is False
        assert field.categories == []


class TestParseIntent:
    def test_parse_basic_prompt(self, mock_intent_parser_response):
        with patch("intent.parser.chat_json") as mock:
            mock.return_value = mock_intent_parser_response
            
            spec = parse_intent("Generate test data")
            
            assert isinstance(spec, DataSpec)
            mock.assert_called_once()

    def test_parse_with_data_type_override(self, mock_intent_parser_response):
        with patch("intent.parser.chat_json") as mock:
            mock.return_value = mock_intent_parser_response
            
            spec = parse_intent("Generate data", data_type=DataType.TABULAR)
            
            # Check that override hint was added to prompt
            call_args = mock.call_args
            user_msg = call_args.kwargs.get("user") or call_args[1].get("user")
            assert "MUTLAKA" in user_msg
            assert "tabular" in user_msg

    def test_parse_with_row_count_override(self, mock_intent_parser_response):
        with patch("intent.parser.chat_json") as mock:
            mock.return_value = mock_intent_parser_response
            
            spec = parse_intent("Generate data", row_count=500)
            
            call_args = mock.call_args
            user_msg = call_args.kwargs.get("user") or call_args[1].get("user")
            assert "500" in user_msg

    def test_parse_handles_nlp_type(self):
        with patch("intent.parser.chat_json") as mock:
            mock.return_value = {
                "name": "reviews",
                "data_type": "nlp",
                "row_count": 20,
                "locale": "tr_TR",
                "context": "Product reviews",
                "constraints": [],
                "fields": [
                    {"name": "text", "dtype": "str", "description": "Review text"}
                ]
            }
            
            spec = parse_intent("Product reviews in Turkish", data_type=DataType.NLP)
            
            assert spec.data_type == DataType.NLP

    def test_parse_handles_timeseries_type(self):
        with patch("intent.parser.chat_json") as mock:
            mock.return_value = {
                "name": "metrics",
                "data_type": "timeseries",
                "row_count": 1000,
                "locale": "en_US",
                "context": "Server metrics",
                "constraints": [],
                "fields": [
                    {"name": "timestamp", "dtype": "datetime"},
                    {"name": "cpu", "dtype": "float", "min_val": 0, "max_val": 100}
                ]
            }
            
            spec = parse_intent("Server CPU metrics", data_type=DataType.TIMESERIES)
            
            assert spec.data_type == DataType.TIMESERIES
            assert any(f.dtype == "datetime" for f in spec.fields)

    def test_parse_handles_constraints(self):
        with patch("intent.parser.chat_json") as mock:
            mock.return_value = {
                "name": "orders",
                "data_type": "tabular",
                "row_count": 100,
                "constraints": ["end_time > start_time", "quantity > 0"],
                "fields": [
                    {"name": "start_time", "dtype": "datetime"},
                    {"name": "end_time", "dtype": "datetime"},
                    {"name": "quantity", "dtype": "int"}
                ]
            }
            
            spec = parse_intent("Order data with time constraints")
            
            assert len(spec.constraints) == 2
            assert "end_time > start_time" in spec.constraints
