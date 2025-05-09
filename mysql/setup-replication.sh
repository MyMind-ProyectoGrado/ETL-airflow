#!/bin/bash
# Script para configurar la replicación MySQL

echo "Esperando a que MySQL Master y Slave estén listos..."
sleep 10

# Variables
MYSQL_ROOT_PASSWORD=${MYSQL_ROOT_PASSWORD:-rootpassword}

# Verificar si ya hay una replicación activa
SLAVE_STATUS=$(docker exec mysql_mymind_slave mysql -uroot -p${MYSQL_ROOT_PASSWORD} -e "SHOW SLAVE STATUS\G")
SLAVE_IO_RUNNING=$(echo "$SLAVE_STATUS" | grep Slave_IO_Running | awk '{print $2}')
SLAVE_SQL_RUNNING=$(echo "$SLAVE_STATUS" | grep Slave_SQL_Running | awk '{print $2}')

if [ "$SLAVE_IO_RUNNING" == "Yes" ] && [ "$SLAVE_SQL_RUNNING" == "Yes" ]; then
    echo "La replicación ya está configurada y funcionando. Saliendo."
    exit 0
fi


# Paso 1: Crear las tablas en el slave si no existen
echo "Asegurando que las tablas existan en el slave..."
docker exec mysql_mymind_slave mysql -uroot -p${MYSQL_ROOT_PASSWORD} mymind_dw -e "
CREATE TABLE IF NOT EXISTS users (
    user_id VARCHAR(255) PRIMARY KEY,
    name VARCHAR(255),
    email VARCHAR(255),
    profile_pic TEXT,
    birthdate DATE,
    city VARCHAR(255),
    personality VARCHAR(255),
    university VARCHAR(255),
    degree VARCHAR(255),
    gender VARCHAR(50),
    notifications BOOLEAN,
    accept_policies BOOLEAN,
    acceptance_date DATETIME,
    acceptance_ip VARCHAR(45),
    allow_anonimized_usage BOOLEAN
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS transcriptions (
    transcription_id VARCHAR(255) PRIMARY KEY,
    user_id VARCHAR(255),
    transcription_date DATE,
    transcription_time TIME,
    text TEXT,
    emotion VARCHAR(50),
    sentiment VARCHAR(50),
    topic VARCHAR(255),
    emotion_probs_joy FLOAT,
    emotion_probs_anger FLOAT,
    emotion_probs_sadness FLOAT,
    emotion_probs_disgust FLOAT,
    emotion_probs_fear FLOAT,
    emotion_probs_neutral FLOAT,
    emotion_probs_surprise FLOAT,
    emotion_probs_trust FLOAT,
    emotion_probs_anticipation FLOAT,
    sentiment_probs_positive FLOAT,
    sentiment_probs_negative FLOAT,
    sentiment_probs_neutral FLOAT,
    FOREIGN KEY (user_id) REFERENCES users(user_id)
) ENGINE=InnoDB;
"

# Paso 2: Obtener información del master
echo "Obteniendo información del master..."
MASTER_STATUS=$(docker exec mysql_mymind_master mysql -uroot -p${MYSQL_ROOT_PASSWORD} -e "SHOW MASTER STATUS\G")
MASTER_LOG_FILE=$(echo "$MASTER_STATUS" | grep File | awk '{print $2}')
MASTER_LOG_POS=$(echo "$MASTER_STATUS" | grep Position | awk '{print $2}')

echo "Master log file: $MASTER_LOG_FILE"
echo "Master log position: $MASTER_LOG_POS"

# Paso 3: Configurar el slave
echo "Configurando el slave..."
docker exec mysql_mymind_slave mysql -uroot -p${MYSQL_ROOT_PASSWORD} -e "
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

echo "Replicación configurada. Verificando estado..."
sleep 5

# Paso 4: Verificar el estado de la replicación
echo "Estado de la replicación:"
docker exec mysql_mymind_slave mysql -uroot -p${MYSQL_ROOT_PASSWORD} -e "SHOW SLAVE STATUS\G" | grep -E "Slave_IO_Running|Slave_SQL_Running|Last_Error|Seconds_Behind_Master"

# Paso 5: Verificar que las tablas existen en ambos servidores
echo -e "\nTablas en el master:"
docker exec mysql_mymind_master mysql -uroot -p${MYSQL_ROOT_PASSWORD} mymind_dw -e "SHOW TABLES;"

echo -e "\nTablas en el slave:"
docker exec mysql_mymind_slave mysql -uroot -p${MYSQL_ROOT_PASSWORD} mymind_dw -e "SHOW TABLES;"
