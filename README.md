# MyMind ETL Pipeline

Un pipeline ETL robusto y escalable construido con Apache Airflow que extrae datos de MongoDB y los carga en un data warehouse MySQL con replicación master-slave para alta disponibilidad.

## 🏗️ Arquitectura

```
MongoDB (MyMind) → Apache Airflow → MySQL Master → MySQL Slave
                                      ↓
                                  Data Warehouse
```

### Componentes Principales

- **Apache Airflow**: Orquestación y programación de tareas ETL
- **MySQL Master-Slave**: Replicación para alta disponibilidad
- **MongoDB**: Base de datos fuente (MyMind users y transcriptions)
- **Docker Compose**: Containerización y gestión de servicios

## 📋 Características

- ✅ ETL automatizado cada 6 horas (configurable)
- ✅ Replicación MySQL master-slave automática
- ✅ Failover automático en caso de fallo del master
- ✅ Sincronización bidireccional de datos
- ✅ Monitoreo y logging detallado
- ✅ Manejo de tipos BSON (ObjectId, DateTime)
- ✅ Vista `study_data` para análisis de investigación
- ✅ Pruebas de integración automatizadas

## 🚀 Inicio Rápido

### Prerrequisitos

- Docker y Docker Compose
- Python 3.8+
- Acceso a MongoDB (MyMind)

### Instalación

1. **Clonar el repositorio**
```bash
git clone <repository-url>
cd airflow-etl-pipeline
```

2. **Configurar variables de entorno**
```bash
# Crear archivo .env
echo "AIRFLOW_UID=$(id -u)" > .env
echo "MYSQL_ROOT_PASSWORD=rootpassword" >> .env
echo "MYSQL_DATABASE=mymind_dw" >> .env
echo "MYSQL_USER=airflow_user" >> .env
echo "MYSQL_PASSWORD=airflow_pass" >> .env
```

3. **Levantar los servicios**
```bash
docker-compose up -d
```

4. **Configurar replicación MySQL**
```bash
./mysql/setup-replication.sh
```

5. **Acceder a Airflow UI**
- URL: http://localhost:8080
- Usuario: `airflow`
- Contraseña: `airflow`

## 🔧 Configuración

### Conexiones de Airflow

Una vez en la UI de Airflow, configurar las siguientes conexiones:

#### Conexión MongoDB (`mongo_mymind`)
- **Conn Type**: Generic
- **Host**: `<mongodb-host>`
- **Login**: `<mongodb-user>`
- **Password**: `<mongodb-password>`
- **Extra**: 
```json
{
  "srv": true,
  "connectTimeoutMS": 10000,
  "serverSelectionTimeoutMS": 30000
}
```

#### Conexión MySQL (`mysql_mymind_dw`)
- **Conn Type**: MySQL
- **Host**: `mysql_mymind_master`
- **Login**: `airflow_user`
- **Password**: `airflow_pass`
- **Schema**: `mymind_dw`
- **Port**: `3306`

### Programación del DAG

El DAG se ejecuta automáticamente cada 6 horas. Para modificar la frecuencia:

```python
# En dags/mymind_etl_dag.py
schedule="0 0,6,12,18 * * *"  # Cada 6 horas
# schedule="0 * * * *"         # Cada hora
# schedule="*/30 * * * *"      # Cada 30 minutos
```

## 📊 Estructura de Datos

### Tabla `users`
- `user_id` (VARCHAR, PK)
- `name`, `email`, `profile_pic`
- `birthdate`, `city`, `personality`
- `university`, `degree`, `gender`
- `notifications`, `accept_policies`
- `acceptance_date`, `acceptance_ip`
- `allow_anonimized_usage`

### Tabla `transcriptions`
- `transcription_id` (VARCHAR, PK)
- `user_id` (FK a users)
- `transcription_date`, `transcription_time`
- `text`, `emotion`, `sentiment`, `topic`
- Probabilidades de emociones: `emotion_probs_*`
- Probabilidades de sentimiento: `sentiment_probs_*`

