#!/bin/bash
# Script para sincronizar completamente las bases de datos master y slave

MYSQL_ROOT_PASSWORD=${MYSQL_ROOT_PASSWORD:-rootpassword}

echo "Iniciando sincronización completa de Master a Slave..."

# 1. Detener replicación si está activa
echo "Deteniendo replicación en el Slave..."
docker exec mysql_mymind_slave mysql -uroot -p$MYSQL_ROOT_PASSWORD -e "STOP SLAVE;"

# 2. Bloquear tablas en el Master para evitar cambios durante el volcado
echo "Bloqueando tablas en el Master para consistencia..."
docker exec mysql_mymind_master mysql -uroot -p$MYSQL_ROOT_PASSWORD mymind_dw -e "FLUSH TABLES WITH READ LOCK;"

# 3. Obtener posición actual del binlog
echo "Obteniendo posición actual del binlog..."
MASTER_STATUS=$(docker exec mysql_mymind_master mysql -uroot -p$MYSQL_ROOT_PASSWORD -e "SHOW MASTER STATUS\G")
MASTER_LOG_FILE=$(echo "$MASTER_STATUS" | grep File | awk '{print $2}')
MASTER_LOG_POS=$(echo "$MASTER_STATUS" | grep Position | awk '{print $2}')

echo "Master log file: $MASTER_LOG_FILE"
echo "Master log position: $MASTER_LOG_POS"

# 4. Exportar datos del Master
echo "Exportando datos del Master..."
docker exec mysql_mymind_master mysqldump -uroot -p$MYSQL_ROOT_PASSWORD --databases mymind_dw --master-data=2 > /tmp/mymind_dump.sql

# 5. Desbloquear tablas en el Master
echo "Desbloqueando tablas en el Master..."
docker exec mysql_mymind_master mysql -uroot -p$MYSQL_ROOT_PASSWORD -e "UNLOCK TABLES;"

# 6. Importar datos al Slave
echo "Importando datos al Slave..."
cat /tmp/mymind_dump.sql | docker exec -i mysql_mymind_slave mysql -uroot -p$MYSQL_ROOT_PASSWORD

# 7. Configurar replicación en el Slave
echo "Configurando replicación en el Slave..."
docker exec mysql_mymind_slave mysql -uroot -p$MYSQL_ROOT_PASSWORD -e "
STOP SLAVE;
RESET SLAVE;
CHANGE MASTER TO
  MASTER_HOST='mysql_mymind',
  MASTER_USER='replication_user',
  MASTER_PASSWORD='replication_password',
  MASTER_LOG_FILE='${MASTER_LOG_FILE}',
  MASTER_LOG_POS=${MASTER_LOG_POS};
START SLAVE;
"

# 8. Verificar el estado de la replicación
echo "Verificando estado de la replicación..."
docker exec mysql_mymind_slave mysql -uroot -p$MYSQL_ROOT_PASSWORD -e "SHOW SLAVE STATUS\G" | grep -E "Slave_IO_Running|Slave_SQL_Running|Last_Error|Seconds_Behind_Master"

echo "Sincronización completa finalizada."
