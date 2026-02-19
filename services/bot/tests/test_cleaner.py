"""
Tests de limpieza de texto — app/cleaner.py
"""
from app.cleaner import clean_text


def test_elimina_espacios_extra():
    # El cleaner colapsa cualquier secuencia de whitespace a un solo espacio
    assert clean_text("  hola   mundo  ") == "hola mundo"


def test_elimina_saltos_de_linea_multiples():
    # \s+ colapsa todo whitespace en un espacio
    assert clean_text("hola\n\n\nmundo") == "hola mundo"


def test_string_vacio():
    assert clean_text("") == ""


def test_solo_espacios():
    assert clean_text("     ") == ""


def test_texto_normal_sin_cambios():
    texto = "Hola, ¿cómo estás?"
    assert clean_text(texto) == texto


def test_elimina_caracteres_nulos():
    # \x00 es control char — se elimina (no se reemplaza con espacio)
    assert clean_text("hola\x00mundo") == "holamundo"
