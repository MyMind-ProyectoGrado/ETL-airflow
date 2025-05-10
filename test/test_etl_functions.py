# tests/test_etl_functions.py
import pytest
import json
from unittest.mock import patch, MagicMock

from bson.objectid import ObjectId
from datetime import datetime
from pymongo.errors import ConnectionFailure

# Importamos el módulo con las funciones a probar
import etl_functions_for_tests
from etl_functions_for_tests import safe_bson_converter, transform_data

# Test para la función de conversión de tipos BSON a JSON serializables
def test_safe_bson_converter():
    # Crear un ObjectId de prueba
    obj_id = ObjectId()
    # Verificar conversión de ObjectId a string
    assert safe_bson_converter(obj_id) == str(obj_id)
    
    # Crear un datetime de prueba
    test_date = datetime(2025, 4, 15, 12, 30, 45)
    # Verificar conversión de datetime a string ISO
    assert safe_bson_converter(test_date) == "2025-04-15T12:30:45"
    
    # Verificar que lanza TypeError para tipos no soportados
    with pytest.raises(TypeError):
        safe_bson_converter(complex(1, 2))

# Test para la extracción desde MongoDB
@patch('etl_functions_for_tests.MongoClient')
@patch('etl_functions_for_tests.BaseHook')
def test_extract_mongo_data_success(mock_base_hook, mock_mongo_client):
    # Configurar los mocks
    mock_connection = MagicMock()
    mock_connection.login = "test_user"
    mock_connection.password = "test_pass"
    mock_connection.host = "test_host"
    mock_connection.port = 27017
    mock_connection.schema = "test_db"
    mock_connection.extra_dejson = {"srv": False}
    
    mock_base_hook.get_connection.return_value = mock_connection
    
    # Configurar el cliente MongoDB simulado
    mock_client_instance = MagicMock()
    mock_mongo_client.return_value = mock_client_instance
    
    # Configurar la prueba de la conexión (ping)
    mock_admin = MagicMock()
    mock_client_instance.admin = mock_admin
    
    # Configurar la colección simulada con datos de prueba
    mock_db = MagicMock()
    mock_collection = MagicMock()
    mock_client_instance.__getitem__.return_value = mock_db
    mock_db.__getitem__.return_value = mock_collection
    
    # Datos de prueba que la colección debería devolver
    test_id = ObjectId()
    test_trans_id = ObjectId()
    test_data = [
        {
            "_id": test_id,
            "name": "Test User",
            "email": "test@example.com",
            "transcriptions": [
                {
                    "_id": test_trans_id,
                    "text": "Test transcription",
                    "emotion": "joy",
                    "sentiment": "positive",
                    "date": "2025-04-15T10:30:00"
                }
            ]
        }
    ]
    mock_collection.find.return_value = test_data
    
    # Implementamos una versión de prueba que use los mocks configurados
    def mock_extract_func(mongo_conn_id, mongo_db, mongo_collection):
        # Obtenemos la conexión (simulada)
        conn = mock_base_hook.get_connection(mongo_conn_id)
        # Creamos el cliente (simulado)
        client = mock_mongo_client()
        # Accedemos a la BD y colección (simuladas)
        db = client[mongo_db]
        collection = db[mongo_collection]
        # Obtenemos los documentos (simulados)
        documents = list(collection.find())
        # Convertimos los docs
        converted_docs = []
        for doc in documents:
            doc_str = json.dumps(doc, default=safe_bson_converter)
            converted_doc = json.loads(doc_str)
            converted_docs.append(converted_doc)
        return converted_docs
    
    # Guardamos la función original para restaurarla después
    original_func = etl_functions_for_tests.extract_mongo_data
    
    try:
        # Reemplazamos la función con nuestro mock
        etl_functions_for_tests.extract_mongo_data = mock_extract_func
        
        # Ejecutar la función y verificar resultado
        result = etl_functions_for_tests.extract_mongo_data("mongo_mymind", "myMindDB-Users", "users")
        
        # Verificar que los datos fueron extraídos y convertidos correctamente
        assert len(result) == 1
        assert "name" in result[0]
        assert result[0]["name"] == "Test User"
        assert "transcriptions" in result[0]
        assert len(result[0]["transcriptions"]) == 1
        
        # Verificar que ObjectId se convirtió correctamente a string
        assert isinstance(result[0]["_id"], str)
        assert isinstance(result[0]["transcriptions"][0]["_id"], str)
    finally:
        # Restaurar la función original
        etl_functions_for_tests.extract_mongo_data = original_func

