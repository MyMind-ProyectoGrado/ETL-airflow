#!/bin/bash

# Activar entorno virtual
source /home/lflee/pytest-env/bin/activate

# Cambiar al directorio de pruebas
cd /home/lflee/airflow/integration_tests

# Ejecutar pruebas
echo "Ejecutando pruebas de proceso ETL (IT-05)..."
pytest -v test_etl.py

# Mostrar resumen
echo "Pruebas completadas."
