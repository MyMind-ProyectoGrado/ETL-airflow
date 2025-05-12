#!/bin/bash
# Script simplificado para ejecutar pruebas de failover y alta disponibilidad

# Activar entorno virtual
source /home/lflee/pytest-env/bin/activate

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
    python -m pytest integration_tests/test_failover_integration.py::test_it_07_01_replication -v
    
    echo "IT-07-02: Simulación de fallo en master"
    python -m pytest integration_tests/test_failover_integration.py::test_it_07_02_failover -v
    
    echo "IT-07-03: Continuidad de operaciones"
    python -m pytest integration_tests/test_failover_integration.py::test_it_07_03_continuity -v
    
    echo "IT-08-01: ETL post-failover"
    python -m pytest integration_tests/test_failover_integration.py::test_it_08_01_etl_post_failover -v
    
    echo "IT-08-02: Actualización de conexión Airflow"
    python -m pytest integration_tests/test_failover_integration.py::test_it_08_02_airflow_connection -v
else
    echo "Ejecutando todas las pruebas juntas:"
    python -m pytest integration_tests/test_failover_integration.py -v
fi

# Restaurar replicación
echo "Restaurando replicación..."
bash mysql/setup-replication.sh

echo "Pruebas completadas"
