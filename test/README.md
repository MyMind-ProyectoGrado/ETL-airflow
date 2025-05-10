# Pruebas del Sistema ETL y Alta Disponibilidad

Este directorio contiene las pruebas para verificar el correcto funcionamiento del sistema ETL MongoDB-MySQL y el sistema de alta disponibilidad implementado.

## Pruebas Unitarias del ETL

Las pruebas unitarias del DAG ETL verifican el correcto funcionamiento de las funciones de extracción, transformación y carga de datos.

### Requisitos

- Python 3.x
- pytest
- Dependencias de Airflow instaladas

### Ejecución

```bash
# Desde el directorio de pruebas
pytest test_etl_functions.py -v
