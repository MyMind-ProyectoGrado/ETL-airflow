import pytest
import os
import pymongo
import pymysql
from dotenv import load_dotenv
import time
from datetime import datetime
import json
import uuid
import subprocess

# Load environment variables
load_dotenv()

# Database configurations
@pytest.fixture(scope="session")
def mongo_config():
    """MongoDB connection configuration."""
    # Use MongoDB Atlas URI or your specific MongoDB URI
    return {
        "uri": os.getenv("MONGO_URI", "mongodb+srv://juanjogomezarenas1:KByyM1bcZmDvdTDn@myminddb-users.cjeck.mongodb.net/?retryWrites=true&w=majority&appName=myMindDB-Users"),
        "db_name": os.getenv("MONGO_DB_NAME", "myMindDB-Users"),
        "collection": os.getenv("MONGO_COLLECTION", "users")
    }

@pytest.fixture(scope="session")
def mysql_config():
    """MySQL connection configuration."""
    return {
        "host": "localhost",
        "port": 3307,  # Port mapped to host
        "user": os.getenv("MYSQL_USER", "airflow_user"),
        "password": os.getenv("MYSQL_PASSWORD", "airflow_pass"),
        "db": os.getenv("MYSQL_DATABASE", "mymind_dw")
    }

@pytest.fixture(scope="session")
def mongo_client(mongo_config):
    """MongoDB client connection."""
    client = pymongo.MongoClient(mongo_config["uri"])
    yield client
    client.close()

@pytest.fixture(scope="session")
def mongo_db(mongo_client, mongo_config):
    """MongoDB database."""
    return mongo_client[mongo_config["db_name"]]

@pytest.fixture(scope="session")
def mongo_collection(mongo_db, mongo_config):
    """MongoDB collection."""
    return mongo_db[mongo_config["collection"]]

@pytest.fixture(scope="session")
def mysql_connection(mysql_config):
    """MySQL connection."""
    # Retry logic for MySQL connection
    max_retries = 5
    retry_delay = 2

    for attempt in range(max_retries):
        try:
            conn = pymysql.connect(
                host=mysql_config["host"],
                port=mysql_config["port"],
                user=mysql_config["user"],
                password=mysql_config["password"],
                database=mysql_config["db"],
                charset='utf8mb4',
                cursorclass=pymysql.cursors.DictCursor
            )
            print(f"✅ MySQL connection established successfully after {attempt+1} attempt(s)")
            yield conn
            conn.close()
            break
        except pymysql.Error as e:
            if attempt < max_retries - 1:
                print(f"MySQL connection attempt {attempt+1} failed: {e}. Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
            else:
                print(f"Failed to connect to MySQL after {max_retries} attempts: {e}")
                raise

@pytest.fixture(scope="function")
def mysql_cursor(mysql_connection):
    """MySQL cursor with automatic commits after test."""
    cursor = mysql_connection.cursor()
    yield cursor
    mysql_connection.commit()  # Commit any changes made during the test
    cursor.close()

@pytest.fixture
def airflow_dag_run():
    """
    Ejecuta el DAG de ETL en Airflow de manera automatizada.
    
    Retorna una función que puede ser llamada para ejecutar el DAG cuando sea necesario
    durante las pruebas, con el tiempo de espera especificado.
    """
    def _run_dag(wait_time=30):
        """
        Ejecuta el DAG de Airflow y espera el tiempo especificado.
        
        Args:
            wait_time: Tiempo de espera en segundos después de ejecutar el DAG
        
        Returns:
            bool: True si el DAG se ejecutó correctamente, False en caso contrario
        """
        # Encontrar el nombre correcto del contenedor de Airflow
        webserver_container = None
        try:
            # Listar contenedores que tengan 'airflow' y 'webserver' en su nombre
            find_cmd = "docker ps | grep airflow | grep webserver | awk '{print $1}'"
            containers = subprocess.run(find_cmd, shell=True, capture_output=True, text=True)
            
            if containers.stdout.strip():
                webserver_container = containers.stdout.strip().split('\n')[0]
                print(f"🔍 Contenedor de Airflow encontrado: {webserver_container}")
            else:
                webserver_container = "airflow-airflow-webserver-1"  # Nombre predeterminado
                print(f"⚠️ No se encontraron contenedores de Airflow. Usando nombre predeterminado: {webserver_container}")
        except Exception as e:
            webserver_container = "airflow-airflow-webserver-1"  # Valor predeterminado
            print(f"⚠️ Error al buscar contenedores: {str(e)}. Usando nombre predeterminado: {webserver_container}")
        
        # ID del DAG
        dag_id = "mymind_mongo_to_mysql_etl"
        
        # Asegurarse de que la conexión a MySQL esté correctamente configurada
        print("🔧 Configurando conexión a MySQL en Airflow...")
        try:
            # Eliminar la conexión existente si existe
            del_cmd = f"docker exec {webserver_container} airflow connections delete mysql_mymind_dw"
            subprocess.run(del_cmd, shell=True, capture_output=True, text=True)
            
            # Crear la nueva conexión
            add_cmd = f"docker exec {webserver_container} airflow connections add mysql_mymind_dw " \
                      f"--conn-type mysql " \
                      f"--conn-login airflow_user " \
                      f"--conn-password airflow_pass " \
                      f"--conn-host mysql_mymind_master " \
                      f"--conn-port 3306 " \
                      f"--conn-schema mymind_dw"
            
            result = subprocess.run(add_cmd, shell=True, capture_output=True, text=True)
            if result.returncode == 0:
                print("✅ Conexión a MySQL configurada exitosamente")
            else:
                print(f"⚠️ Error al configurar la conexión: {result.stderr}")
        except Exception as e:
            print(f"⚠️ Error al configurar la conexión: {str(e)}")
        
        # Ejecutar el DAG
        print(f"🚀 Ejecutando DAG: {dag_id}")
        try:
            # Opciones de comando para ejecutar el DAG
            commands = [
                f"docker exec {webserver_container} airflow dags trigger {dag_id}",
                f"docker exec {webserver_container} airflow dags trigger -c '{{\"force\": true}}' {dag_id}",
                f"docker exec {webserver_container} airflow dags backfill -s $(date +%Y-%m-%d) -e $(date +%Y-%m-%d) {dag_id}"
            ]
            
            # Intentar cada comando hasta que uno funcione
            for i, cmd in enumerate(commands):
                print(f"🔄 Intento {i+1}: {cmd}")
                result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
                
                if result.returncode == 0:
                    print(f"✅ DAG {dag_id} ejecutado exitosamente")
                    break
                else:
                    print(f"⚠️ Error al ejecutar el DAG: {result.stderr}")
                    
                    # Si es el último intento y todos fallaron
                    if i == len(commands) - 1:
                        print("❌ Todos los intentos de ejecutar el DAG fallaron")
                        return False
            
            # Esperar a que el DAG complete su ejecución
            print(f"⏳ Esperando {wait_time} segundos para que el DAG complete su ejecución...")
            time.sleep(wait_time)
            return True
            
        except Exception as e:
            print(f"❌ Error inesperado al ejecutar el DAG: {str(e)}")
            return False
    
    # Retornar la función de ejecución
    return _run_dag
