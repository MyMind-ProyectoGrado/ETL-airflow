import pytest
import time
from datetime import datetime
import os

def test_etl_with_insertions(mongo_collection, mysql_cursor, insert_test_data, airflow_dag_run):
    """IT-05-01: Verificar que el ETL inserte correctamente nuevos datos."""
    
    # Obtener IDs de los datos de prueba
    user_id, transcription_ids = insert_test_data
    
    # Verificar que los datos existen en MongoDB
    mongo_user = mongo_collection.find_one({"_id": user_id})
    assert mongo_user is not None, "Usuario no encontrado en MongoDB"
    assert len(mongo_user["transcriptions"]) == 2, "Transcripciones no encontradas en MongoDB"
    
    print(f"✅ Datos insertados en MongoDB: Usuario {user_id}, 2 transcripciones")
    
    # Ejecutar el DAG de ETL (ya hecho en el fixture airflow_dag_run)
    assert airflow_dag_run, "Error al ejecutar el DAG de ETL"
    
    # Verificar que los datos se hayan insertado en MySQL
    # 1. Verificar usuario
    mysql_cursor.execute("SELECT * FROM users WHERE user_id = %s", (user_id,))
    mysql_user = mysql_cursor.fetchone()
    assert mysql_user is not None, "Usuario no encontrado en MySQL después del ETL"
    assert mysql_user["name"] == mongo_user["name"], "Nombre de usuario no coincide en MySQL"
    assert mysql_user["email"] == mongo_user["email"], "Email de usuario no coincide en MySQL"
    
    print(f"✅ Usuario insertado correctamente en MySQL: {mysql_user['name']}")
    
    # 2. Verificar transcripciones
    for trans_id in transcription_ids:
        mysql_cursor.execute("SELECT * FROM transcriptions WHERE transcription_id = %s", (trans_id,))
        mysql_trans = mysql_cursor.fetchone()
        assert mysql_trans is not None, f"Transcripción {trans_id} no encontrada en MySQL después del ETL"
        assert mysql_trans["user_id"] == user_id, "ID de usuario no coincide en transcripción"
    
    print(f"✅ Transcripciones insertadas correctamente en MySQL")
    print(f"✅ IT-05-01: ETL con inserciones verificado correctamente")

def test_etl_with_updates(mongo_collection, mysql_cursor, insert_test_data, airflow_dag_run):
    """IT-05-02: Verificar que el ETL actualice correctamente datos modificados."""
    
    # Obtener IDs de los datos de prueba
    user_id, transcription_ids = insert_test_data
    
    # Modificar datos en MongoDB
    new_name = f"Updated User {datetime.now().strftime('%H%M%S')}"
    mongo_collection.update_one(
        {"_id": user_id},
        {"$set": {"name": new_name}}
    )
    
    # Verificar que la actualización se hizo en MongoDB
    mongo_user = mongo_collection.find_one({"_id": user_id})
    assert mongo_user["name"] == new_name, "Actualización en MongoDB falló"
    
    print(f"✅ Datos actualizados en MongoDB: Usuario {user_id}, nuevo nombre: {new_name}")
    
    # Ejecutar el DAG de ETL
    assert airflow_dag_run, "Error al ejecutar el DAG de ETL"
    
    # Verificar que los datos se hayan actualizado en MySQL
    mysql_cursor.execute("SELECT * FROM users WHERE user_id = %s", (user_id,))
    mysql_user = mysql_cursor.fetchone()
    assert mysql_user is not None, "Usuario no encontrado en MySQL después del ETL"
    assert mysql_user["name"] == new_name, "Nombre actualizado no coincide en MySQL"
    
    print(f"✅ Usuario actualizado correctamente en MySQL: {mysql_user['name']}")
    print(f"✅ IT-05-02: ETL con actualizaciones verificado correctamente")

def test_etl_with_deletions(mongo_collection, mysql_cursor, mysql_connection, insert_test_data, airflow_dag_run):
    """IT-05-03: Verificar que el ETL elimine correctamente datos borrados de MongoDB."""
    
    # Obtener IDs de los datos de prueba
    user_id, transcription_ids = insert_test_data
    
    # Verificar que existen en MySQL antes de eliminar
    mysql_cursor.execute("SELECT COUNT(*) as count FROM users WHERE user_id = %s", (user_id,))
    result = mysql_cursor.fetchone()
    assert result["count"] > 0, "Usuario no existe en MySQL antes de la eliminación"
    
    # Eliminar de MongoDB
    mongo_collection.delete_one({"_id": user_id})
    
    # Verificar que se eliminó de MongoDB
    mongo_user = mongo_collection.find_one({"_id": user_id})
    assert mongo_user is None, "Usuario no se eliminó correctamente de MongoDB"
    
    print(f"✅ Usuario {user_id} eliminado de MongoDB")
    
    # Ejecutar el DAG de ETL
    assert airflow_dag_run, "Error al ejecutar el DAG de ETL"
    
    # Verificar que se eliminó de MySQL
    mysql_cursor.execute("SELECT COUNT(*) as count FROM users WHERE user_id = %s", (user_id,))
    result = mysql_cursor.fetchone()
    
    # También verificar que se eliminaron las transcripciones asociadas
    all_trans_deleted = True
    for trans_id in transcription_ids:
        mysql_cursor.execute("SELECT COUNT(*) as count FROM transcriptions WHERE transcription_id = %s", (trans_id,))
        trans_result = mysql_cursor.fetchone()
        if trans_result["count"] > 0:
            all_trans_deleted = False
            break
    
    assert result["count"] == 0, f"Usuario no se eliminó de MySQL después del ETL: {result}"
    assert all_trans_deleted, "No se eliminaron todas las transcripciones asociadas"
    
    print(f"✅ Usuario y transcripciones eliminados correctamente de MySQL")
    print(f"✅ IT-05-03: ETL con eliminaciones verificado correctamente")
