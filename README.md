# 🏢 Real Estate Management System
> **Sistema Profesional de Gestión Inmobiliaria con Arquitectura Modular y Automatización.**

Este sistema ha sido desarrollado para digitalizar y optimizar las operaciones de una inmobiliaria, cubriendo desde la gestión de contratos y ventas hasta la automatización de reportes impositivos y auditoría interna.

---

## 🚀 Módulos del Sistema

El proyecto está organizado en módulos independientes (**Blueprints**) para facilitar su mantenimiento y escalabilidad:

| Módulo | Funcionalidades Clave |
| :--- | :--- |
| **💰 Ventas** | Gestión de facturación, definición de clientes y reportes de ventas. |
| **🏦 Tesorería** | Control de movimientos de caja, bancos y conciliación financiera. |
| **📋 Inventario** | Administración de inmuebles, fraccionamientos y control de contratos. |
| **👥 RRHH** | Gestión de funcionarios, cargos y definiciones de personal. |
| **💸 Gastos & Cobros** | Seguimiento detallado de egresos operativos y flujo de ingresos. |
| **🛡️ Auditoría** | Sistema de logs en tiempo real para rastrear cada acción realizada en el sistema. |

---

## 🛠️ Stack Tecnológico

* **Backend:** [Python 3.11+](https://www.python.org/) con **Flask Framework**.
* **Base de Datos:** Configuración dual para **Oracle SQL** (Producción) y **SQLite** (Desarrollo).
* **ORM:** SQLAlchemy con Flask-Migrate para control de versiones de la base de datos.
* **Frontend:** Interfaz dinámica con Jinja2, JavaScript moderno, HTML5 y CSS3.
* **Seguridad:** Implementación de CSRF Protection y gestión de sesiones con Flask-Login.

---

## ✨ Características Técnicas Avanzadas

* **Arquitectura Modular:** Uso de Blueprints para separar la lógica de negocios por departamentos (Ventas, RRHH, etc.).
* **Sistema de Auditoría:** Registro automático de operaciones en la tabla `AuditLog` para cumplimiento y seguridad.
* **Gestión de Errores:** Páginas personalizadas para errores 404 y 500 integradas en el flujo de usuario.
* **Soft Deletes:** Implementación de borrado lógico para preservar la integridad histórica de los datos.
* **Automatización de Reportes:** Generación de archivos listos para liquidación de propietarios y listados de precios.

---

## ⚙️ Instalación y Despliegue

1. **Clonar el repositorio:**
   ```bash
   git clone [https://github.com/DariusK1ngg/Real-Estate-Management-System.git](https://github.com/DariusK1ngg/Real-Estate-Management-System.git)
   cd Real-Estate-Management-System
Configurar el entorno virtual:

Bash
python -m venv venv
source venv/bin/activate  # En Windows: venv\Scripts\activate
Instalar dependencias:

Bash
pip install -r requirements.txt
Variables de Entorno:
Configura tu archivo .env basándote en los requerimientos del sistema para conectar con Oracle o SQLite.

Migrar Base de Datos e Iniciar:

Bash
flask db upgrade
python app.py
📂 Estructura del Proyecto
Plaintext
├── routes/           # Lógica de cada módulo (Ventas, RRHH, etc.)
├── templates/        # Vistas organizadas por carpetas de módulo
├── static/           # Archivos CSS y JS específicos por funcionalidad
├── models.py         # Definición de modelos de base de datos
├── extensions.py     # Configuración de extensiones (DB, Login, CSRF)
└── utils.py          # Funciones auxiliares y decoradores
👨‍💻 Perfil del Desarrollador
Dario - Estudiante de 3er año de Ingeniería Informática.

Institución: Universidad Católica "Nuestra Señora de la Asunción".

Especialización: Desarrollo de Software, Ciberseguridad y Automatización con Python.

✨ Proyecto desarrollado con enfoque en la eficiencia operativa y seguridad de datos para el sector inmobiliario.
