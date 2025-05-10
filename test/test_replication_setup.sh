#!/bin/bash
# tests/test_replication_setup.sh

# Variables
MYSQL_ROOT_PASSWORD=rootpassword

# 1. Probar configuración de la replicación
echo "Test: Configuración de replicación"

# Reiniciar los servicios para un entorno limpio
docker-compose down
docker-compose up -d mysql_mymind mysql_mymind_slave

# Esperar a que los servicios estén disponibles
sleep 20

# Ejecutar script de replicación
./mysql/setup-replication.sh

# Verificar estado de replicación
SLAVE_STATUS=$(docker exec mysql_mymind_slave mysql -uroot -p$MYSQL_ROOT_PASSWORD -e "SHOW SLAVE STATUS\G")
SLAVE_IO_RUNNING=$(echo "$SLAVE_STATUS" | grep Slave_IO_Running | awk '{print $2}')
SLAVE_SQL_RUNNING=$(echo "$SLAVE_STATUS" | grep Slave_SQL_Running | awk '{print $2}')

if [ "$SLAVE_IO_RUNNING" == "Yes" ] && [ "$SLAVE_SQL_RUNNING" == "Yes" ]; then
    echo "✅ Test exitoso: Replicación configurada correctamente"
else
    echo "❌ Test fallido: Replicación no configurada correctamente"
    echo "$SLAVE_STATUS"
    exit 1
fi

# 2. Probar inserción de datos con replicación
echo "Test: Inserción de datos con replicación"

# Insertar datos en el master
docker exec mysql_mymind mysql -uroot -p$MYSQL_ROOT_PASSWORD mymind_dw -e "
INSERT INTO users (user_id, name, email) 
VALUES ('test-user-1', 'Test User 1', 'test1@example.com');
"

# Esperar replicación
sleep 5

# Verificar datos en el slave
SLAVE_DATA=$(docker exec mysql_mymind_slave mysql -uroot -p$MYSQL_ROOT_PASSWORD mymind_dw -e "SELECT * FROM users WHERE user_id='test-user-1'")

if [[ $SLAVE_DATA == *"test-user-1"* ]]; then
    echo "✅ Test exitoso: Datos replicados correctamente"
else
    echo "❌ Test fallido: Datos no replicados al slave"
    exit 1
fi

# 3. Probar detección de fallo del master
echo "Test: Detección de fallo del master"

# Simular caída del master
docker stop mysql_mymind

# Verificar que el script de failover detecta la caída
./mysql/failover.sh &
FAILOVER_PID=$!

# Dar tiempo para la detección y ejecución del failover
sleep 10

# Verificar que el slave ha sido promovido a master
SLAVE_STATUS=$(docker exec mysql_mymind_slave mysql -uroot -p$MYSQL_ROOT_PASSWORD -e "SHOW SLAVE STATUS\G")
READ_ONLY=$(docker exec mysql_mymind_slave mysql -uroot -p$MYSQL_ROOT_PASSWORD -e "SELECT @@read_only" | grep -v "read_only" | tr -d " ")

# Matar proceso de failover
kill $FAILOVER_PID

if [[ "$READ_ONLY" == "0" ]]; then
    echo "✅ Test exitoso: Slave promovido a master (read_only desactivado)"
else
    echo "❌ Test fallido: Slave no promovido correctamente a master"
    exit 1
fi

# 4. Probar inserción después del failover
echo "Test: Inserción después del failover"

# Insertar datos en el nuevo master (antiguo slave)
docker exec mysql_mymind_slave mysql -uroot -p$MYSQL_ROOT_PASSWORD mymind_dw -e "
INSERT INTO users (user_id, name, email) 
VALUES ('test-user-2', 'Test User 2', 'test2@example.com');
"

# Verificar inserción
INSERTED_DATA=$(docker exec mysql_mymind_slave mysql -uroot -p$MYSQL_ROOT_PASSWORD mymind_dw -e "SELECT * FROM users WHERE user_id='test-user-2'")

if [[ $INSERTED_DATA == *"test-user-2"* ]]; then
    echo "✅ Test exitoso: Datos insertados correctamente en nuevo master"
else
    echo "❌ Test fallido: No se pueden insertar datos en nuevo master"
    exit 1
fi

# Limpiar entorno
docker-compose down

echo "Tests completados"
