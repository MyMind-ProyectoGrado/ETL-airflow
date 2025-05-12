#!/bin/bash
# run_etl_integration_test.sh - Ejecuta las pruebas de integración ETL

# Activar el entorno virtual
if [ -d "/home/lflee/pytest-env" ]; then
    source /home/lflee/pytest-env/bin/activate
else
    echo "Entorno virtual no encontrado. Creando uno nuevo..."
    python -m venv /home/lflee/pytest-env
    source /home/lflee/pytest-env/bin/activate
    pip install -U pip
    pip install pytest pymongo pymysql python-dotenv pytest-cov
fi

# Asegurar que la conexión entre Airflow y MySQL está configurada correctamente
echo "🔧 Configurando permisos de MySQL para Airflow..."
docker exec mysql_mymind_master mysql -uroot -prootpassword -e "
CREATE USER IF NOT EXISTS 'airflow_user'@'%' IDENTIFIED BY 'airflow_pass';
GRANT ALL PRIVILEGES ON mymind_dw.* TO 'airflow_user'@'%';
FLUSH PRIVILEGES;
"

echo "🔍 Verificando permisos de usuario MySQL..."
docker exec mysql_mymind_master mysql -uroot -prootpassword -e "
SELECT user, host FROM mysql.user WHERE user = 'airflow_user';
"

# Verificar tablas en MySQL
echo "🔍 Verificando tablas en MySQL..."
docker exec mysql_mymind_master mysql -uairflow_user -pairflow_pass -e "SHOW TABLES;" mymind_dw

# Verificar que podemos acceder directamente a la base de datos MySQL desde nuestro sistema
echo "🔍 Probando conexión directa a MySQL desde el host..."
mysql -h localhost -P 3307 -u airflow_user -p'airflow_pass' -e "SHOW TABLES;" mymind_dw || echo "⚠️ No se pudo conectar directamente a MySQL desde el host"

# Buscar todos los contenedores de Airflow
echo "🔍 Buscando contenedores de Airflow..."
docker ps | grep airflow

# Actualizar la conexión en Airflow
echo "🔧 Actualizando conexión a MySQL en Airflow..."
# Obtener el ID del contenedor de Airflow webserver
airflow_container=$(docker ps | grep airflow | grep webserver | awk '{print $1}')
if [ -z "$airflow_container" ]; then
    echo "⚠️ No se encontró el contenedor de Airflow webserver"
else
    echo "✅ Contenedor de Airflow webserver encontrado: $airflow_container"
    
    # Eliminar y volver a crear la conexión
    docker exec $airflow_container airflow connections delete mysql_mymind_dw
    docker exec $airflow_container airflow connections add mysql_mymind_dw \
        --conn-type mysql \
        --conn-login airflow_user \
        --conn-password airflow_pass \
        --conn-host mysql_mymind_master \
        --conn-port 3306 \
        --conn-schema mymind_dw
    
    echo "✅ Conexión a MySQL actualizada en Airflow"
fi

# Ejecutar pruebas con formato detallado y sacar todo el detalle posible
echo "==== Ejecutando pruebas de integración ETL (IT-05) ===="
python -m pytest test_etl_integration.py -v --no-header --tb=native

# Mostrar un resumen
echo "==== Ejecución de pruebas completada ===="
