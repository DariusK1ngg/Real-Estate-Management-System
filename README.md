# 🏡 Inmobiliaria Mapa – Sistema de Gestión de Loteamientos y Propiedades

Proyecto web desarrollado en **Python + Flask**, diseñado para administrar fraccionamientos, lotes, clientes y asignaciones de propiedades dentro de un entorno intuitivo y visual.  
Incluye un mapa interactivo para gestionar lotes, CRUD completo y generación de reportes.

---

## 🚀 Características principales

### 🔹 Gestión de Clientes
- Alta, baja y modificación de clientes.
- Datos completos: nombre, apellido, CI, teléfono, dirección y nacionalidad.
- Búsqueda por CI.

### 🔹 Gestión de Propiedades
- Registro de loteamientos, manzanas y lotes.
- Asignación de propiedades a clientes.
- Edición y eliminación de propiedades.

### 🔹 Módulo Mapa Interactivo
(Disponible si tu proyecto lo incluye)
- Visualización de fraccionamientos.
- Marcado y edición de polígonos/lotes.
- Estados: Disponible, Reservado, Vendido.

### 🔹 Generación de Reportes
- Exportación en PDF (FPDF).
- Listados detallados por cliente o por propiedad.

---

## 🛠️ Tecnologías utilizadas

| Tecnología | Uso |
|-----------|-----|
| **Python 3.x** | Backend del sistema |
| **Flask** | Servidor web y enrutamiento |
| **MySQL** | Base de datos |
| **SQLAlchemy** | ORM (si lo usás) |
| **HTML / CSS / JS** | Interfaz de usuario |
| **Bootstrap** | Estilos y componentes |
| **Leaflet.js** | Mapa interactivo (si está incluido) |
| **FPDF** | Generación de reportes PDF |

---

## 📦 Instalación y configuración

### 1️⃣ Clonar el repositorio

### 2️⃣ Crear y activar entorno virtual
python -m venv .venv
.venv\Scripts\activate

### 3️⃣ Instalar dependencias
pip install -r requirements.txt

### 4️⃣ Configurar variables de entorno

Crear un archivo .env con:

DB_HOST=localhost
DB_USER=tu_usuario
DB_PASSWORD=tu_password
DB_NAME=inmobiliaria
SECRET_KEY=tu_clave_secreta

### 5️⃣ Ejecutar la aplicación
flask run

📌 Funcionalidades destacadas
✔ CRUD de clientes
✔ CRUD de propiedades
✔ Relación cliente → propiedad
✔ Búsqueda por CI
✔ Edición y borrado desde tabla
✔ Generación de PDF
✔ Mapa interactivo (opcional según tu proyecto)

🧑‍💻 Autor

Dario Avalos
Proyecto académico y profesional de gestión inmobiliaria.
