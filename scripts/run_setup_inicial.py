"""
AeroTrack Analytics — Setup Inicial (ejecutar UNA vez desde el PC local)
=========================================================================
Qué hace:
  1. Crea la colección 'vuelos_raw' en PocketBase (si no existe).
  2. Carga el CSV airline_2m.csv en PocketBase (con auto-detección:
     si ya hay datos, no los vuelve a cargar).
  3. Imprime instrucciones para activar el DAG en Airflow.

IMPORTANTE: Este script se ejecuta SIEMPRE desde el PC anfitrión,
nunca desde dentro de un contenedor Docker.

Cómo ejecutar:
    pip install -r requirements.txt
    python scripts/run_setup_inicial.py
"""

import sys
import os

# Asegurar que el directorio scripts/ está en el path para importar los módulos
sys.path.insert(0, os.path.dirname(__file__))

# Importar las funciones principales de cada script de setup
import importlib.util


def _cargar_modulo(nombre_archivo: str):
    """Carga un script de scripts/ como módulo Python."""
    ruta = os.path.join(os.path.dirname(__file__), nombre_archivo)
    spec = importlib.util.spec_from_file_location(nombre_archivo.replace(".py", ""), ruta)
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


def main():
    print("=" * 62)
    print("  AeroTrack Analytics — Setup Inicial")
    print("  (Ejecutar una vez desde el PC antes de usar Airflow)")
    print("=" * 62)

    # ── PASO 1: Crear colección en PocketBase ─────────────────
    print("\n━━━ PASO 1/3: Crear colección en PocketBase ━━━")
    try:
        script_01 = _cargar_modulo("01_crear_coleccion_pb.py")
        script_01.main()
    except SystemExit as e:
        # sys.exit(0) en script 01 significa "ya existe, está bien"
        if e.code != 0:
            print(f"❌ Script 01 terminó con error (código {e.code}). Abortando.")
            sys.exit(e.code)
    except Exception as e:
        print(f"❌ Error en setup de colección: {e}")
        sys.exit(1)

    # ── PASO 2: Cargar CSV en PocketBase (con auto-detección) ─
    print("\n━━━ PASO 2/3: Cargar CSV en PocketBase ━━━")
    print("  (Se salta automáticamente si ya hay datos cargados)")
    try:
        script_02 = _cargar_modulo("02_cargar_csv_a_pb.py")
        script_02.main()
    except SystemExit as e:
        # sys.exit(0) en script 02 = "ya hay datos, se saltó la carga" → OK
        if e.code != 0:
            print(f"❌ Script 02 terminó con error (código {e.code}). Abortando.")
            sys.exit(e.code)
    except Exception as e:
        print(f"❌ Error en carga de CSV: {e}")
        sys.exit(1)

    # ── PASO 3: Configurar colecciones de administración ──────
    print("\n━━━ PASO 3/3: Configurando colecciones de administración... ━━━")
    try:
        script_admin = _cargar_modulo("setup_pocketbase_admin.py")
        script_admin.main()
    except SystemExit as e:
        if e.code != 0:
            print(f"❌ Script de admin terminó con error (código {e.code}). Abortando.")
            sys.exit(e.code)
    except Exception as e:
        print(f"❌ Error en setup de administración: {e}")
        sys.exit(1)

    # ── Instrucciones finales ─────────────────────────────────
    print("\n" + "=" * 62)
    print("  ✅ Setup completo.")
    print()
    print("  Próximos pasos:")
    print("  1. Abre Airflow:  http://localhost:8080")
    print(f"     Usuario: {os.getenv('AIRFLOW_ADMIN_USER', 'admin')}")
    print("     Contraseña: la definida en AIRFLOW_ADMIN_PASSWORD de .env")
    print()
    print("  2. Busca el DAG:  aerotrack_elt_pipeline")
    print()
    print("  3. Actívalo con el toggle y pulsa ▶ Trigger DAG")
    print("     para ejecutar extract → transform manualmente.")
    print()
    print("  4. Monitorea los resultados en MinIO:")
    print("     http://localhost:9001")
    print("=" * 62)


if __name__ == "__main__":
    main()
