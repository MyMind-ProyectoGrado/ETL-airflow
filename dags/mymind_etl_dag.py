# ~/airflow/dags/mymind_etl_dag.py
from __future__ import annotations
import pendulum
import json
from bson import ObjectId
from datetime import datetime
import logging
import certifi
from airflow.decorators import dag, task
from airflow.providers.mysql.hooks.mysql import MySqlHook
from airflow.exceptions import AirflowSkipException
from airflow.hooks.base import BaseHook
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, ConfigurationError, OperationFailure

# IDs de las conexiones creadas en la UI de Airflow
MONGO_CONN_ID = "mongo_mymind"
MYSQL_CONN_ID = "mysql_mymind_dw"
# Constantes para bases de datos y tablas
MONGO_DB = "myMindDB-Users"
MONGO_COLLECTION = "users"
MYSQL_USERS_TABLE = "users"
MYSQL_TRANSCRIPTIONS_TABLE = "transcriptions"

# Configurar un logger básico
log = logging.getLogger(__name__)

# Función para convertir tipos BSON a tipos JSON serializables
def safe_bson_converter(obj):
    """Convierte tipos BSON como ObjectId y datetime a strings."""
    if isinstance(obj, ObjectId):
        return str(obj)
    elif isinstance(obj, datetime):
        return obj.isoformat()
    raise TypeError(f"Tipo no serializable: {type(obj)}")

