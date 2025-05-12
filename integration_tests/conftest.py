import pytest
import os
import pymongo
import pymysql
from dotenv import load_dotenv
import time
from datetime import datetime
import json
import uuid

# Cargar variables de entorno
load_dotenv()

# Configuraciones de bases de datos
@pytest.fixture(scope="session")
def mongo_config():
    """Configuración de conexión a MongoDB."""
    # Usar la URI de MongoDB Atlas en lugar de localhost
    return {
        "uri": os.getenv("MONGO_URI", "mongodb+srv://juanjogomezarenas1:KByyM1bcZmDvdTDn@myminddb-users.cjeck.mongodb.net/?retryWrites=true&w=majority&appName=myMindDB-Users"),
        "db_name": os.getenv("MONGO_DB_NAME", "myMindDB-Users"),
        "collection": os.getenv("MONGO_COLLECTION", "users")
    }

@pytest.fixture(scope="session")
def mysql_config():
    """Configuración de conexión a MySQL."""
    return {
        "host": "localhost",
        "port": 3307,  # Puerto mapeado al host
        "user": os.getenv("MYSQL_USER", "airflow_user"),
        "password": os.getenv("MYSQL_PASSWORD", "airflow_pass"),
        "db": os.getenv("MYSQL_DB", "mymind_dw")
    }

@pytest.fixture(scope="session")
def mongo_client(mongo_config):
    """Cliente de conexión a MongoDB."""
    client = pymongo.MongoClient(mongo_config["uri"])
    yield client
    client.close()

@pytest.fixture(scope="session")
def mongo_db(mongo_client, mongo_config):
    """Base de datos MongoDB."""
    return mongo_client[mongo_config["db_name"]]

@pytest.fixture(scope="session")
def mongo_collection(mongo_db, mongo_config):
    """Colección de MongoDB."""
    return mongo_db[mongo_config["collection"]]

@pytest.fixture(scope="session")
def mysql_connection(mysql_config):
    """Conexión a MySQL."""
    conn = pymysql.connect(
        host=mysql_config["host"],
        port=mysql_config["port"],
        user=mysql_config["user"],
        password=mysql_config["password"],
        database=mysql_config["db"]
    )
    yield conn
    conn.close()

@pytest.fixture(scope="session")
def mysql_cursor(mysql_connection):
    """Cursor de MySQL."""
    cursor = mysql_connection.cursor(pymysql.cursors.DictCursor)
    yield cursor
    cursor.close()

@pytest.fixture
def sample_user_data():
    """Datos de muestra para un usuario con transcripciones."""
    # Usamos UUID en lugar de ObjectId para evitar problemas con bson
    unique_id = str(uuid.uuid4())
    timestamp = datetime.now().isoformat()
    
    return {
        "_id": unique_id,
        "name": f"ETL Test User {unique_id[:8]}",
        "email": f"etl_test_{unique_id[:8]}@example.com",
        "profilePic": "https://example.com/pic.jpg",
        "birthdate": "1990-05-15T00:00:00",
        "city": "Test City",
        "personality": "Extrovertido",
        "university": "Test University",
        "degree": "Computer Science",
        "gender": "Masculino",
        "notifications": True,
        "data_treatment": {
            "accept_policies": True,
            "acceptance_date": timestamp,
            "acceptance_ip": "192.168.1.100",
            "privacy_preferences": {
                "allow_anonimized_usage": True
            }
        },
        "transcriptions": [
            {
                "_id": str(uuid.uuid4()),
                "date": timestamp.split("T")[0],
                "time": timestamp.split("T")[1][:8],
                "text": "Estoy muy feliz con los resultados de las pruebas.",
                "emotion": "joy",
                "emotionProbabilities": {
                    "joy": 0.85,
                    "anger": 0.02,
                    "sadness": 0.03,
                    "disgust": 0.01,
                    "fear": 0.01,
                    "neutral": 0.05,
                    "surprise": 0.01,
                    "trust": 0.01,
                    "anticipation": 0.01
                },
                "sentiment": "positive",
                "sentimentProbabilities": {
                    "positive": 0.90,
                    "negative": 0.05,
                    "neutral": 0.05
                },
                "topic": "trabajo"
            },
            {
                "_id": str(uuid.uuid4()),
                "date": timestamp.split("T")[0],
                "time": timestamp.split("T")[1][:8],
                "text": "Me preocupa un poco la reunión de mañana.",
                "emotion": "fear",
                "emotionProbabilities": {
                    "joy": 0.05,
                    "anger": 0.10,
                    "sadness": 0.15,
                    "disgust": 0.05,
                    "fear": 0.55,
                    "neutral": 0.05,
                    "surprise": 0.02,
                    "trust": 0.02,
                    "anticipation": 0.01
                },
                "sentiment": "negative",
                "sentimentProbabilities": {
                    "positive": 0.10,
                    "negative": 0.70,
                    "neutral": 0.20
                },
                "topic": "trabajo"
            }
        ]
    }

@pytest.fixture
def insert_test_data(mongo_collection, sample_user_data):
    """Inserta datos de prueba en MongoDB y los limpia después."""
    # Insertar datos de prueba
    mongo_collection.insert_one(sample_user_data)
    
    # Devolver ID para referencia y limpieza
    user_id = sample_user_data["_id"]
    transcription_ids = [t["_id"] for t in sample_user_data["transcriptions"]]
    
    yield user_id, transcription_ids
    
    # Limpiar después de la prueba
    mongo_collection.delete_one({"_id": user_id})

@pytest.fixture
def airflow_dag_run():
    """
    Ejecuta el DAG de ETL y espera a que termine.
    
    Nota: Esta es una simulación simplificada. En un entorno real,
    se usaría la API de Airflow para disparar y monitorear el DAG.
    """
    # Comando para ejecutar el DAG a través de la CLI de Airflow
    # Este comando debe ejecutarse desde el entorno de Airflow
    dag_id = "mymind_mongo_to_mysql_etl"
    
    # Crear la cadena JSON sin escape problemático
    conf = json.dumps({"mock": "test"})
    trigger_command = f"docker exec airflow-airflow-webserver-1 airflow dags trigger {dag_id} --conf '{conf}'"
    
    try:
        # Ejecutar en shell
        print(f"Ejecutando comando: {trigger_command}")
        result = os.system(trigger_command)
        print(f"Resultado del comando: {result}")
        
        # Dar tiempo a que el DAG se ejecute (en un entorno real, se verificaría el estado del DAG)
        print(f"DAG {dag_id} disparado. Esperando 60 segundos para completar...")
        time.sleep(60)  # Tiempo estimado para que el DAG complete
        return True
    except Exception as e:
        print(f"Error al ejecutar el DAG: {str(e)}")
        return False
