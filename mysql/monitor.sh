#!/bin/bash
# Script de monitoreo de replicación

MYSQL_PASSWORD=${MYSQL_ROOT_PASSWORD:-rootpassword}

while true; do
    echo "=== Estado de Replicación === $(date)"
    
    # Verificar estado del master
    echo "MASTER STATUS:"
    docker exec mysql_mymind_master mysql -uroot -p$MYSQL_PASSWORD -e "SHOW MASTER STATUS\G" 2>/dev/null || echo "Master no disponible"
    
    # Verificar estado del slave
    echo -e "\nSLAVE STATUS:"
    docker exec mysql_mymind_slave mysql -uroot -p$MYSQL_PASSWORD -e "SHOW SLAVE STATUS\G" 2>/dev/null || echo "Slave no disponible"
    
    echo -e "\n----------------------------------------\n"
    sleep 60
done
