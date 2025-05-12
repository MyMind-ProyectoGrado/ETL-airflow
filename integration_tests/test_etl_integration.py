"""
Integration Tests for IT-05: ETL Process Complete

Este módulo contiene pruebas de integración que verifican que el proceso ETL extrae correctamente
datos de MongoDB y los carga en MySQL, incluyendo:
- IT-05-01: Prueba de inserción de nuevos datos
- IT-05-02: Prueba de actualización de datos existentes
- IT-05-03: Prueba de eliminación de datos
"""
import pytest
import time
import uuid
from datetime import datetime
import pymongo

def test_etl_full_process(mongo_collection, mysql_cursor, mysql_connection, airflow_dag_run):
    """
    IT-05: Prueba completa del proceso ETL.
    Esta prueba cubre inserción, actualizaciones y eliminación de datos entre MongoDB y MySQL.
    """
    # ETAPA 1: Insertar datos de prueba en MongoDB
    print("\n▶️ ETAPA 1: Probando inserción de nuevos datos (IT-05-01)")
    
    # Crear ID de usuario único para esta prueba
    test_user_id = str(uuid.uuid4())
    timestamp = datetime.now().isoformat()
    
    # Crear datos de usuario de prueba
    user_data = {
        "_id": test_user_id,
        "name": f"ETL Test User {test_user_id[:8]}",
        "email": f"etl_test_{test_user_id[:8]}@example.com",
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
        "transcriptions": []
    }
    
    # Crear dos transcripciones de prueba
    transcription1_id = str(uuid.uuid4())
    transcription2_id = str(uuid.uuid4())
    
    transcription1 = {
        "_id": transcription1_id,
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
    }
    
    transcription2 = {
        "_id": transcription2_id,
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
    
    # Agregar transcripciones al usuario
    user_data["transcriptions"] = [transcription1, transcription2]
    
    # Insertar usuario en MongoDB
    mongo_collection.insert_one(user_data)
    print(f"✅ Usuario de prueba '{user_data['name']}' con ID {test_user_id} y 2 transcripciones insertado en MongoDB")
    
    # Verificar que los datos estén en MongoDB
    mongo_user = mongo_collection.find_one({"_id": test_user_id})
    assert mongo_user is not None, "Usuario no encontrado en MongoDB"
    assert len(mongo_user.get("transcriptions", [])) == 2, "Transcripciones no encontradas en MongoDB"
    
    # Esperar un momento para asegurarse de que MongoDB haya registrado los cambios
    print("⏳ Esperando 10 segundos para que los cambios se registren en MongoDB...")
    time.sleep(10)
    
    # Ejecutar el DAG de ETL
    print("🔄 Ejecutando el DAG de ETL para procesar la inserción...")
    dag_success = airflow_dag_run(wait_time=45)  # Esperar 45 segundos para que el DAG termine
    assert dag_success, "Error al ejecutar el DAG de Airflow"
    
    # Verificar que los datos fueron transferidos a MySQL
    print("🔍 Verificando datos en MySQL...")
    mysql_cursor.execute("SELECT * FROM users WHERE user_id = %s", (test_user_id,))
    mysql_user = mysql_cursor.fetchone()
    
    # Si el usuario no se encuentra, dar información detallada del error
    if mysql_user is None:
        print(f"⚠️ ERROR: Usuario con ID {test_user_id} no encontrado en MySQL después del ETL.")
        
        # Verificar si las tablas existen
        mysql_cursor.execute("SHOW TABLES")
        tables = mysql_cursor.fetchall()
        print(f"Tablas disponibles en MySQL: {[list(t.values())[0] for t in tables]}")
        
        # Verificar si hay otros usuarios
        mysql_cursor.execute("SELECT COUNT(*) as count FROM users")
        user_count = mysql_cursor.fetchone()["count"]
        print(f"Número total de usuarios en MySQL: {user_count}")
        
        # Verificar los logs de Airflow
        print("Por favor verifica los logs de Airflow para obtener más información.")
    
    assert mysql_user is not None, "Usuario no encontrado en MySQL después del ETL"
    assert mysql_user["name"] == user_data["name"], "El nombre de usuario no coincide en MySQL"
    assert mysql_user["email"] == user_data["email"], "El email de usuario no coincide en MySQL"
    
    # Verificar que las transcripciones fueron transferidas
    mysql_cursor.execute("SELECT * FROM transcriptions WHERE user_id = %s", (test_user_id,))
    mysql_transcriptions = mysql_cursor.fetchall()
    
    assert len(mysql_transcriptions) == 2, f"Se esperaban 2 transcripciones en MySQL, se encontraron {len(mysql_transcriptions)}"
    
    # Verificar IDs específicos de transcripciones
    trans_ids = [trans["transcription_id"] for trans in mysql_transcriptions]
    assert transcription1_id in trans_ids, f"Transcripción {transcription1_id} no encontrada en MySQL"
    assert transcription2_id in trans_ids, f"Transcripción {transcription2_id} no encontrada en MySQL"
    
    # Verificar probabilidades de emociones y sentimientos
    for trans in mysql_transcriptions:
        if trans["transcription_id"] == transcription1_id:
            assert abs(trans["emotion_probs_joy"] - 0.85) < 0.001, "Probabilidad de emoción no coincide"
            assert abs(trans["sentiment_probs_positive"] - 0.90) < 0.001, "Probabilidad de sentimiento no coincide"
    
    print("✅ IT-05-01: Prueba de inserción superada - Datos transferidos correctamente de MongoDB a MySQL")
    
    # ETAPA 2: Actualizar datos de prueba en MongoDB
    print("\n▶️ ETAPA 2: Probando actualizaciones de datos existentes (IT-05-02)")
    
    # Actualizar usuario en MongoDB
    new_name = f"Updated User {datetime.now().strftime('%H%M%S')}"
    
    # Aquí hay un problema potencial - Verificamos cómo se debe hacer correctamente la actualización
    update_result = mongo_collection.update_one(
        {"_id": test_user_id},
        {"$set": {"name": new_name}}
    )
    
    print(f"🔄 Resultado de la actualización: {update_result.modified_count} documento(s) modificado(s)")
    
    # Actualizar una transcripción
    updated_text = "Este texto ha sido actualizado para la prueba de integración"
    # Para actualizar un elemento en un array, debemos usar un operador de actualización específico
    # El operador $ selecciona el primer elemento del array que coincide con la condición
    trans_update_result = mongo_collection.update_one(
        {"_id": test_user_id, "transcriptions._id": transcription1_id},
        {"$set": {"transcriptions.$.text": updated_text}}
    )
    
    print(f"🔄 Resultado de la actualización de transcripción: {trans_update_result.modified_count} documento(s) modificado(s)")
    
    print(f"✅ Nombre de usuario actualizado a '{new_name}' y texto de transcripción modificado en MongoDB")
    
    # Verificar actualización en MongoDB
    mongo_user = mongo_collection.find_one({"_id": test_user_id})
    if mongo_user["name"] != new_name:
        print(f"⚠️ ERROR: Nombre en MongoDB no actualizado. Esperado: '{new_name}', Actual: '{mongo_user['name']}'")
    assert mongo_user["name"] == new_name, "La actualización del nombre de usuario falló en MongoDB"
    
    # Verificar que la transcripción se actualizó en MongoDB
    trans_updated = False
    for trans in mongo_user.get("transcriptions", []):
        if trans["_id"] == transcription1_id and trans["text"] == updated_text:
            trans_updated = True
            break
    if not trans_updated:
        print(f"⚠️ ERROR: Texto de transcripción en MongoDB no actualizado.")
    assert trans_updated, "La actualización del texto de la transcripción falló en MongoDB"
    
    # Esperar un momento para asegurarse de que MongoDB haya registrado los cambios
    print("⏳ Esperando 10 segundos para que los cambios se registren en MongoDB...")
    time.sleep(10)
    
    # Ejecutar el DAG de ETL nuevamente
    print("🔄 Ejecutando el DAG de ETL para procesar la actualización...")
    dag_success = airflow_dag_run(wait_time=60)  # Aumentar el tiempo de espera a 60 segundos
    assert dag_success, "Error al ejecutar el DAG de Airflow para actualizaciones"
    
    # Verificar que las actualizaciones fueron transferidas a MySQL
    mysql_cursor.execute("SELECT name FROM users WHERE user_id = %s", (test_user_id,))
    updated_mysql_user = mysql_cursor.fetchone()
    
    if updated_mysql_user is None:
        print(f"⚠️ ERROR: Usuario con ID {test_user_id} no encontrado en MySQL después de la actualización.")
    else:
        # Mostrar los detalles del usuario antes de la afirmación
        print(f"📊 Datos del usuario en MySQL: {updated_mysql_user}")
        if updated_mysql_user["name"] != new_name:
            print(f"⚠️ ERROR: Nombre en MySQL no actualizado. Esperado: '{new_name}', Actual: '{updated_mysql_user['name']}'")
            
            # Verificar todos los usuarios en MySQL para ver si hay alguna coincidencia
            mysql_cursor.execute("SELECT user_id, name FROM users WHERE name LIKE %s", (f"%{new_name}%",))
            similar_users = mysql_cursor.fetchall()
            if similar_users:
                print(f"🔍 Usuarios similares encontrados en MySQL: {similar_users}")
    
    assert updated_mysql_user is not None, "Usuario no encontrado en MySQL después de la actualización"
    assert updated_mysql_user["name"] == new_name, f"Actualización del nombre de usuario no reflejada en MySQL. Esperado: {new_name}, Actual: {updated_mysql_user['name']}"
    
    # Verificar actualización de transcripción
    mysql_cursor.execute("SELECT text FROM transcriptions WHERE transcription_id = %s", (transcription1_id,))
    updated_transcription = mysql_cursor.fetchone()
    
    if updated_transcription is None:
        print(f"⚠️ ERROR: Transcripción con ID {transcription1_id} no encontrada en MySQL después de la actualización.")
    else:
        # Mostrar los detalles de la transcripción antes de la afirmación
        print(f"📊 Datos de la transcripción en MySQL: {updated_transcription}")
        if updated_transcription["text"] != updated_text:
            print(f"⚠️ ERROR: Texto en MySQL no actualizado. Esperado: '{updated_text}', Actual: '{updated_transcription['text']}'")
    
    assert updated_transcription is not None, "Transcripción no encontrada en MySQL después de la actualización"
    assert updated_transcription["text"] == updated_text, f"Actualización del texto de transcripción no reflejada en MySQL. Esperado: {updated_text}, Actual: {updated_transcription['text']}"
    
    print("✅ IT-05-02: Prueba de actualización superada - Actualizaciones propagadas correctamente de MongoDB a MySQL")
    
    # ETAPA 3: Eliminar datos de prueba de MongoDB
    print("\n▶️ ETAPA 3: Probando eliminación de datos (IT-05-03)")
    
    # Verificar que los datos existen en MySQL antes de la eliminación
    mysql_cursor.execute("SELECT COUNT(*) AS count FROM users WHERE user_id = %s", (test_user_id,))
    pre_delete_count = mysql_cursor.fetchone()["count"]
    assert pre_delete_count > 0, "Usuario no encontrado en MySQL antes de la prueba de eliminación"
    
    # Eliminar de MongoDB
    delete_result = mongo_collection.delete_one({"_id": test_user_id})
    print(f"🔄 Resultado de la eliminación: {delete_result.deleted_count} documento(s) eliminado(s)")
    
    # Verificar eliminación de MongoDB
    mongo_user = mongo_collection.find_one({"_id": test_user_id})
    assert mongo_user is None, "El usuario todavía existe en MongoDB después de la eliminación"
    
    # Esperar un momento para asegurarse de que MongoDB haya registrado los cambios
    print("⏳ Esperando 10 segundos para que los cambios se registren en MongoDB...")
    time.sleep(10)
    
    # Ejecutar el DAG por tercera vez
    print("🔄 Ejecutando el DAG de ETL para procesar la eliminación...")
    dag_success = airflow_dag_run(wait_time=60)  # Aumentar el tiempo de espera a 60 segundos
    assert dag_success, "Error al ejecutar el DAG de Airflow para eliminaciones"
    
    # Verificar que el usuario fue eliminado de MySQL
    mysql_cursor.execute("SELECT COUNT(*) AS count FROM users WHERE user_id = %s", (test_user_id,))
    post_delete_count = mysql_cursor.fetchone()["count"]
    
    if post_delete_count > 0:
        print(f"⚠️ ERROR: Usuario con ID {test_user_id} todavía existe en MySQL después de la eliminación.")
        
        # Verificar qué usuario existe
        mysql_cursor.execute("SELECT * FROM users WHERE user_id = %s", (test_user_id,))
        remaining_user = mysql_cursor.fetchone()
        print(f"📊 Usuario que sigue existiendo en MySQL: {remaining_user}")
    
    assert post_delete_count == 0, f"El usuario todavía existe en MySQL después de la eliminación (count={post_delete_count})"
    
    # Verificar que las transcripciones fueron eliminadas de MySQL
    mysql_cursor.execute("SELECT COUNT(*) AS count FROM transcriptions WHERE user_id = %s", (test_user_id,))
    trans_count = mysql_cursor.fetchone()["count"]
    
    if trans_count > 0:
        print(f"⚠️ ERROR: Transcripciones para el usuario con ID {test_user_id} todavía existen en MySQL después de la eliminación.")
        
        # Verificar qué transcripciones existen
        mysql_cursor.execute("SELECT * FROM transcriptions WHERE user_id = %s", (test_user_id,))
        remaining_trans = mysql_cursor.fetchall()
        print(f"📊 Transcripciones que siguen existiendo en MySQL: {remaining_trans}")
    
    assert trans_count == 0, f"Las transcripciones todavía existen en MySQL después de la eliminación del usuario (count={trans_count})"
    
    print("✅ IT-05-03: Prueba de eliminación superada - Eliminaciones propagadas correctamente de MongoDB a MySQL")
    
    print("\n🎉 ¡Todas las pruebas de integración IT-05 del ETL se completaron exitosamente!")
