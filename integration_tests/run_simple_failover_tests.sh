#!/bin/bash
# run_simple_failover_tests.sh - Ejecuta las pruebas directamente con Python

# Activar entorno virtual
source /home/lflee/pytest-env/bin/activate

# Comprobar si los scripts existen
echo "Verificando archivos necesarios..."
FAILOVER_SCRIPT="/home/lflee/airflow/mysql/failover.sh"
SETUP_SCRIPT="/home/lflee/airflow/mysql/setup-replication.sh"
TEST_FILE="/home/lflee/airflow/integration_tests/test_failover_integration.py"

if [ ! -f "$FAILOVER_SCRIPT" ]; then
    echo "❌ ERROR: Script de failover no encontrado en: $FAILOVER_SCRIPT"
    exit 1
else
    echo "✅ Script de failover encontrado: $FAILOVER_SCRIPT"
    chmod +x "$FAILOVER_SCRIPT"
fi

if [ ! -f "$SETUP_SCRIPT" ]; then
    echo "❌ ERROR: Script de setup-replication no encontrado en: $SETUP_SCRIPT"
    exit 1
else
    echo "✅ Script de setup-replication encontrado: $SETUP_SCRIPT"
    chmod +x "$SETUP_SCRIPT"
fi

if [ ! -f "$TEST_FILE" ]; then
    echo "❌ ERROR: Archivo de prueba no encontrado en: $TEST_FILE"
    exit 1
else
    echo "✅ Archivo de prueba encontrado: $TEST_FILE"
fi

# Comprobar contenedores
echo "Verificando contenedores MySQL..."
docker ps | grep mysql_mymind

# Verificar replicación
echo "Verificando replicación..."
docker exec mysql_mymind_slave mysql -uroot -prootpassword -e "SHOW SLAVE STATUS\G" | grep -E "Slave_IO_Running:|Slave_SQL_Running:"

# Ejecutar pruebas
if [ "$1" = "--sequential" ]; then
    echo "Ejecutando pruebas de forma secuencial:"
    
    echo "IT-07-01: Replicación master-slave"
    python "$TEST_FILE" replication
    
    echo "IT-07-02: Simulación de fallo en master"
    python "$TEST_FILE" failover
    
    echo "IT-07-03: Continuidad de operaciones"
    python "$TEST_FILE" continuity
    
    echo "IT-08-01: ETL post-failover"
    python "$TEST_FILE" etl
    
    echo "IT-08-02: Actualización de conexión Airflow"
    python "$TEST_FILE" connection
else
    echo "Ejecutando todas las pruebas juntas:"
    python "$TEST_FILE" all
fi

echo "Restaurando replicación..."
bash "$SETUP_SCRIPT"

echo "Pruebas completadas"
