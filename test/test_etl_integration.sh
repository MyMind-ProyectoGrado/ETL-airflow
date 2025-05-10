#!/bin/bash
# tests/test_etl_integration.sh

# Variables
MYSQL_ROOT_PASSWORD=rootpassword

# 1. Preparar entorno
echo "Preparando entorno de pruebas..."
docker-compose down
docker volume prune -f
docker-compose up -d

# Esperar a que los servicios estén disponibles
sleep 30

# 2. Configurar replicación MySQL
echo "Configurando replicación MySQL..."
./mysql/setup-replication.sh

# 3. Preparar datos de prueba en MongoDB
echo "Preparando datos de prueba en MongoDB..."
# Usamos mongo-express o un script Python para cargar datos de prueba
python3 - <<EOF
from pymongo import MongoClient
from bson import ObjectId
from datetime import datetime

# Conectar a MongoDB
client = MongoClient("mongodb://airflow_user:airflow_pass@localhost:27017/myMindDB-Users")
db = client["myMindDB-Users"]
collection = db["users"]

# Limpiar colección
collection.delete_many({})

# Insertar datos de prueba
users = [
    {
        "_id": ObjectId(),
        "name": "Test User 1",
        "email": "user1@example.com",
        "profilePic": "profile1.jpg",
        "birthdate": datetime(1990, 1, 15).isoformat(),
        "city": "Test City 1",
        "personality": "INTJ",
        "university": "Test University",
        "degree": "Computer Science",
        "gender": "Male",
        "notifications": True,
        "data_treatment": {
            "accept_policies": True,
            "acceptance_date": datetime(2025, 3, 10, 14, 30).isoformat(),
            "acceptance_ip": "192.168.1.100",
            "privacy_preferences": {
                "allow_anonimized_usage": True
            }
        },
        "transcriptions": [
            {
                "_id": ObjectId(),
                "date": datetime(2025, 4, 5, 10, 15).isoformat(),
                "time": "10:15:00",
                "text": "Hoy me siento muy contento con los avances del proyecto.",
                "emotion": "joy",
                "sentiment": "positive",
                "topic": "trabajo",
                "emotionProbabilities": {
                    "joy": 0.85,
                    "anger": 0.02,
                    "sadness": 0.01,
                    "disgust": 0.01,
                    "fear": 0.01,
                    "neutral": 0.05,
                    "surprise": 0.02,
                    "trust": 0.02,
                    "anticipation": 0.01
                },
                "sentimentProbabilities": {
                    "positive": 0.90,
                    "negative": 0.05,
                    "neutral": 0.05
                }
            }
        ]
    },
    {
        "_id": ObjectId(),
        "name": "Test User 2",
        "email": "user2@example.com",
        "profilePic": "profile2.jpg",
        "birthdate": datetime(1985, 5, 20).isoformat(),
        "city": "Test City 2",
        "personality": "ENFP",
        "university": "Another University",
        "degree": "Psychology",
        "gender": "Female",
        "notifications": False,
        "data_treatment": {
            "accept_policies": True,
            "acceptance_date": datetime(2025, 2, 15, 9, 45).isoformat(),
            "acceptance_ip": "192.168.1.101",
            "privacy_preferences": {
                "allow_anonimized_usage": False
            }
        },
        "transcriptions": [
            {
                "_id": ObjectId(),
                "date": datetime(2025, 4, 6, 18, 30).isoformat(),
                "time": "18:30:00",
                "text": "Estoy preocupada por la reunión de mañana.",
                "emotion": "fear",
                "sentiment": "negative",
                "topic": "trabajo",
                "emotionProbabilities": {
                    "joy": 0.05,
                    "anger": 0.05,
                    "sadness": 0.10,
                    "disgust": 0.00,
                    "fear": 0.70,
                    "neutral": 0.05,
                    "surprise": 0.02,
                    "trust": 0.01,
                    "anticipation": 0.02
                },
                "sentimentProbabilities": {
                    "positive": 0.10,
                    "negative": 0.80,
                    "neutral": 0.10
                }
            }
        ]
    }
]

