#!/bin/bash
# Script de failover automático

# Configuración
MASTER_HOST="mysql_mymind_master"
SLAVE_HOST="mysql_mymind_slave"
MYSQL_PASSWORD=${MYSQL_ROOT_PASSWORD:-rootpassword}

# Función para verificar si MySQL está disponible
check_mysql() {
    local host=$1
    docker exec $host mysqladmin ping -h localhost -u root -p$MYSQL_PASSWORD > /dev/null 2>&1
    return $?
}

# Función para actualizar la conexión de Airflow
update_airflow_connection() {
    echo "Actualizando conexión de Airflow..."
    
    # Detener el contenedor de Airflow (ajusta el nombre según tu configuración)
    docker stop airflow-airflow-scheduler-1
    docker stop airflow-airflow-worker-1
    
    # Actualizar la conexión en la base de datos de Airflow
    docker exec airflow-airflow-webserver-1 airflow connections delete mysql_mymind_dw
    docker exec airflow-airflow-webserver-1 airflow connections add mysql_mymind_dw \
        --conn-type mysql \
        --conn-login ${MYSQL_USER:-airflow_user} \
        --conn-password ${MYSQL_PASSWORD:-airflow_pass} \
        --conn-host mysql_mymind_slave \
        --conn-port 3306 \
        --conn-schema mymind_dw
    
    # Reiniciar los servicios de Airflow
    docker start airflow-airflow-scheduler-1
    docker start airflow-airflow-worker-1
    
    echo "Conexión de Airflow actualizada a apuntar al nuevo master (slave promovido)"
}

# Función para promover slave a master
promote_slave_to_master() {
    echo "Promoviendo slave a master..."
    
    # Detener replicación en el slave
    docker exec $SLAVE_HOST mysql -uroot -p$MYSQL_PASSWORD -e "STOP SLAVE;"
    
    # Remover configuración de slave
    docker exec $SLAVE_HOST mysql -uroot -p$MYSQL_PASSWORD -e "RESET SLAVE ALL;"
    
    # Configurar como master
    docker exec $SLAVE_HOST mysql -uroot -p$MYSQL_PASSWORD -e "SET GLOBAL read_only=OFF;"
    
    echo "Slave promovido a master exitosamente"
    
    # Actualizar configuración de Airflow para apuntar al nuevo master
    update_airflow_connection
}

# Función para actualizar la conexión de Airflow
update_airflow_connection() {
    echo "Actualizando conexión de Airflow..."
    # Aquí puedes actualizar la conexión de Airflow para que apunte al nuevo master
    # Esto dependerá de tu configuración específica
}

# Monitor principal
while true; do
    if ! check_mysql $MASTER_HOST; then
        echo "Master no responde, iniciando failover..."
        
        if check_mysql $SLAVE_HOST; then
            promote_slave_to_master
            echo "Failover completado"
            
            # Notificar al administrador
            echo "ALERTA: Se realizó failover de MySQL. El slave ahora es el master." | mail -s "Failover MySQL" admin@example.com
            
            break
        else
            echo "ERROR: Tanto master como slave están caídos"
            exit 1
        fi
    fi
    
    sleep 10
done
