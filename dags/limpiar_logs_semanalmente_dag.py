from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta
import os
import shutil

# Definir argumentos por defecto
default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
    'start_date': datetime(2025, 5, 8),
}

# Definir DAG
dag = DAG(
    'limpiar_logs_semanalmente',
    default_args=default_args,
    description='DAG para limpiar logs semanalmente',
    schedule_interval='0 0 * * 0',  # Ejecutar cada domingo a medianoche
    catchup=False,
)

# Función para limpiar logs específicos de tu DAG de transferencia
def limpiar_logs_especificos():
    # Ruta donde Airflow guarda los logs
    log_dir = '/opt/airflow/logs/dag_id_de_tu_transferencia'
    
    # Verificar si el directorio existe
    if os.path.exists(log_dir):
        # Eliminar logs más antiguos que X días
        current_time = datetime.now()
        retention_days = 7  # Retener logs de la última semana
        
        for root, dirs, files in os.walk(log_dir):
            for file in files:
                if file.endswith('.log'):
                    file_path = os.path.join(root, file)
                    file_time = datetime.fromtimestamp(os.path.getmtime(file_path))
                    if (current_time - file_time).days > retention_days:
                        os.remove(file_path)
                        print(f"Eliminado: {file_path}")

# Tarea para limpiar los logs específicos
limpiar_logs_task = PythonOperator(
    task_id='limpiar_logs_especificos',
    python_callable=limpiar_logs_especificos,
    dag=dag,
)

# Tarea para limpiar logs generales de Airflow (opcional)
limpiar_logs_airflow = BashOperator(
    task_id='limpiar_logs_airflow',
    bash_command='airflow db clean --clean-before-timestamp "$(date -d "7 days ago" +%Y-%m-%d)" --yes',
    dag=dag,
)

# Definir el orden de las tareas
limpiar_logs_task >> limpiar_logs_airflow