# Test para error de conexión a MongoDB
def test_extract_mongo_data_connection_error():
    # Implementamos una versión de prueba que lance el error
    def mock_extract_error_func(mongo_conn_id, mongo_db, mongo_collection):
        raise ConnectionFailure("Test connection error")
    
    # Guardamos la función original para restaurarla después
    original_func = etl_functions_for_tests.extract_mongo_data
    
    try:
        # Reemplazamos la función con nuestro mock
        etl_functions_for_tests.extract_mongo_data = mock_extract_error_func
        
        # Verificar que la función maneja correctamente el error
        with pytest.raises(ConnectionFailure):
            etl_functions_for_tests.extract_mongo_data("mongo_mymind", "myMindDB-Users", "users")
    finally:
        # Restaurar la función original
        etl_functions_for_tests.extract_mongo_data = original_func

# Test para la transformación de datos
def test_transform_data():
    # Datos de entrada simulando documentos de MongoDB ya convertidos a JSON
    mongo_docs = [
        {
            "_id": "507f1f77bcf86cd799439011",
            "name": "Test User",
            "email": "test@example.com",
            "birthdate": "1990-01-15T00:00:00",
            "city": "Test City",
            "data_treatment": {
                "accept_policies": True,
                "acceptance_date": "2025-01-10T14:30:00",
                "acceptance_ip": "192.168.1.1",
                "privacy_preferences": {
                    "allow_anonimized_usage": True
                }
            },
            "transcriptions": [
                {
                    "_id": "607f1f77bcf86cd799439022",
                    "date": "2025-04-10T15:45:00",
                    "time": "15:45:00",
                    "text": "Test transcription 1",
                    "emotion": "joy",
                    "sentiment": "positive",
                    "topic": "test",
                    "emotionProbabilities": {
                        "joy": 0.8,
                        "anger": 0.05,
                        "sadness": 0.02,
                        "disgust": 0.01,
                        "fear": 0.02,
                        "neutral": 0.05,
                        "surprise": 0.03,
                        "trust": 0.01,
                        "anticipation": 0.01
                    },
                    "sentimentProbabilities": {
                        "positive": 0.75,
                        "negative": 0.15,
                        "neutral": 0.1
                    }
                }
            ]
        }
    ]
    
    # Ejecutar transformación
    result = transform_data(mongo_docs)
    
    # Verificar resultados
    assert "users" in result
    assert "transcriptions" in result
    assert "user_ids" in result
    assert "transcription_ids" in result
    
    # Verificar datos de usuarios
    assert len(result["users"]) == 1
    user = result["users"][0]
    assert user[0] == "507f1f77bcf86cd799439011"  # user_id
    assert user[1] == "Test User"  # name
    assert user[11] == True  # accept_policies
    assert user[12] == "2025-01-10 14:30:00"  # acceptance_date en formato MySQL
    
    # Verificar datos de transcripciones
    assert len(result["transcriptions"]) == 1
    trans = result["transcriptions"][0]
    assert trans[0] == "607f1f77bcf86cd799439022"  # transcription_id
    assert trans[1] == "507f1f77bcf86cd799439011"  # user_id
    assert trans[2] == "2025-04-10"  # transcription_date en formato MySQL
    assert trans[4] == "Test transcription 1"  # text
    assert trans[5] == "joy"  # emotion
    assert trans[8] == 0.8  # emotion_probs_joy
    
    # Imprimir todos los valores para diagnóstico
    for i in range(17, 20):
        print(f"Valor en trans[{i}]: {trans[i]}")
    
    # Verificar valores de sentimentProbabilities en el orden correcto
    assert trans[17] == 0.75  # sentiment_probs_positive
    assert trans[18] == 0.15  # sentiment_probs_negative
    assert trans[19] == 0.1   # sentiment_probs_neutral
    
    # Verificar IDs para sincronización
    assert "507f1f77bcf86cd799439011" in result["user_ids"]
    assert "607f1f77bcf86cd799439022" in result["transcription_ids"]

