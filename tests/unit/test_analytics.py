"""Tests unitarios para analytics helpers."""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

import pandas as pd
from app.shared.analytics import _desnormalizar


class TestDesnormalizar:
    def test_converts_categorical_to_base_dtype(self):
        df = pd.DataFrame({
            "cat_col": pd.Categorical(["a", "b", "c"]),
            "num_col": pd.Categorical([1, 2, 3]),
        })
        result = _desnormalizar(df)
        assert not hasattr(result["cat_col"], "cat")
        assert not hasattr(result["num_col"], "cat")

    def test_preserves_non_categorical(self):
        df = pd.DataFrame({
            "str_col": ["a", "b"],
            "int_col": [1, 2],
            "float_col": [1.0, 2.0],
        })
        result = _desnormalizar(df)
        assert not hasattr(result["str_col"], "cat")
        assert not hasattr(result["int_col"], "cat")
        assert not hasattr(result["float_col"], "cat")

    def test_empty_dataframe(self):
        df = pd.DataFrame()
        result = _desnormalizar(df)
        assert result.empty

    def test_multiple_categorical_columns(self):
        df = pd.DataFrame({
            "a": pd.Categorical(["x", "y"]),
            "b": pd.Categorical([10, 20]),
            "c": pd.Categorical([1.5, 2.5]),
        })
        result = _desnormalizar(df)
        for col in df.columns:
            assert not hasattr(result[col], "cat")
