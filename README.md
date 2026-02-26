Real Estate Management System 🏢
Sistema Integral de Gestión Inmobiliaria y Automatización Financiera
📋 Descripción
Este sistema fue diseñado para optimizar las operaciones de gestión de propiedades y el seguimiento financiero en el sector inmobiliario. Combina un robusto backend en Python/Flask con herramientas de automatización para la generación de reportes y reconciliación de datos impositivos.

🛠️ Características Técnicas
El proyecto implementa estándares de desarrollo profesional y de seguridad:

Arquitectura Modular: Uso de Flask Blueprints para una organización de código escalable y mantenible.

Seguridad Avanzada: Implementación de protección contra ataques CSRF y validación de datos en formularios.

Sistema de Auditoría: Registro automático de acciones de usuario para trazabilidad total de los cambios en el sistema.

Integridad de Datos: Uso de Soft Deletes para evitar la pérdida accidental de información crítica.

Automatización con Python: Scripts integrados para:

Generación de reportes financieros automáticos a partir de archivos Excel.

Reconciliación de deudas de impuestos inmobiliarios mediante comparación de datasets.

Automatización de carga de formularios de retención para el sistema Tesakã.

🗄️ Tecnologías Utilizadas
Backend: Python 3 (Flask).

Base de Datos: Soporte para Oracle (entorno de producción) y SQLite (desarrollo).

Frontend: HTML5, CSS3, JavaScript y Jinja2 Templates.

Gestión de Migraciones: Flask-Migrate para el control de versiones del esquema de base de datos.

🚀 Instalación y Configuración
1. Clonar el repositorio:

git clone https://github.com/DariusK1ngg/Real-Estate-Management-System.git
cd Real-Estate-Management-System

2. Crear y activar un entorno virtual:
python -m venv venv
source venv/bin/activate  # En Windows: venv\Scripts\activate

3. Instalar dependencias:
pip install -r requirements.txt

4. Configurar variables de entorno:
Crea un archivo .env en la raíz con tus credenciales (asegúrate de no subirlas a GitHub).

5. Ejecutar migraciones:
flask db upgrade

6. Iniciar el servidor:
python app.py

📄 Licencia
Este proyecto está bajo la Licencia Dario Avalos.