# Insertar usuarios
collection.insert_many(users)
print(f"Insertados {len(users)} usuarios con transcripciones en MongoDB")
EOF

# 4. Ejecutar DAG de ETL
echo "Ejecutando DAG de ETL..."
docker exec airflow-airflow-webserver-1 airflow dags trigger mymind_mongo_to_mysql_etl

# Esperar a que el DAG complete su ejecución
echo "Esperando a que el DAG complete la ejecución..."
sleep 30

# 5. Verificar datos en MySQL Master
echo "Verificando datos en MySQL Master..."
USERS_COUNT=$(docker exec mysql_mymind mysql -uroot -p$MYSQL_ROOT_PASSWORD mymind_dw -e "SELECT COUNT(*) FROM users")
TRANSCRIPTIONS_COUNT=$(docker exec mysql_mymind mysql -uroot -p$MYSQL_ROOT_PASSWORD mymind_dw -e "SELECT COUNT(*) FROM transcriptions")

if [[ $USERS_COUNT == *"2"* ]] && [[ $TRANSCRIPTIONS_COUNT == *"2"* ]]; then
    echo "✅ Test exitoso: Datos cargados correctamente en MySQL Master"
else
    echo "❌ Test fallido: Datos no cargados correctamente en MySQL Master"
    echo "Usuarios: $USERS_COUNT"
    echo "Transcripciones: $TRANSCRIPTIONS_COUNT"
    exit 1
fi

# 6. Verificar replicación a MySQL Slave
echo "Verificando replicación a MySQL Slave..."
USERS_COUNT_SLAVE=$(docker exec mysql_mymind_slave mysql -uroot -p$MYSQL_ROOT_PASSWORD mymind_dw -e "SELECT COUNT(*) FROM users")
TRANSCRIPTIONS_COUNT_SLAVE=$(docker exec mysql_mymind_slave mysql -uroot -p$MYSQL_ROOT_PASSWORD mymind_dw -e "SELECT COUNT(*) FROM transcriptions")

if [[ $USERS_COUNT_SLAVE == *"2"* ]] && [[ $TRANSCRIPTIONS_COUNT_SLAVE == *"2"* ]]; then
    echo "✅ Test exitoso: Datos replicados correctamente en MySQL Slave"
else
    echo "❌ Test fallido: Datos no replicados correctamente en MySQL Slave"
    echo "Usuarios: $USERS_COUNT_SLAVE"
    echo "Transcripciones: $TRANSCRIPTIONS_COUNT_SLAVE"
    exit 1
fi

# 7. Modificar datos en MongoDB
echo "Modificando datos en MongoDB..."
python3 - <<EOF
from pymongo import MongoClient
from bson import ObjectId
from datetime import datetime

# Conectar a MongoDB
client = MongoClient("mongodb://airflow_user:airflow_pass@localhost:27017/myMindDB-Users")
db = client["myMindDB-Users"]
collection = db["users"]

# Modificar primer usuario
first_user = collection.find_one({"email": "user1@example.com"})
first_user["city"] = "Updated City"
first_user["transcriptions"].append({
    "_id": ObjectId(),
    "date": datetime(2025, 4, 8, 14, 20).isoformat(),
    "time": "14:20:00",
    "text": "Nueva transcripción de prueba.",
    "emotion": "neutral",
    "sentiment": "neutral",
    "topic": "test",
    "emotionProbabilities": {
        "joy": 0.10,
        "anger": 0.10,
        "sadness": 0.10,
        "disgust": 0.10,
        "fear": 0.10,
        "neutral": 0.30,
        "surprise": 0.10,
        "trust": 0.05,
        "anticipation": 0.05
    },
    "sentimentProbabilities": {
        "positive": 0.20,
        "negative": 0.20,
        "neutral": 0.60
    }
})

# Actualizar primer usuario
collection.replace_one({"_id": first_user["_id"]}, first_user)

# Eliminar segundo usuario
collection.delete_one({"email": "user2@example.com"})

