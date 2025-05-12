#!/bin/bash
# /home/lflee/airflow/integration_tests/run_performance_tests.sh

# Variables de entorno
# Deja esto vacío para que lo completes tú
export AUTH_TOKEN="eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCIsImtpZCI6Ildwa1htLUROUGppOFRMb0FNVWpGSSJ9.eyJpc3MiOiJodHRwczovL215LW1pbmQudXMuYXV0aDAuY29tLyIsInN1YiI6ImF1dGgwfDY3ZWM2OGM3NDAwMGFjZDQ5YjliZmVjNyIsImF1ZCI6WyJodHRwczovL2NsaWVudGNyZWRlbnRpYWxzLmNvbSIsImh0dHBzOi8vbXktbWluZC51cy5hdXRoMC5jb20vdXNlcmluZm8iXSwiaWF0IjoxNzQ2NzEyNzY1LCJleHAiOjE3NDgwMDg3NjUsInNjb3BlIjoib3BlbmlkIHByb2ZpbGUgZW1haWwgYWRkcmVzcyBwaG9uZSIsImd0eSI6InBhc3N3b3JkIiwiYXpwIjoiNDZ1dk9abjM2SmpkMkxNcHlIczhFQVpTV0RxMnh2bFMifQ.Y4zuQgZ2U28DiiHsjv33l9w2zZJYz1fcWB5wxscm32oU0Ja4CBS_2RJKC3Cy8GTAyD4ffi4neiwQsqq3ATuve1rJgHV1ARPKNJ1z_sVej35dXzDz10WjYLt45iE7lpbUd5VKtPwy39PPZ8TVcnGnVUMxsckwFDdmdgRudljvgGf26Nmjv0P5Tzx2iNj1kNgyvhfoL2BznX7JVklsOUwTXhmpzKIOloYhS6zL6Vxsb3ESQxn44nWExtlcMrZ1gVrXnJHJ969ivGj5cZikl7F13pZimpUpXOwHbUQs3e2n0zDGPQUXOopaIqyOt4Ur98K2ieiWr5Wg4slJnmkzc2ItAg"
# Modo de solo medición (sin validar tiempos límite)
export ONLY_MEASURE="true"

PYTHON_ENV="/home/lflee/pytest-env/bin/python"
TEST_DIR="/home/lflee/airflow/integration_tests"

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

# Verificar entorno y dependencias
print_header "Verificando entorno"

# Activar entorno virtual si existe
if [ -d "/home/lflee/pytest-env" ]; then
    source /home/lflee/pytest-env/bin/activate
    print_success "Entorno virtual activado"
else
    print_warning "Entorno virtual no encontrado. Creando uno nuevo..."
    python -m venv /home/lflee/pytest-env
    source /home/lflee/pytest-env/bin/activate
    pip install -U pip
    print_success "Entorno virtual creado y activado"
fi

# Instalar dependencias si no existen
pip list | grep requests > /dev/null
if [ $? -ne 0 ]; then
    print_info "Instalando dependencias..."
    pip install pytest requests statistics
fi

# Verificar que los servicios estén corriendo
print_header "Verificando servicios"

# Verificar APISIX
curl -s -o /dev/null -w '%{http_code}' http://localhost:9080 > /dev/null
if [ $? -eq 0 ]; then
    print_success "APISIX está corriendo"
else
    print_error "APISIX no está disponible. Asegúrate de que esté corriendo"
    exit 1
fi

# Verificar backend users
curl -s -o /dev/null -w '%{http_code}' http://localhost:8000/metrics > /dev/null
if [ $? -eq 0 ]; then
    print_success "Servicio de usuarios está corriendo"
else
    print_warning "Servicio de usuarios no parece estar disponible directamente (puede estar solo en Docker)"
fi

# Verificar backend models
curl -s -o /dev/null -w '%{http_code}' http://localhost:8001/metrics > /dev/null
if [ $? -eq 0 ]; then
    print_success "Servicio de modelos está corriendo"
else
    print_warning "Servicio de modelos no parece estar disponible directamente (puede estar solo en Docker)"
fi

# Verificar backend visualizations
curl -s -o /dev/null -w '%{http_code}' http://localhost:8002/metrics > /dev/null
if [ $? -eq 0 ]; then
    print_success "Servicio de visualizaciones está corriendo"
else
    print_warning "Servicio de visualizaciones no parece estar disponible directamente (puede estar solo en Docker)"
fi

# Verificar token
if [ -z "$AUTH_TOKEN" ]; then
    print_warning "No se ha configurado un token de autenticación. Las pruebas pueden fallar si los endpoints requieren autenticación."
    read -p "¿Deseas continuar de todos modos? (s/n): " confirm
    if [ "$confirm" != "s" ] && [ "$confirm" != "S" ]; then
        print_info "Pruebas canceladas. Configura el token en este script y vuelve a intentarlo."
        exit 0
    fi
fi

# Ejecutar pruebas
print_header "Ejecutando pruebas de rendimiento"

# Ejecutar las pruebas con Python directamente
cd "${TEST_DIR}"
python test_performance_integration.py

# Informar sobre resultados
print_info "Consulta el archivo performance_tests.log para ver los resultados detallados"
print_header "Pruebas completadas"
print_info "Las pruebas se ejecutaron en modo MEDICIÓN. Para validar contra límites de tiempo, cambia ONLY_MEASURE a 'false' en el script."
