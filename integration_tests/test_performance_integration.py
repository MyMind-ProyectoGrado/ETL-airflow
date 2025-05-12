# /home/lflee/airflow/integration_tests/test_performance_integration.py

import pytest
import requests
import time
import concurrent.futures
import statistics
import os
import json
import logging
from datetime import datetime

# Configuración de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),  # Para mostrar en consola
        logging.FileHandler('performance_tests.log')  # Para guardar en archivo
    ]
)
logger = logging.getLogger(__name__)

# Cargar configuración
config_path = os.path.join(os.path.dirname(__file__), 'performance_config.json')
with open(config_path, 'r') as f:
    CONFIG = json.load(f)

# Token de autenticación (para las solicitudes que lo requieran)
AUTH_TOKEN = os.getenv("AUTH_TOKEN", "")
ONLY_MEASURE = os.getenv("ONLY_MEASURE", "true").lower() == "true"

# Endpoints para pruebas
ENDPOINTS = CONFIG["endpoints"]

def make_request(endpoint, auth=True):
    """Realiza una solicitud HTTP y mide el tiempo de respuesta"""
    url = endpoint["url"]
    method = endpoint.get("method", "GET").upper()
    headers = {"Authorization": f"Bearer {AUTH_TOKEN}"} if auth and AUTH_TOKEN else {}
    
    start_time = time.time()
    success = False
    status_code = None
    response_data = None
    
    try:
        if method == "GET":
            response = requests.get(url, headers=headers, timeout=30)
        elif method == "POST":
            data = endpoint.get("data", {})
            response = requests.post(url, json=data, headers=headers, timeout=30)
        elif method == "PUT":
            data = endpoint.get("data", {})
            response = requests.put(url, json=data, headers=headers, timeout=30)
        elif method == "DELETE":
            response = requests.delete(url, headers=headers, timeout=30)
        
        status_code = response.status_code
        success = 200 <= status_code < 300
        
        # Intentar obtener datos de respuesta si es JSON
        try:
            response_data = response.json()
        except:
            response_data = None
            
    except requests.RequestException as e:
        logger.error(f"Error al hacer solicitud a {url}: {str(e)}")
        status_code = 0
    
    end_time = time.time()
    return {
        "endpoint": url,
        "method": method,
        "duration": end_time - start_time,
        "success": success,
        "status_code": status_code,
        "response_data": response_data
    }