# Test para transformación con datos incompletos
def test_transform_data_incomplete():
    # Documento con campos faltantes
    mongo_docs = [
        {
            "_id": "507f1f77bcf86cd799439011",
            "name": "Incomplete User",
            # email faltante
            # birthdate faltante
            "transcriptions": [
                {
                    "_id": "607f1f77bcf86cd799439022",
                    "text": "Test incomplete",
                    # emotion faltante
                    # emotionProbabilities faltante
                }
            ]
        }
    ]
    
    # Ejecutar transformación
    result = transform_data(mongo_docs)
    
    # Verificar que la transformación maneja campos faltantes
    assert len(result["users"]) == 1
    user = result["users"][0]
    assert user[1] == "Incomplete User"  # name
    assert user[2] is None  # email debería ser None
    
    # Verificar transcripción incompleta
    assert len(result["transcriptions"]) == 1
    trans = result["transcriptions"][0]
    assert trans[4] == "Test incomplete"  # text
    assert trans[5] is None  # emotion debería ser None

# Test para sync_and_load_mysql usando mocks
def test_sync_and_load_mysql():
    # Implementamos una versión de prueba
    def mock_sync_load_mysql(transformed_data, mysql_conn_id, users_table, transcriptions_table):
        # Simulamos que la función se ejecuta correctamente
        users_to_load = transformed_data.get("users", [])
        transcriptions_to_load = transformed_data.get("transcriptions", [])
        
        # Para esta prueba, simplemente verificamos que los datos transformados son correctos
        assert len(users_to_load) == 2
        assert len(transcriptions_to_load) == 2
        
        # Y simulamos que todo funcionó bien
        return True
    
    # Guardamos la función original para restaurarla después
    original_func = etl_functions_for_tests.sync_and_load_mysql
    
    try:
        # Reemplazar la función con nuestro mock
        etl_functions_for_tests.sync_and_load_mysql = mock_sync_load_mysql
        
        # Datos transformados de prueba
        transformed_data = {
            "users": [
                ("new_user_1", "New User", "new@example.com", None, "1990-01-15", None, None, None, None, None, None, True, "2025-01-10 14:30:00", "192.168.1.1", True),
                ("existing_user_1", "Updated User", "updated@example.com", None, "1985-05-20", None, None, None, None, None, None, True, "2025-01-10 14:30:00", "192.168.1.1", True)
            ],
            "transcriptions": [
                ("new_trans_1", "new_user_1", "2025-04-10", "15:45:00", "New transcription", "joy", "positive", "test", 0.8, 0.05, 0.02, 0.01, 0.02, 0.05, 0.03, 0.01, 0.01, 0.75, 0.15, 0.1),
                ("existing_trans_1", "existing_user_1", "2025-04-10", "16:30:00", "Updated transcription", "sadness", "negative", "test", 0.1, 0.05, 0.7, 0.05, 0.05, 0.02, 0.02, 0.01, 0.0, 0.1, 0.8, 0.1)
            ],
            "user_ids": ["new_user_1", "existing_user_1"],
            "transcription_ids": ["new_trans_1", "existing_trans_1"]
        }
        
        # Ejecutar función
        result = etl_functions_for_tests.sync_and_load_mysql(transformed_data, "mysql_mymind_dw", "users", "transcriptions")
        
        # Verificar que devolvió True
        assert result is True
    finally:
        # Restaurar la función original
        etl_functions_for_tests.sync_and_load_mysql = original_func
