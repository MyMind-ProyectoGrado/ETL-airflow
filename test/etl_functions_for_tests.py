# etl_functions_for_tests.py
from bson import ObjectId
from datetime import datetime
import json
import logging

# Importa estas clases para que sean patcheables desde las pruebas
from airflow.hooks.base import BaseHook
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, ConfigurationError, OperationFailure
from airflow.providers.mysql.hooks.mysql import MySqlHook

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

def extract_mongo_data(mongo_conn_id, mongo_db, mongo_collection):
    """Versión sin decorador @task para pruebas."""
    # Esta implementación será reemplazada por mocks en las pruebas
    log.info("Esta función será mockeada en las pruebas")
    return []

def transform_data(mongo_docs):
    """
    Transforma los documentos extraídos de MongoDB a un formato
    adecuado para MySQL, adaptado a la nueva estructura.
    Versión sin decorador @task para pruebas.
    """
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
                
    return {
        "users": users_rows, 
        "transcriptions": transcriptions_rows,
        "user_ids": user_ids,
        "transcription_ids": transcription_ids
    }

def sync_and_load_mysql(transformed_data, mysql_conn_id, users_table, transcriptions_table):
    """Versión sin decorador @task para pruebas."""
    # Esta implementación será reemplazada por mocks en las pruebas
    log.info("Esta función será mockeada en las pruebas")
    return True  # Devolver True para las pruebas