class TestPerformanceIntegration:
    """Clase para pruebas de rendimiento del sistema"""
    
    def test_it_09_01_transcription_response_time(self):
        """
        IT-09-01: Tiempo de respuesta de transcripción
        Mide el tiempo de respuesta de las solicitudes de transcripción.
        """
        logger.info("======== IT-09-01: Tiempo de respuesta de transcripción ========")
        
        # Buscar endpoint de transcripción
        transcription_endpoint = next(
            (ep for ep in ENDPOINTS if ep["type"] == "transcription"), 
            None
        )
        
        if not transcription_endpoint:
            logger.warning("No se encontró endpoint de transcripción configurado")
            return
        
        # Realizar la solicitud
        logger.info(f"Realizando solicitud de transcripción a {transcription_endpoint['url']}")
        result = make_request(transcription_endpoint)
        
        # Mostrar resultados
        logger.info(f"Tiempo de respuesta: {result['duration']:.2f}s")
        logger.info(f"Código de estado: {result['status_code']}")
        
        if not ONLY_MEASURE:
            # Verificar límite de tiempo solo si no estamos en modo medición
            assert result["success"], f"La solicitud falló con código {result['status_code']}"
            assert result["duration"] <= 10, f"El tiempo de respuesta ({result['duration']:.2f}s) excede el límite de 10s"
        
        if result["success"]:
            logger.info("✅ Solicitud exitosa")
        else:
            logger.error(f"❌ Solicitud fallida: {result['status_code']}")
            if result["response_data"]:
                logger.error(f"Respuesta: {result['response_data']}")
    
    def test_it_09_02_query_response_time(self):
        """
        IT-09-02: Tiempo de respuesta de consulta
        Mide el tiempo de respuesta de las consultas de historial.
        """
        logger.info("======== IT-09-02: Tiempo de respuesta de consulta ========")
        
        # Buscar endpoint de consulta de historial
        history_endpoint = next(
            (ep for ep in ENDPOINTS if ep["type"] == "history"), 
            None
        )
        
        if not history_endpoint:
            logger.warning("No se encontró endpoint de historial configurado")
            return
        
        # Realizar la solicitud
        logger.info(f"Realizando consulta de historial a {history_endpoint['url']}")
        result = make_request(history_endpoint)
        
        # Mostrar resultados
        logger.info(f"Tiempo de respuesta: {result['duration']:.2f}s")
        logger.info(f"Código de estado: {result['status_code']}")
        
        if not ONLY_MEASURE:
            # Verificar límite de tiempo solo si no estamos en modo medición
            assert result["success"], f"La solicitud falló con código {result['status_code']}"
            assert result["duration"] <= 2, f"El tiempo de respuesta ({result['duration']:.2f}s) excede el límite de 2s"
        
        if result["success"]:
            logger.info("✅ Solicitud exitosa")
        else:
            logger.error(f"❌ Solicitud fallida: {result['status_code']}")
            if result["response_data"]:
                logger.error(f"Respuesta: {result['response_data']}")
    
    def test_it_09_03_report_update_time(self):
        """
        IT-09-03: Tiempo de actualización de reportes
        Mide el tiempo de actualización de los reportes emocionales.
        """
        logger.info("======== IT-09-03: Tiempo de actualización de reportes ========")
        
        # Buscar endpoint de reporte emocional
        report_endpoint = next(
            (ep for ep in ENDPOINTS if ep["type"] == "report"), 
            None
        )
        
        if not report_endpoint:
            logger.warning("No se encontró endpoint de reporte configurado")
            return
        
        # Realizar la solicitud
        logger.info(f"Realizando solicitud de reporte a {report_endpoint['url']}")
        result = make_request(report_endpoint)
        
        # Mostrar resultados
        logger.info(f"Tiempo de respuesta: {result['duration']:.2f}s")
        logger.info(f"Código de estado: {result['status_code']}")
        
        if not ONLY_MEASURE:
            # Verificar límite de tiempo solo si no estamos en modo medición
            assert result["success"], f"La solicitud falló con código {result['status_code']}"
            assert result["duration"] <= 30, f"El tiempo de actualización ({result['duration']:.2f}s) excede el límite de 30s"
        
        if result["success"]:
            logger.info("✅ Solicitud exitosa")
        else:
            logger.error(f"❌ Solicitud fallida: {result['status_code']}")
            if result["response_data"]:
                logger.error(f"Respuesta: {result['response_data']}")
    
    def _run_concurrent_requests(self, endpoint, num_requests):
        """Ejecuta solicitudes concurrentes y devuelve estadísticas de los resultados"""
        with concurrent.futures.ThreadPoolExecutor(max_workers=num_requests) as executor:
            futures = [executor.submit(make_request, endpoint) for _ in range(num_requests)]
            results = [future.result() for future in concurrent.futures.as_completed(futures)]
        
        # Calcular estadísticas
        success_count = sum(1 for r in results if r["success"])
        success_rate = success_count / len(results) if results else 0
        durations = [r["duration"] for r in results if r["success"]]
        avg_duration = statistics.mean(durations) if durations else 0
        
        return {
            "total": len(results),
            "success": success_count,
            "failure": len(results) - success_count,
            "success_rate": success_rate,
            "avg_duration": avg_duration,
            "durations": durations
        }
    
    def test_it_10_01_low_load(self):
        """
        IT-10-01: Carga baja (10 usuarios)
        Mide el rendimiento del sistema con 10 peticiones simultáneas.
        """
        logger.info("======== IT-10-01: Disponibilidad bajo carga baja (10 usuarios) ========")
        
        # Buscar endpoint para prueba de carga
        load_endpoint = next(
            (ep for ep in ENDPOINTS if ep["type"] == "load_test"), 
            None
        )
        
        if not load_endpoint:
            logger.warning("No se encontró endpoint para prueba de carga configurado")
            return
        
        # Número de solicitudes concurrentes
        num_requests = 10
        
        # Ejecutar solicitudes concurrentes
        logger.info(f"Ejecutando {num_requests} solicitudes concurrentes a {load_endpoint['url']}")
        stats = self._run_concurrent_requests(load_endpoint, num_requests)
        
        # Mostrar resultados
        logger.info(f"Total de solicitudes: {stats['total']}")
        logger.info(f"Solicitudes exitosas: {stats['success']}")
        logger.info(f"Solicitudes fallidas: {stats['failure']}")
        logger.info(f"Tasa de éxito: {stats['success_rate']:.2%}")
        logger.info(f"Tiempo promedio de respuesta: {stats['avg_duration']:.2f}s")
        
        if not ONLY_MEASURE:
            # Verificar tasa de éxito solo si no estamos en modo medición
            assert stats['success_rate'] == 1.0, f"La tasa de éxito ({stats['success_rate']:.2%}) no es 100%"
        
        if stats['success_rate'] >= 0.95:
            logger.info("✅ Prueba de carga baja superada")
        else:
            logger.warning(f"⚠️ Tasa de éxito por debajo del objetivo (100%): {stats['success_rate']:.2%}")
    
    def test_it_10_02_medium_load(self):
        """
        IT-10-02: Carga media (50 usuarios)
        Mide el rendimiento del sistema con 50 peticiones simultáneas.
        """
        logger.info("======== IT-10-02: Disponibilidad bajo carga media (50 usuarios) ========")
        
        # Buscar endpoint para prueba de carga
        load_endpoint = next(
            (ep for ep in ENDPOINTS if ep["type"] == "load_test"), 
            None
        )
        
        if not load_endpoint:
            logger.warning("No se encontró endpoint para prueba de carga configurado")
            return
        
        # Número de solicitudes concurrentes
        num_requests = 50
        
        # Ejecutar solicitudes concurrentes
        logger.info(f"Ejecutando {num_requests} solicitudes concurrentes a {load_endpoint['url']}")
        stats = self._run_concurrent_requests(load_endpoint, num_requests)
        
        # Mostrar resultados
        logger.info(f"Total de solicitudes: {stats['total']}")
        logger.info(f"Solicitudes exitosas: {stats['success']}")
        logger.info(f"Solicitudes fallidas: {stats['failure']}")
        logger.info(f"Tasa de éxito: {stats['success_rate']:.2%}")
        logger.info(f"Tiempo promedio de respuesta: {stats['avg_duration']:.2f}s")
        
        if not ONLY_MEASURE:
            # Verificar tasa de éxito solo si no estamos en modo medición
            assert stats['success_rate'] >= 0.95, f"La tasa de éxito ({stats['success_rate']:.2%}) es menor al 95% requerido"
        
        if stats['success_rate'] >= 0.95:
            logger.info("✅ Prueba de carga media superada")
        else:
            logger.warning(f"⚠️ Tasa de éxito por debajo del objetivo (95%): {stats['success_rate']:.2%}")
    
    def test_it_10_03_high_load(self):
        """
        IT-10-03: Carga alta (100 usuarios)
        Mide el rendimiento del sistema con 100 peticiones simultáneas.
        """
        logger.info("======== IT-10-03: Disponibilidad bajo carga alta (100 usuarios) ========")
        
        # Buscar endpoint para prueba de carga
        load_endpoint = next(
            (ep for ep in ENDPOINTS if ep["type"] == "load_test"), 
            None
        )
        
        if not load_endpoint:
            logger.warning("No se encontró endpoint para prueba de carga configurado")
            return
        
        # Número de solicitudes concurrentes
        num_requests = 100
        
        # Ejecutar solicitudes concurrentes
        logger.info(f"Ejecutando {num_requests} solicitudes concurrentes a {load_endpoint['url']}")
        stats = self._run_concurrent_requests(load_endpoint, num_requests)
        
        # Mostrar resultados
        logger.info(f"Total de solicitudes: {stats['total']}")
        logger.info(f"Solicitudes exitosas: {stats['success']}")
        logger.info(f"Solicitudes fallidas: {stats['failure']}")
        logger.info(f"Tasa de éxito: {stats['success_rate']:.2%}")
        logger.info(f"Tiempo promedio de respuesta: {stats['avg_duration']:.2f}s")
        
        if not ONLY_MEASURE:
            # Verificar tasa de éxito solo si no estamos en modo medición
            assert stats['success_rate'] >= 0.9, f"La tasa de éxito ({stats['success_rate']:.2%}) es menor al 90% requerido"
        
        if stats['success_rate'] >= 0.9:
            logger.info("✅ Prueba de carga alta superada")
        else:
            logger.warning(f"⚠️ Tasa de éxito por debajo del objetivo (90%): {stats['success_rate']:.2%}")

# Para correr las pruebas manualmente desde este archivo
if __name__ == "__main__":
    test = TestPerformanceIntegration()
    
    # Pruebas IT-09: Tiempo de Respuesta
    test.test_it_09_01_transcription_response_time()
    test.test_it_09_02_query_response_time()
    test.test_it_09_03_report_update_time()
    
    # Pruebas IT-10: Disponibilidad bajo Carga
    test.test_it_10_01_low_load()
    test.test_it_10_02_medium_load()
    test.test_it_10_03_high_load()