@dag(
    dag_id="mymind_mongo_to_mysql_etl",
    # schedule="* * * * *", # Se ejecuta cada minuto
    schedule="0 0,6,12,18 * * *", # Se ejecuta cada 6 horas
    start_date=pendulum.datetime(2025, 4, 1, tz="UTC"),
    catchup=False,
    tags=["mymind", "etl", "mongodb", "mysql"],
    default_args={
        "owner": "airflow",
        "retries": 1,
    },
)
def mymind_mongo_to_mysql_etl():
    """
    DAG para realizar ETL desde MongoDB (MyMind) a MySQL.
    Adaptado para la nueva estructura de datos.
    """
    @task
    def extract_mongo_data() -> list[dict]:
        """
        Extrae documentos de MongoDB usando MongoClient directamente.
        Convierte tipos BSON (ObjectId, Date) a formatos serializables (str, ISO string).
        """
        log.info("Iniciando extracción desde MongoDB (usando MongoClient directo)...")
        client = None # Inicializar cliente a None
        try:
            # 1. Obtener el objeto de conexión de Airflow
            log.info(f"Obteniendo detalles de conexión para {MONGO_CONN_ID}...")
            conn = BaseHook.get_connection(MONGO_CONN_ID)
            
            # 2. Construir la URI manualmente con el esquema correcto
            is_srv = conn.extra_dejson.get('srv', False)
            
            # Construir la URI base con el esquema correcto
            if is_srv:
                mongo_uri = f"mongodb+srv://{conn.login}:{conn.password}@{conn.host}"
            else:
                mongo_uri = f"mongodb://{conn.login}:{conn.password}@{conn.host}"
                if conn.port:
                    mongo_uri += f":{conn.port}"
            
            # Añadir la base de datos si está presente
            if conn.schema:
                mongo_uri += f"/{conn.schema}"
            
            # Añadir parámetros de conexión desde extras
            params = []
            for key, value in conn.extra_dejson.items():
                if key not in ['srv', 'uri']:  # Excluir 'srv' y 'uri' que ya procesamos
                    if isinstance(value, bool):
                        # Convertir booleanos a strings para la URI
                        params.append(f"{key}={str(value).lower()}")
                    else:
                        params.append(f"{key}={value}")
            
            if params:
                mongo_uri += "?" + "&".join(params)
            
            log.info("URI de MongoDB construida correctamente.")
            
            # 3. Obtener timeouts y otros parámetros relevantes de 'extras' si existen
            connect_timeout_ms = conn.extra_dejson.get("connectTimeoutMS", 10000) # 10 segundos
            server_selection_timeout_ms = conn.extra_dejson.get("serverSelectionTimeoutMS", 30000) # 30 segundos
            log.info(f"Timeouts - Connect: {connect_timeout_ms}ms, ServerSelect: {server_selection_timeout_ms}ms")
            
            # 4. Crear el cliente MongoClient directamente
            log.info("Creando instancia de MongoClient...")
            client = MongoClient(
                mongo_uri,
                # Usar certifi para manejar certificados TLS/SSL de forma estándar
                tlsCAFile=certifi.where(),
                connectTimeoutMS=connect_timeout_ms,
                serverSelectionTimeoutMS=server_selection_timeout_ms
            )
            
            # 5. Probar la conexión (opcional pero recomendado)
            log.info("Probando conexión con MongoDB (ping)...")
            client.admin.command('ping')
            log.info("Conexión a MongoDB exitosa.")
            
            # 6. Acceder a la base de datos y colección
            db = client[MONGO_DB]
            collection = db[MONGO_COLLECTION]
            log.info(f"Accediendo a DB: '{MONGO_DB}', Colección: '{MONGO_COLLECTION}'")
            
            # 7. Extraer los documentos - Mantenemos la misma consulta ya que la estructura de colección no cambia
            log.info("Realizando find en la colección...")
            documents = list(collection.find({}, {
                "_id": 1,
                "name": 1,
                "email": 1,
                "profilePic": 1,
                "birthdate": 1,
                "city": 1,
                "personality": 1,
                "university": 1,
                "degree": 1,
                "gender": 1,
                "notifications": 1,
                "data_treatment": 1,
                "transcriptions": 1
            }))
            
            if not documents:
                log.info("No se encontraron documentos en MongoDB.")
                return []
            log.info(f"Se extrajeron {len(documents)} documentos de MongoDB. Iniciando conversión de tipos BSON...")
            
            # 8. Convertir tipos BSON
            converted_docs = []
            for doc in documents:
                try:
                    doc_str = json.dumps(doc, default=safe_bson_converter)
                    converted_doc = json.loads(doc_str)
                    converted_docs.append(converted_doc)
                except Exception as e:
                    log.error(f"Error convirtiendo documento {doc.get('_id', 'N/A')}: {e}", exc_info=True)
            log.info(f"Conversión de tipos completada. {len(converted_docs)} documentos listos para XCom.")
            return converted_docs
        except (ConnectionFailure, ConfigurationError, OperationFailure) as e:
            log.error(f"Error de PyMongo al conectar o ejecutar operación: {e}", exc_info=True)
            raise # Re-lanzar para que la tarea falle
        except Exception as e:
            log.error(f"Error inesperado durante la extracción: {e}", exc_info=True)
            raise # Re-lanzar para que la tarea falle
        finally:
            # 9. Asegurarse de cerrar la conexión
            if client:
                log.info("Cerrando conexión MongoClient.")
                client.close()

    @task
    def transform_data(mongo_docs: list[dict]) -> dict[str, list]:
        """
        Transforma los documentos extraídos de MongoDB a un formato
        adecuado para MySQL, adaptado a la nueva estructura.
        """
        log.info(f"Iniciando transformación de {len(mongo_docs)} documentos.")
        if not mongo_docs:
            log.info("No hay documentos para transformar.")
            return {"users": [], "transcriptions": [], "user_ids": [], "transcription_ids": []}
            
        users_rows = []
        transcriptions_rows = []
        user_ids = []
        transcription_ids = []
        
        for doc in mongo_docs:
            user_id = doc.get('_id')
            if not user_id:
                log.warning(f"Documento omitido por falta de _id: {doc}")
                continue # Saltar si no hay ID de usuario
            
            # Guardar ID del usuario para sincronización
            user_ids.append(user_id)
                
            # --- Preparar fila de usuario ---
            data_treatment = doc.get('data_treatment', {})
            privacy_prefs = data_treatment.get('privacy_preferences', {})
            
            # Manejar fechas - la estructura ahora tiene un objeto $date para acceptance_date
            birthdate_str = doc.get('birthdate')
            
            # Manejar el formato de acceptance_date que ahora está como objeto con $date
            acceptance_date_str = None
            if data_treatment and 'acceptance_date' in data_treatment:
                # Verificar si viene como objeto $date o directamente como string
                if isinstance(data_treatment['acceptance_date'], dict) and '$date' in data_treatment['acceptance_date']:
                    acceptance_date_str = data_treatment['acceptance_date']['$date']
                else:
                    acceptance_date_str = data_treatment.get('acceptance_date')
            
            # Formatear fechas para MySQL
            mysql_birthdate = birthdate_str[:10] if birthdate_str else None # YYYY-MM-DD
            mysql_acceptance_date = acceptance_date_str[:19].replace('T', ' ') if acceptance_date_str else None # YYYY-MM-DD HH:MM:SS
            
            user_row = (
                user_id,
                doc.get('name'),
                doc.get('email'),
                doc.get('profilePic'),
                mysql_birthdate,
                doc.get('city'),
                doc.get('personality'),
                doc.get('university'),
                doc.get('degree'),
                doc.get('gender'),
                doc.get('notifications'),
                data_treatment.get('accept_policies'),
                mysql_acceptance_date,
                data_treatment.get('acceptance_ip'),
                privacy_prefs.get('allow_anonimized_usage')
            )
            users_rows.append(user_row)
            
            # --- Preparar filas de transcripciones con los campos adicionales de probabilidades ---
            if 'transcriptions' in doc and doc['transcriptions']:
                for trans in doc['transcriptions']:
                    transcription_id = trans.get('_id')
                    if not transcription_id:
                        log.warning(f"Transcripción omitida por falta de _id en usuario {user_id}")
                        continue
                    
                    # Guardar ID de transcripción para sincronización
                    transcription_ids.append(transcription_id)
                        
                    # Formatear fecha de transcripción
                    transcription_date_str = trans.get('date')
                    mysql_trans_date = transcription_date_str[:10] if transcription_date_str else None
                    
                    # Obtener probabilidades de emociones y sentimientos
                    emotion_probs = trans.get('emotionProbabilities', {})
                    sentiment_probs = trans.get('sentimentProbabilities', {})
                    
                    # Crear la fila con todos los campos de probabilidades
                    transcription_row = (
                        transcription_id,
                        user_id,
                        mysql_trans_date,
                        trans.get('time'),
                        trans.get('text'),
                        trans.get('emotion'),
                        trans.get('sentiment'),
                        trans.get('topic'),
                        # Probabilidades de emociones
                        emotion_probs.get('joy'),
                        emotion_probs.get('anger'),
                        emotion_probs.get('sadness'),
                        emotion_probs.get('disgust'),
                        emotion_probs.get('fear'),
                        emotion_probs.get('neutral'),
                        emotion_probs.get('surprise'),
                        emotion_probs.get('trust'),
                        emotion_probs.get('anticipation'),
                        # Probabilidades de sentimiento
                        sentiment_probs.get('positive'),
                        sentiment_probs.get('negative'),
                        sentiment_probs.get('neutral')
                    )
                    transcriptions_rows.append(transcription_row)
                    
        log.info(f"Transformación completada: {len(users_rows)} filas de usuarios, {len(transcriptions_rows)} filas de transcripciones.")
        return {
            "users": users_rows, 
            "transcriptions": transcriptions_rows,
            "user_ids": user_ids,
            "transcription_ids": transcription_ids
        }

    @task
    def sync_and_load_mysql(transformed_data: dict[str, list]):
        """
        Sincroniza y carga los datos transformados en las tablas de MySQL.
        1. Inserta/actualiza registros existentes
        2. Elimina registros que ya no existen en MongoDB
        """
        users_to_load = transformed_data.get("users", [])
        transcriptions_to_load = transformed_data.get("transcriptions", [])
        mongo_user_ids = transformed_data.get("user_ids", [])
        mongo_transcription_ids = transformed_data.get("transcription_ids", [])
        
        if not users_to_load and not transcriptions_to_load:
            log.info("No hay datos transformados para cargar en MySQL.")
            return
            
        log.info(f"Iniciando sincronización y carga a MySQL: {len(users_to_load)} usuarios, {len(transcriptions_to_load)} transcripciones.")
        mysql_hook = MySqlHook(mysql_conn_id=MYSQL_CONN_ID)
        
        # Usar una transacción para asegurar atomicidad
        conn = mysql_hook.get_conn()
        cursor = conn.cursor()
        
        try:
            # Obtener IDs actuales desde MySQL
            log.info("Obteniendo IDs actuales desde MySQL...")
            cursor.execute(f"SELECT user_id FROM {MYSQL_USERS_TABLE}")
            mysql_user_ids = [row[0] for row in cursor.fetchall()]
            
            cursor.execute(f"SELECT transcription_id FROM {MYSQL_TRANSCRIPTIONS_TABLE}")
            mysql_transcription_ids = [row[0] for row in cursor.fetchall()]
            
            # Encontrar registros a eliminar (en MySQL pero no en MongoDB)
            users_to_delete = [uid for uid in mysql_user_ids if uid not in mongo_user_ids]
            transcriptions_to_delete = [tid for tid in mysql_transcription_ids if tid not in mongo_transcription_ids]
            
            log.info(f"Usuarios a eliminar: {len(users_to_delete)}")
            log.info(f"Transcripciones a eliminar: {len(transcriptions_to_delete)}")
            
            # Deshabilitar temporalmente las verificaciones de clave foránea
            cursor.execute("SET FOREIGN_KEY_CHECKS=0")
            
            # --- Eliminar transcripciones obsoletas ---
            if transcriptions_to_delete:
                format_strings = ','.join(['%s'] * len(transcriptions_to_delete))
                delete_trans_sql = f"DELETE FROM {MYSQL_TRANSCRIPTIONS_TABLE} WHERE transcription_id IN ({format_strings})"
                cursor.execute(delete_trans_sql, transcriptions_to_delete)
                log.info(f"Se eliminaron {cursor.rowcount} transcripciones obsoletas.")
            
            # --- Eliminar usuarios obsoletos ---
            if users_to_delete:
                # Primero eliminar las transcripciones asociadas a estos usuarios
                format_strings = ','.join(['%s'] * len(users_to_delete))
                delete_trans_sql = f"DELETE FROM {MYSQL_TRANSCRIPTIONS_TABLE} WHERE user_id IN ({format_strings})"
                cursor.execute(delete_trans_sql, users_to_delete)
                log.info(f"Se eliminaron {cursor.rowcount} transcripciones de usuarios obsoletos.")
                
                # Luego eliminar los usuarios
                delete_users_sql = f"DELETE FROM {MYSQL_USERS_TABLE} WHERE user_id IN ({format_strings})"
                cursor.execute(delete_users_sql, users_to_delete)
                log.info(f"Se eliminaron {cursor.rowcount} usuarios obsoletos.")
            
            # --- Cargar Usuarios ---
            if users_to_load:
                user_target_fields = [
                    'user_id', 'name', 'email', 'profile_pic', 'birthdate', 'city',
                    'personality', 'university', 'degree', 'gender', 'notifications',
                    'accept_policies', 'acceptance_date', 'acceptance_ip', 'allow_anonimized_usage'
                ]
                
                log.info(f"Cargando {len(users_to_load)} usuarios en la tabla {MYSQL_USERS_TABLE}...")
                
                # Usar INSERT ... ON DUPLICATE KEY UPDATE en lugar de REPLACE
                user_sql = f"""
                INSERT INTO {MYSQL_USERS_TABLE} 
                ({', '.join(user_target_fields)}) 
                VALUES ({', '.join(['%s'] * len(user_target_fields))})
                ON DUPLICATE KEY UPDATE
                name = VALUES(name),
                email = VALUES(email),
                profile_pic = VALUES(profile_pic),
                birthdate = VALUES(birthdate),
                city = VALUES(city),
                personality = VALUES(personality),
                university = VALUES(university),
                degree = VALUES(degree),
                gender = VALUES(gender),
                notifications = VALUES(notifications),
                accept_policies = VALUES(accept_policies),
                acceptance_date = VALUES(acceptance_date),
                acceptance_ip = VALUES(acceptance_ip),
                allow_anonimized_usage = VALUES(allow_anonimized_usage)
                """
                
                cursor.executemany(user_sql, users_to_load)
                log.info("Usuarios cargados exitosamente.")
            
            # --- Cargar Transcripciones ---
            if transcriptions_to_load:
                transcription_target_fields = [
                    'transcription_id', 'user_id', 'transcription_date', 'transcription_time',
                    'text', 'emotion', 'sentiment', 'topic',
                    'emotion_probs_joy', 'emotion_probs_anger', 'emotion_probs_sadness',
                    'emotion_probs_disgust', 'emotion_probs_fear', 'emotion_probs_neutral',
                    'emotion_probs_surprise', 'emotion_probs_trust', 'emotion_probs_anticipation',
                    'sentiment_probs_positive', 'sentiment_probs_negative', 'sentiment_probs_neutral'
                ]
                
                log.info(f"Cargando {len(transcriptions_to_load)} transcripciones en la tabla {MYSQL_TRANSCRIPTIONS_TABLE}...")
                
                # Usar INSERT ... ON DUPLICATE KEY UPDATE
                trans_sql = f"""
                INSERT INTO {MYSQL_TRANSCRIPTIONS_TABLE} 
                ({', '.join(transcription_target_fields)}) 
                VALUES ({', '.join(['%s'] * len(transcription_target_fields))})
                ON DUPLICATE KEY UPDATE
                user_id = VALUES(user_id),
                transcription_date = VALUES(transcription_date),
                transcription_time = VALUES(transcription_time),
                text = VALUES(text),
                emotion = VALUES(emotion),
                sentiment = VALUES(sentiment),
                topic = VALUES(topic),
                emotion_probs_joy = VALUES(emotion_probs_joy),
                emotion_probs_anger = VALUES(emotion_probs_anger),
                emotion_probs_sadness = VALUES(emotion_probs_sadness),
                emotion_probs_disgust = VALUES(emotion_probs_disgust),
                emotion_probs_fear = VALUES(emotion_probs_fear),
                emotion_probs_neutral = VALUES(emotion_probs_neutral),
                emotion_probs_surprise = VALUES(emotion_probs_surprise),
                emotion_probs_trust = VALUES(emotion_probs_trust),
                emotion_probs_anticipation = VALUES(emotion_probs_anticipation),
                sentiment_probs_positive = VALUES(sentiment_probs_positive),
                sentiment_probs_negative = VALUES(sentiment_probs_negative),
                sentiment_probs_neutral = VALUES(sentiment_probs_neutral)
                """
                
                cursor.executemany(trans_sql, transcriptions_to_load)
                log.info("Transcripciones cargadas exitosamente.")
            
            # Rehabilitar las verificaciones de clave foránea
            cursor.execute("SET FOREIGN_KEY_CHECKS=1")
            
            # Confirmar la transacción
            conn.commit()
            log.info("Sincronización y carga a MySQL completada con éxito.")
            
        except Exception as e:
            # Si hay un error, hacer rollback
            conn.rollback()
            log.error(f"Error durante la carga a MySQL: {e}", exc_info=True)
            raise
        finally:
            # Asegurarse de cerrar el cursor y la conexión
            cursor.close()
            conn.close()

    # Definir flujo del DAG
    mongo_data = extract_mongo_data()
    transformed_data = transform_data(mongo_data)
    sync_and_load_mysql(transformed_data)

# Instanciar el DAG
mymind_mongo_to_mysql_etl()