print("Datos modificados en MongoDB: 1 usuario actualizado, 1 usuario eliminado, 1 transcripción añadida")
EOF

# 8. Ejecutar DAG de ETL nuevamente
echo "Ejecutando DAG de ETL nuevamente para sincronizar cambios..."
docker exec airflow-airflow-webserver-1 airflow dags trigger mymind_mongo_to_mysql_etl

# Esperar a que el DAG complete su ejecución
echo "Esperando a que el DAG complete la ejecución..."
sleep 30

# 9. Verificar cambios en MySQL Master
echo "Verificando cambios en MySQL Master..."
USERS_COUNT_AFTER=$(docker exec mysql_mymind mysql -uroot -p$MYSQL_ROOT_PASSWORD mymind_dw -e "SELECT COUNT(*) FROM users")
TRANSCRIPTIONS_COUNT_AFTER=$(docker exec mysql_mymind mysql -uroot -p$MYSQL_ROOT_PASSWORD mymind_dw -e "SELECT COUNT(*) FROM transcriptions")
CITY_UPDATE=$(docker exec mysql_mymind mysql -uroot -p$MYSQL_ROOT_PASSWORD mymind_dw -e "SELECT city FROM users WHERE email='user1@example.com'")

if [[ $USERS_COUNT_AFTER == *"1"* ]] && [[ $TRANSCRIPTIONS_COUNT_AFTER == *"2"* ]] && [[ $CITY_UPDATE == *"Updated City"* ]]; then
    echo "✅ Test exitoso: Cambios sincronizados correctamente en MySQL Master"
else
    echo "❌ Test fallido: Cambios no sincronizados correctamente en MySQL Master"
    echo "Usuarios: $USERS_COUNT_AFTER (esperado 1)"
    echo "Transcripciones: $TRANSCRIPTIONS_COUNT_AFTER (esperado 2)"
    echo "Ciudad actualizada: $CITY_UPDATE (esperado 'Updated City')"
    exit 1
fi

# 10. Simular fallo del Master
echo "Simulando fallo del Master..."
docker stop mysql_mymind

# 11. Ejecutar failover
echo "Ejecutando failover..."
./mysql/failover.sh

# Esperar a que se complete el failover
sleep 10

# 12. Verificar promoción del Slave a Master
echo "Verificando promoción del Slave a Master..."
READ_ONLY=$(docker exec mysql_mymind_slave mysql -uroot -p$MYSQL_ROOT_PASSWORD -e "SELECT @@read_only" | grep -v "read_only" | tr -d " ")

if [[ "$READ_ONLY" == "0" ]]; then
    echo "✅ Test exitoso: Slave promovido a Master correctamente"
else
    echo "❌ Test fallido: Slave no promovido a Master"
    exit 1
fi

# 13. Verificar conexión de Airflow actualizada
echo "Verificando que Airflow puede seguir funcionando con el nuevo Master..."
docker exec airflow-airflow-webserver-1 airflow connections get mysql_mymind_dw

# 14. Ejecutar DAG de ETL después del failover
echo "Ejecutando DAG de ETL después del failover..."
docker exec airflow-airflow-webserver-1 airflow dags trigger mymind_mongo_to_mysql_etl

# Esperar a que el DAG complete su ejecución
echo "Esperando a que el DAG complete la ejecución..."
sleep 30

# 15. Verificar que los datos siguen siendo accesibles
echo "Verificando datos después del failover..."
USERS_FINAL=$(docker exec mysql_mymind_slave mysql -uroot -p$MYSQL_ROOT_PASSWORD mymind_dw -e "SELECT COUNT(*) FROM users")

if [[ $USERS_FINAL == *"1"* ]]; then
    echo "✅ Test exitoso: Datos accesibles después del failover"
else
    echo "❌ Test fallido: Datos no accesibles después del failover"
    exit 1
fi

# Limpiar entorno
echo "Limpiando entorno de pruebas..."
docker-compose down

echo "Prueba de integración completada con éxito"
