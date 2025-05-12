#!/bin/bash
# run_failover_tests.sh - Script mejorado para ejecutar pruebas de failover

# Colores para los mensajes
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Función para imprimir mensajes con formato
print_header() {
    echo -e "\n${BLUE}##################################################${NC}"
    echo -e "${BLUE}# $1${NC}"
    echo -e "${BLUE}##################################################${NC}\n"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ $1${NC}"
}

# Configurar entorno
print_header "Configurando entorno de prueba"

# Activar entorno virtual
if [ -d "/home/lflee/pytest-env" ]; then
    source /home/lflee/pytest-env/bin/activate
    print_success "Entorno virtual activado"
else
    print_warning "Entorno virtual no encontrado. Creando uno nuevo..."
    python -m venv /home/lflee/pytest-env
    source /home/lflee/pytest-env/bin/activate
    pip install -U pip
    pip install pymysql python-dotenv pytest
    print_success "Entorno virtual creado y activado"
fi

# Verificar archivos necesarios
print_info "Verificando archivos necesarios..."
FAILOVER_SCRIPT="/home/lflee/airflow/mysql/failover.sh"
SETUP_SCRIPT="/home/lflee/airflow/mysql/setup-replication.sh"
TEST_FILE="/home/lflee/airflow/integration_tests/test_failover_integration.py"

if [ ! -f "$FAILOVER_SCRIPT" ]; then
    print_error "Script de failover no encontrado: $FAILOVER_SCRIPT"
    exit 1
else
    print_success "Script de failover encontrado: $FAILOVER_SCRIPT"
    chmod +x "$FAILOVER_SCRIPT"
fi

if [ ! -f "$SETUP_SCRIPT" ]; then
    print_error "Script de setup-replication no encontrado: $SETUP_SCRIPT"
    exit 1
else
    print_success "Script de setup-replication encontrado: $SETUP_SCRIPT"
    chmod +x "$SETUP_SCRIPT"
fi

if [ ! -f "$TEST_FILE" ]; then
    print_error "Archivo de prueba no encontrado: $TEST_FILE"
    exit 1
else
    print_success "Archivo de prueba encontrado: $TEST_FILE"
fi

# Comprobar contenedores
print_header "Verificando servicios MySQL"
print_info "Verificando contenedores MySQL..."
docker ps | grep mysql_mymind

# Verificar replicación
print_info "Verificando estado de replicación..."
REPLICATION=$(docker exec mysql_mymind_slave mysql -uroot -prootpassword -e "SHOW SLAVE STATUS\G" | grep -E "Slave_IO_Running:|Slave_SQL_Running:")
echo "$REPLICATION"

IO_RUNNING=$(echo "$REPLICATION" | grep "Slave_IO_Running:" | grep -c "Yes")
SQL_RUNNING=$(echo "$REPLICATION" | grep "Slave_SQL_Running:" | grep -c "Yes")

if [ "$IO_RUNNING" -eq 1 ] && [ "$SQL_RUNNING" -eq 1 ]; then
    print_success "Replicación funcionando correctamente"
else
    print_warning "Replicación no está activa. Intentando configurar..."
    bash "$SETUP_SCRIPT"
    sleep 5
    
    # Verificar nuevamente
    REPLICATION=$(docker exec mysql_mymind_slave mysql -uroot -prootpassword -e "SHOW SLAVE STATUS\G" | grep -E "Slave_IO_Running:|Slave_SQL_Running:")
    IO_RUNNING=$(echo "$REPLICATION" | grep "Slave_IO_Running:" | grep -c "Yes")
    SQL_RUNNING=$(echo "$REPLICATION" | grep "Slave_SQL_Running:" | grep -c "Yes")
    
    if [ "$IO_RUNNING" -eq 1 ] && [ "$SQL_RUNNING" -eq 1 ]; then
        print_success "Replicación configurada correctamente"
    else
        print_error "No se pudo configurar la replicación. Las pruebas pueden fallar."
    fi
fi

# Ejecutar pruebas
print_header "Ejecutando pruebas de integración"

if [ "$1" = "--sequential" ]; then
    print_info "Ejecutando pruebas de forma secuencial:"
    
    print_header "IT-07-01: Replicación master-slave"
    python "$TEST_FILE" replication
    
    print_header "IT-07-02: Simulación de fallo en master"
    python "$TEST_FILE" failover
    
    print_header "IT-07-03: Continuidad de operaciones"
    python "$TEST_FILE" continuity
    
    print_header "IT-08-01: ETL post-failover"
    python "$TEST_FILE" etl
    
    print_header "IT-08-02: Actualización de conexión Airflow"
    python "$TEST_FILE" connection
else
    print_info "Ejecutando todas las pruebas juntas:"
    python "$TEST_FILE" all
fi

# Restaurar entorno
print_header "Restaurando entorno"
print_info "Restaurando replicación..."
bash "$SETUP_SCRIPT"

print_success "Pruebas completadas"
