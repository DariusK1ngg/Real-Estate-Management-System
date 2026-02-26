# 🏢 Real Estate Management System
> **Sistema Integral de Gestión Inmobiliaria y Automatización de Procesos Financieros.**

Este proyecto representa una solución robusta para la administración de propiedades, integrando seguridad avanzada, auditoría de datos y herramientas de automatización para optimizar la operativa diaria en el sector inmobiliario.

---

## 🚀 Características Principales

| Módulo | Descripción |
| :--- | :--- |
| **🛡️ Seguridad** | Protección contra ataques **CSRF** y validación estricta de formularios. |
| **📑 Auditoría** | Registro histórico de acciones (Logs) para trazabilidad total de cambios. |
| **🗑️ Integridad** | Implementación de **Soft Deletes** (eliminación lógica) para evitar pérdida de datos críticos. |
| **🤖 Automatización** | Scripts para reportes financieros en Excel y carga masiva en el sistema **Tesakã**. |
| **🏗️ Arquitectura** | Estructura modular basada en **Flask Blueprints** para alta escalabilidad. |

---

## 🛠️ Stack Tecnológico

* **Lenguaje:** [Python 3.9+](https://www.python.org/)
* **Framework Web:** [Flask](https://flask.palletsprojects.com/)
* **Bases de Datos:** * **Producción:** Oracle Database
    * **Desarrollo:** SQLite
* **Herramientas de Datos:** Pandas / Openpyxl (para automatización de Excel)
* **Frontend:** Jinja2, HTML5, CSS3, JavaScript

---

## 📊 Capacidades de Automatización
Como parte de la optimización del flujo de trabajo, el sistema incluye herramientas especializadas:

1.  **Reconciliación de Impuestos:** Comparación automática de datasets para identificar clientes con pagos pendientes.
2.  **Reportes de Propietarios:** Generación dinámica de estados financieros a partir de archivos Excel.
3.  **Integración Tesakã:** Script de automatización para la entrada de datos en formularios de retención impositiva.

---

## ⚙️ Instalación Rápida

1. **Clonar el repositorio:**
   ```bash
   git clone [https://github.com/DariusK1ngg/Real-Estate-Management-System.git](https://github.com/DariusK1ngg/Real-Estate-Management-System.git)
   cd Real-Estate-Management-System
2. **Configurar el entorno:**
   ```bash
    python -m venv venv
    source venv/bin/activate  # En Windows: venv\Scripts\activate
    pip install -r requirements.txt
3. **Base de Datos y Ejecución:**
   ```bash
   flask db upgrade
   python app.py


## By - Dario Avalos :)
