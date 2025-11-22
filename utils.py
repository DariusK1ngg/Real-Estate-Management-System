from flask import jsonify
from flask_login import current_user
from functools import wraps
from extensions import db
# Importamos ParametroSistema dentro de la función para evitar ciclos, o asumimos que models ya está cargado en app context

def get_param(clave, default=""):
    """Obtiene un parámetro del sistema por su clave."""
    from models import ParametroSistema
    try:
        p = ParametroSistema.query.filter_by(clave=clave).first()
        return p.valor if p else default
    except:
        return default

def clean(text):
    """Elimina caracteres no compatibles con Latin-1 para evitar errores en FPDF"""
    if not text: return ""
    return str(text).encode('latin-1', 'replace').decode('latin-1')

def role_required(*roles):
    """Decorador para restringir acceso por roles."""
    def wrapper(fn):
        @wraps(fn)
        def decorated_view(*args, **kwargs):
            if not current_user.is_authenticated:
                return jsonify({"error": "No autorizado"}), 401
            
            # Si es Admin tiene pase libre
            if current_user.has_role('Admin'):
                return fn(*args, **kwargs)
                
            # Verificar si tiene alguno de los roles requeridos
            if not any(current_user.has_role(role) for role in roles):
                return jsonify({"error": "No tienes permiso para realizar esta acción"}), 403
                
            return fn(*args, **kwargs)
        return decorated_view
    return wrapper

def admin_required(fn):
    return role_required('Admin')(fn)