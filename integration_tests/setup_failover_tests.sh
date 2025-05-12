#!/bin/bash
# setup_failover_tests.sh - Configura los permisos necesarios para las pruebas de failover

set -e  # Salir inmediatamente si un comando falla

# Hacer ejecutables los scripts
echo "🔧 Configurando permisos de scripts..."
chmod +x run_failover_integration_test.sh
chmod +x ../mysql/failover.sh
chmod +x ../mysql/setup-replication.sh
chmod +x ../mysql/monitor.sh
chmod +x ../mysql/sync-databases.sh

echo "✅ Permisos configurados correctamente"

# Verificar conexión a MySQL Master y Slave desde los contenedores
echo "🔍 Verificando conexión a MySQL Master desde el contenedor..."
docker exec mysql_mymind_master mysql -uairflow_user -pairflow_pass -e "SELECT 'Conexión a MySQL Master exitosa' as Status;" mymind_dw || echo "❌ No se pudo conectar a MySQL Master"

echo "🔍 Verificando conexión a MySQL Slave desde el contenedor..."
docker exec mysql_mymind_slave mysql -uairflow_user -pairflow_pass -e "SELECT 'Conexión a MySQL Slave exitosa' as Status;" mymind_dw || echo "❌ No se pudo conectar a MySQL Slave"

# Verificar estado de replicación actual
echo "🔍 Verificando estado de replicación actual..."
docker exec mysql_mymind_slave mysql -uroot -prootpassword -e "SHOW SLAVE STATUS\G" | grep -E "Slave_IO_Running:|Slave_SQL_Running:|Seconds_Behind_Master:|Last_Error:"

echo "✅ Todo listo para ejecutar las pruebas de failover"
echo "   Ejecuta: bash integration_tests/run_failover_integration_test.sh"
echo "   Para ejecución secuencial: bash integration_tests/run_failover_integration_test.sh --sequential"
