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

MONGO_CONN_ID = "mongo_mymind"
MYSQL_CONN_ID = "mysql_mymind_dw"
MONGO_DB = "myMindDB-Users"
MONGO_COLLECTION = "users"
MYSQL_USERS_TABLE = "users"
MYSQL_TRANSCRIPTIONS_TABLE = "transcriptions"

log = logging.getLogger(__name__)

def safe_bson_converter(obj):
    if isinstance(obj, ObjectId):
        return str(obj)
    elif isinstance(obj, datetime):
        return obj.isoformat()
    raise TypeError(f"Tipo no serializable: {type(obj)}")

@dag(
    dag_id="mymind_mongo_to_mysql_etl",
    schedule="* * * * *",
    max_active_runs=2,
    start_date=pendulum.datetime(2025, 4, 1, tz="UTC"),
    catchup=False,
    tags=["mymind", "etl", "mongodb", "mysql"],
    default_args={"owner": "airflow", "retries": 1},
)
def mymind_mongo_to_mysql_etl():
    @task
    def extract_mongo_data() -> list[dict]:
        log.info("Extrayendo datos de MongoDB...")
        conn = BaseHook.get_connection(MONGO_CONN_ID)
        is_srv = conn.extra_dejson.get('srv', False)
        mongo_uri = f"mongodb+srv://{conn.login}:{conn.password}@{conn.host}" if is_srv else f"mongodb://{conn.login}:{conn.password}@{conn.host}"
        if conn.port:
            mongo_uri += f":{conn.port}"
        if conn.schema:
            mongo_uri += f"/{conn.schema}"
        params = [f"{k}={str(v).lower() if isinstance(v, bool) else v}" for k, v in conn.extra_dejson.items() if k not in ['srv', 'uri']]
        if params:
            mongo_uri += "?" + "&".join(params)

        client = MongoClient(
            mongo_uri,
            tlsCAFile=certifi.where(),
            connectTimeoutMS=conn.extra_dejson.get("connectTimeoutMS", 10000),
            serverSelectionTimeoutMS=conn.extra_dejson.get("serverSelectionTimeoutMS", 30000)
        )
        client.admin.command('ping')
        collection = client[MONGO_DB][MONGO_COLLECTION]
        documents = list(collection.find({}, {
            "_id": 1, "name": 1, "email": 1, "profilePic": 1, "birthdate": 1, "city": 1,
            "personality": 1, "university": 1, "degree": 1, "gender": 1, "notifications": 1,
            "data_treatment": 1, "transcriptions": 1
        }))
        client.close()

        return [
            json.loads(json.dumps(doc, default=safe_bson_converter)) for doc in documents
        ]

    @task
    def transform_data(mongo_docs: list[dict]) -> dict[str, list]:
        users_rows = []
        transcriptions_rows = []
        for doc in mongo_docs:
            user_id = doc.get('_id')
            if not user_id:
                continue
            data_treatment = doc.get('data_treatment', {})
            privacy_prefs = data_treatment.get('privacy_preferences', {})
            birthdate_str = doc.get('birthdate')
            acceptance_date_str = data_treatment.get('acceptance_date', {}).get('$date') if isinstance(data_treatment.get('acceptance_date'), dict) else data_treatment.get('acceptance_date')
            user_row = (
                user_id,
                doc.get('name'),
                doc.get('email'),
                doc.get('profilePic'),
                birthdate_str[:10] if birthdate_str else None,
                doc.get('city'),
                doc.get('personality'),
                doc.get('university'),
                doc.get('degree'),
                doc.get('gender'),
                doc.get('notifications'),
                data_treatment.get('accept_policies'),
                acceptance_date_str[:19].replace('T', ' ') if acceptance_date_str else None,
                data_treatment.get('acceptance_ip'),
                privacy_prefs.get('allow_anonimized_usage')
            )
            users_rows.append(user_row)

            for trans in doc.get('transcriptions', []):
                trans_id = trans.get('_id')
                if not trans_id:
                    continue
                emotion_probs = trans.get('emotionProbabilities', {})
                sentiment_probs = trans.get('sentimentProbabilities', {})
                trans_row = (
                    trans_id,
                    user_id,
                    trans.get('date', '')[:10],
                    trans.get('time'),
                    trans.get('text'),
                    trans.get('emotion'),
                    trans.get('sentiment'),
                    trans.get('topic'),
                    emotion_probs.get('joy'),
                    emotion_probs.get('anger'),
                    emotion_probs.get('sadness'),
                    emotion_probs.get('disgust'),
                    emotion_probs.get('fear'),
                    emotion_probs.get('neutral'),
                    emotion_probs.get('surprise'),
                    emotion_probs.get('trust'),
                    emotion_probs.get('anticipation'),
                    sentiment_probs.get('positive'),
                    sentiment_probs.get('negative'),
                    sentiment_probs.get('neutral')
                )
                transcriptions_rows.append(trans_row)

        return {"users": users_rows, "transcriptions": transcriptions_rows}

    @task
    def sync_and_load_mysql(transformed_data: dict[str, list]):
        mysql_hook = MySqlHook(mysql_conn_id=MYSQL_CONN_ID)
        conn = mysql_hook.get_conn()
        cursor = conn.cursor()

        users = transformed_data.get("users", [])
        transcriptions = transformed_data.get("transcriptions", [])
        current_user_ids = {row[0] for row in users}
        current_trans_ids = {row[0] for row in transcriptions}

        log.info("Obteniendo IDs actuales desde MySQL...")
        cursor.execute(f"SELECT user_id FROM {MYSQL_USERS_TABLE}")
        db_user_ids = {row[0] for row in cursor.fetchall()}
        cursor.execute(f"SELECT transcription_id FROM {MYSQL_TRANSCRIPTIONS_TABLE}")
        db_trans_ids = {row[0] for row in cursor.fetchall()}

        users_to_delete = db_user_ids - current_user_ids
        trans_to_delete = db_trans_ids - current_trans_ids

        if users_to_delete:
            log.info(f"Eliminando {len(users_to_delete)} usuarios obsoletos...")
            cursor.execute(f"DELETE FROM {MYSQL_USERS_TABLE} WHERE user_id IN ({','.join(['%s']*len(users_to_delete))})", tuple(users_to_delete))
        if trans_to_delete:
            log.info(f"Eliminando {len(trans_to_delete)} transcripciones obsoletas...")
            cursor.execute(f"DELETE FROM {MYSQL_TRANSCRIPTIONS_TABLE} WHERE transcription_id IN ({','.join(['%s']*len(trans_to_delete))})", tuple(trans_to_delete))

        if users:
            log.info(f"Cargando {len(users)} usuarios...")
            cursor.executemany(
                f"""REPLACE INTO {MYSQL_USERS_TABLE} (
                    user_id, name, email, profile_pic, birthdate, city, personality, university,
                    degree, gender, notifications, accept_policies, acceptance_date,
                    acceptance_ip, allow_anonimized_usage
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                )""",
                users
            )

        if transcriptions:
            log.info(f"Cargando {len(transcriptions)} transcripciones...")
            cursor.executemany(
                f"""REPLACE INTO {MYSQL_TRANSCRIPTIONS_TABLE} (
                    transcription_id, user_id, transcription_date, transcription_time,
                    text, emotion, sentiment, topic,
                    emotion_probs_joy, emotion_probs_anger, emotion_probs_sadness,
                    emotion_probs_disgust, emotion_probs_fear, emotion_probs_neutral,
                    emotion_probs_surprise, emotion_probs_trust, emotion_probs_anticipation,
                    sentiment_probs_positive, sentiment_probs_negative, sentiment_probs_neutral
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                )""",
                transcriptions
            )

        conn.commit()
        cursor.close()
        conn.close()
        log.info("Carga y sincronización con MySQL completada.")

    mongo_data = extract_mongo_data()
    transformed = transform_data(mongo_data)
    sync_and_load_mysql(transformed)

mymind_mongo_to_mysql_etl()

