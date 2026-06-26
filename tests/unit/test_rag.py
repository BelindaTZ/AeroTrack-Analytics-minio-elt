"""Tests unitarios para RAG intent parsing y question type detection."""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from app.asistente_ia.rag import parse_intent, _detect_question_type
from app.shared.metrics import safe_float


class TestSafe:
    def test_float_conversion(self):
        assert safe_float(42.5) == 42.5

    def test_nan_returns_zero(self):
        import math
        assert safe_float(float("nan")) == 0.0

    def test_inf_returns_zero(self):
        assert safe_float(float("inf")) == 0.0
        assert safe_float(float("-inf")) == 0.0

    def test_string_conversion(self):
        assert safe_float("12.5") == 12.5

    def test_invalid_string(self):
        assert safe_float("abc") == 0.0

    def test_none_returns_zero(self):
        assert safe_float(None) == 0.0

    def test_integer(self):
        assert safe_float(100) == 100


class TestDetectQuestionType:
    def test_delay_cause_detection(self):
        assert "delay_cause" in _detect_question_type("¿Cuál es la causa del retraso?")

    def test_cancelacion_detection(self):
        assert "cancelacion" in _detect_question_type("¿Por qué se cancelan vuelos?")

    def test_dia_semana_detection(self):
        assert "dia_semana" in _detect_question_type("OTP los lunes")

    def test_ruta_detection(self):
        assert "ruta" in _detect_question_type("Analiza la ruta JFK-LAX")

    def test_eficiencia_detection(self):
        assert "eficiencia" in _detect_question_type("¿Cuál es la ruta más eficiente?")

    def test_desvio_detection(self):
        assert "desvio" in _detect_question_type("Desvíos en rutas")

    def test_tendencia_detection(self):
        assert "tendencia" in _detect_question_type("Tendencia mensual del OTP")

    def test_ranking_otp_detection(self):
        assert "ranking_otp" in _detect_question_type("¿Cuál es la aerolínea más puntual?")

    def test_multiple_types(self):
        result = _detect_question_type("Causas de cancelación y retraso")
        assert "cancelacion" in result
        assert "delay_cause" in result

    def test_no_type_for_generic(self):
        result = _detect_question_type("Hola, ¿cómo estás?")
        assert len(result) == 0


class TestParseIntent:
    def test_year_extraction(self):
        filtros = parse_intent("OTP en 2024")
        assert filtros.get("year") == "2024"

    def test_month_extraction_es(self):
        filtros = parse_intent("Datos de marzo")
        assert filtros.get("month") == "3"

    def test_month_extraction_en(self):
        filtros = parse_intent("Data from jan")
        assert filtros.get("month") == "1"

    def test_route_extraction(self):
        filtros = parse_intent("Ruta JFK-LAX")
        assert filtros.get("ruta") == "JFK-LAX"
        assert filtros.get("origen") == "JFK"
        assert filtros.get("destino") == "LAX"

    def test_route_de_a_extraction(self):
        filtros = parse_intent("Vuelos de JFK a LAX")
        assert filtros.get("ruta") == "JFK-LAX"

    def test_dow_extraction(self):
        filtros = parse_intent("OTP los lunes")
        assert filtros.get("dow") == "1"

    def test_dow_extraction_domingo(self):
        filtros = parse_intent("Datos del domingo")
        assert filtros.get("dow") == "7"

    def test_combined_filters(self):
        filtros = parse_intent("Cancelaciones de LATAM en marzo 2024")
        assert filtros.get("year") == "2024"
        assert filtros.get("month") == "3"

    def test_no_filters(self):
        filtros = parse_intent("Hola")
        assert len(filtros) == 0