### Vista `study_data`
Vista optimizada para análisis de investigación que incluye:
- Transcripciones con análisis emocional
- Datos demográficos anonimizados
- Solo usuarios que aceptaron políticas

## 🔄 Alta Disponibilidad

### Replicación Master-Slave

El sistema incluye replicación automática:

```bash
# Monitorear estado de replicación
./mysql/monitor.sh

# Sincronización manual completa
./mysql/sync-databases.sh
```

### Failover Automático

En caso de fallo del master, el sistema:

1. Detecta la caída del master
2. Promueve el slave a master
3. Actualiza automáticamente las conexiones de Airflow
4. Envía notificaciones al administrador

```bash
# Ejecutar failover manual
./mysql/failover.sh
```

## 🧪 Pruebas

### Pruebas de Integración

```bash
# Ejecutar todas las pruebas
python integration_tests/test_failover.py

# Revisar logs de pruebas
tail -f failover_tests.log
```

Las pruebas incluyen:
- IT-07-01: Verificación de replicación master-slave
- IT-07-02: Simulación de fallo y failover
- IT-07-03: Continuidad de operaciones post-failover
- IT-08-01: Ejecución ETL después del failover
- IT-08-02: Actualización de conexiones Airflow

## 📈 Monitoreo

### Servicios Disponibles

- **Airflow UI**: http://localhost:8080
- **MySQL Master**: localhost:3307
- **MySQL Slave**: localhost:3308
- **Flower (Celery)**: http://localhost:5555 (con `--profile flower`)

### Logs Importantes

```bash
# Logs de Airflow
docker-compose logs airflow-scheduler
docker-compose logs airflow-worker

# Logs de MySQL
docker-compose logs mysql_mymind
docker-compose logs mysql_mymind_slave

# Logs del DAG ETL
# Disponibles en Airflow UI > DAGs > mymind_mongo_to_mysql_etl > Logs
```

## 🛠️ Mantenimiento

### Comandos Útiles

```bash
# Reiniciar todos los servicios
docker-compose restart

# Ver estado de contenedores
docker-compose ps

# Limpiar volúmenes (¡CUIDADO: Elimina datos!)
docker-compose down -v

# Acceder a MySQL master
docker exec -it mysql_mymind_master mysql -uroot -p

# Ejecutar DAG manualmente
docker exec -it <airflow-container> airflow dags trigger mymind_mongo_to_mysql_etl
```

### Backup de Datos

```bash
# Backup completo de MySQL
docker exec mysql_mymind_master mysqldump -uroot -prootpassword --all-databases > backup_$(date +%Y%m%d).sql

# Restaurar desde backup
cat backup_20240501.sql | docker exec -i mysql_mymind_master mysql -uroot -prootpassword
```

## 🔍 Troubleshooting

### Problemas Comunes

**Error de conexión a MongoDB**
```bash
# Verificar conectividad
docker exec airflow-airflow-worker-1 python -c "from pymongo import MongoClient; print(MongoClient('mongodb://...').admin.command('ping'))"
```

**Replicación MySQL no funciona**
```bash
# Verificar estado de replicación
./mysql/monitor.sh

# Reconfigurar replicación
./mysql/setup-replication.sh
```

**DAG no se ejecuta**
```bash
# Verificar que el DAG esté activado en la UI
# Revisar logs del scheduler
docker-compose logs airflow-scheduler
```

### Contacto y Soporte

Para problemas o preguntas:
- Revisar logs detallados en Airflow UI
- Consultar documentación de troubleshooting
- Verificar configuración de conexiones

## 📄 Licencia

Este proyecto está bajo la Licencia Apache 2.0. Ver archivo `LICENSE` para más detalles.

---

**Nota**: Este sistema maneja datos sensibles de usuarios. Asegúrate de cumplir con las regulaciones de privacidad y protección de datos aplicables (GDPR, CCPA, etc.).
