from flask import Blueprint, request, jsonify, render_template
from flask_login import login_required
from extensions import db
from models import FormaPago, TipoCliente, TipoComprobante, Profesion, TipoDocumento, Ciudad, Barrio, CondicionPago, Impuesto, Talonario, ParametroSistema, Cotizacion, Aplicacion, Role
from datetime import datetime
from utils import admin_required, role_required, registrar_auditoria

bp = Blueprint('base', __name__)

@bp.route("/admin/base/definiciones")
@login_required
@admin_required
def base_definiciones(): 
    return render_template("base/definiciones.html")

def create_api_for_simple_model(model_class, endpoint):
    @bp.route(f"/api/admin/{endpoint}", methods=["GET", "POST"], endpoint=f"api_{endpoint}")
    @login_required
    def api_simple_model():
        if request.method == "POST":
            data = request.json
            if not data.get('nombre'): return jsonify({"error": "El nombre es requerido"}), 400
            if hasattr(model_class, 'nombre') and model_class.query.filter_by(nombre=data['nombre']).first(): 
                return jsonify({"error": "Ese nombre ya existe"}), 400
            
            if endpoint == 'barrios':
                new_obj = model_class(nombre=data['nombre'], ciudad_id=data['ciudad_id'])
            else:
                new_obj = model_class(nombre=data['nombre'])
                
            db.session.add(new_obj); db.session.commit()
            registrar_auditoria("CREAR", endpoint, f"Nuevo registro: {new_obj.nombre}")
            return jsonify(new_obj.to_dict()), 201
        
        query = model_class.query
        if endpoint == 'barrios' and request.args.get('ciudad_id'):
            query = query.filter_by(ciudad_id=request.args.get('ciudad_id'))
            
        return jsonify([obj.to_dict() for obj in query.all()])

    # CORRECCIÓN 1: Se agregó "GET" a los métodos permitidos
    @bp.route(f"/api/admin/{endpoint}/<int:obj_id>", methods=["GET", "PUT", "DELETE"], endpoint=f"api_{endpoint}_detalle")
    @login_required
    def api_simple_model_detalle(obj_id):
        obj = model_class.query.get_or_404(obj_id)
        
        # CORRECCIÓN 2: Lógica para devolver el objeto cuando se solicita con GET
        if request.method == "GET":
            return jsonify(obj.to_dict())

        if request.method == "PUT":
            data = request.json
            if 'nombre' in data: obj.nombre = data.get('nombre', obj.nombre)
            if endpoint == 'barrios' and 'ciudad_id' in data: obj.ciudad_id = data['ciudad_id']
            db.session.commit()
            registrar_auditoria("EDITAR", endpoint, f"Edición ID {obj_id}")
            return jsonify(obj.to_dict())
            
        if request.method == "DELETE":
            db.session.delete(obj); db.session.commit()
            registrar_auditoria("ELIMINAR", endpoint, f"Eliminación ID {obj_id}")
            return jsonify({"message": "Eliminado correctamente"})

# Creación dinámica de endpoints
create_api_for_simple_model(FormaPago, 'formas-pago')
create_api_for_simple_model(TipoCliente, 'tipos-cliente')
create_api_for_simple_model(TipoComprobante, 'tipos-comprobante')
create_api_for_simple_model(Profesion, 'profesiones')
create_api_for_simple_model(TipoDocumento, 'tipos-documentos')
create_api_for_simple_model(Ciudad, 'ciudades')
create_api_for_simple_model(Barrio, 'barrios')

@bp.route("/api/admin/condiciones-pago", methods=["GET", "POST"])
@login_required
@role_required('Admin', 'Cajero')
def api_condiciones_pago():
    if request.method == "POST":
        data = request.json
        new_obj = CondicionPago(nombre=data['nombre'], dias=data.get('dias', 0))
        db.session.add(new_obj); db.session.commit()
        registrar_auditoria("CREAR", "CondicionPago", f"Nueva: {new_obj.nombre}")
        return jsonify(new_obj.to_dict()), 201
    return jsonify([obj.to_dict() for obj in CondicionPago.query.all()])

# CORRECCIÓN 3: Se habilitó GET para condiciones de pago
@bp.route("/api/admin/condiciones-pago/<int:obj_id>", methods=["GET", "PUT", "DELETE"])
@login_required
@role_required('Admin', 'Cajero')
def api_condicion_pago_detalle(obj_id):
    obj = CondicionPago.query.get_or_404(obj_id)
    
    # CORRECCIÓN 4: Retorno de datos en GET
    if request.method == "GET":
        return jsonify(obj.to_dict())

    if request.method == "PUT":
        data = request.json
        obj.nombre = data.get('nombre', obj.nombre)
        obj.dias = data.get('dias', obj.dias)
        db.session.commit()
        registrar_auditoria("EDITAR", "CondicionPago", f"Edición ID {obj_id}")
        return jsonify(obj.to_dict())
        
    if request.method == "DELETE":
        db.session.delete(obj); db.session.commit()
        registrar_auditoria("ELIMINAR", "CondicionPago", f"Baja ID {obj_id}")
        return jsonify({"message": "Eliminado correctamente"})

@bp.route("/api/admin/impuestos", methods=["GET", "POST"])
@login_required
@role_required('Admin')
def api_impuestos():
    if request.method == "POST":
        data = request.json
        obj = Impuesto(nombre=data['nombre'], porcentaje=data['porcentaje'])
        db.session.add(obj); db.session.commit()
        registrar_auditoria("CREAR", "Impuesto", f"Nuevo: {obj.nombre}")
        return jsonify(obj.to_dict()), 201
    return jsonify([o.to_dict() for o in Impuesto.query.all()])

@bp.route("/api/admin/impuestos/<int:obj_id>", methods=["GET", "PUT", "DELETE"])
@login_required
@role_required('Admin')
def api_impuesto_detalle(obj_id):
    obj = Impuesto.query.get_or_404(obj_id)
    if request.method == "GET":
        return jsonify(obj.to_dict())
    if request.method == "PUT":
        data = request.json
        obj.nombre = data.get('nombre', obj.nombre)
        obj.porcentaje = data.get('porcentaje', obj.porcentaje)
        db.session.commit()
        registrar_auditoria("EDITAR", "Impuesto", f"Edición ID {obj_id}")
        return jsonify(obj.to_dict())
    if request.method == "DELETE":
        db.session.delete(obj); db.session.commit()
        registrar_auditoria("ELIMINAR", "Impuesto", f"Baja ID {obj_id}")
        return jsonify({"message": "Eliminado correctamente"})

@bp.route("/api/admin/talonarios", methods=["GET", "POST"])
@login_required
@role_required('Admin')
def api_talonarios():
    if request.method == "POST":
        data = request.json
        obj = Talonario(
            tipo_comprobante_id=data['tipo_comprobante_id'],
            timbrado=data['timbrado'],
            fecha_inicio_vigencia=datetime.strptime(data['fecha_inicio_vigencia'], "%Y-%m-%d").date(),
            fecha_fin_vigencia=datetime.strptime(data['fecha_fin_vigencia'], "%Y-%m-%d").date(),
            punto_expedicion=data['punto_expedicion'],
            caja=data['caja'],
            numero_actual=data['numero_actual'],
            numero_fin=data['numero_fin'],
            activo=data.get('activo', True)
        )
        db.session.add(obj); db.session.commit()
        registrar_auditoria("CREAR", "Talonario", f"Nuevo Talonario {obj.timbrado}")
        return jsonify(obj.to_dict()), 201
    return jsonify([o.to_dict() for o in Talonario.query.order_by(Talonario.activo.desc(), Talonario.fecha_fin_vigencia.desc()).all()])

@bp.route("/api/admin/talonarios/<int:obj_id>", methods=["GET", "PUT", "DELETE"])
@login_required
@role_required('Admin')
def api_talonario_detalle(obj_id):
    obj = Talonario.query.get_or_404(obj_id)
    if request.method == "GET":
        return jsonify(obj.to_dict())
    if request.method == "PUT":
        data = request.json
        obj.tipo_comprobante_id = data.get('tipo_comprobante_id', obj.tipo_comprobante_id)
        obj.timbrado = data.get('timbrado', obj.timbrado)
        obj.fecha_inicio_vigencia = datetime.strptime(data['fecha_inicio_vigencia'], "%Y-%m-%d").date() if data.get('fecha_inicio_vigencia') else obj.fecha_inicio_vigencia
        obj.fecha_fin_vigencia = datetime.strptime(data['fecha_fin_vigencia'], "%Y-%m-%d").date() if data.get('fecha_fin_vigencia') else obj.fecha_fin_vigencia
        obj.punto_expedicion = data.get('punto_expedicion', obj.punto_expedicion)
        obj.caja = data.get('caja', obj.caja)
        obj.numero_actual = data.get('numero_actual', obj.numero_actual)
        obj.numero_fin = data.get('numero_fin', obj.numero_fin)
        obj.activo = data.get('activo', obj.activo)
        db.session.commit()
        registrar_auditoria("EDITAR", "Talonario", f"Edición ID {obj_id}")
        return jsonify(obj.to_dict())
    if request.method == "DELETE":
        db.session.delete(obj); db.session.commit()
        registrar_auditoria("ELIMINAR", "Talonario", f"Baja ID {obj_id}")
        return jsonify({"message": "Eliminado correctamente"})

@bp.route("/api/admin/parametros", methods=["GET", "POST"])
@login_required
def api_parametros_sistema():
    if request.method == "POST":
        data = request.json
        if ParametroSistema.query.filter_by(clave=data['clave']).first():
            return jsonify({"error": "Esa clave ya existe"}), 400
        param = ParametroSistema(clave=data['clave'], valor=data['valor'], descripcion=data.get('descripcion'))
        db.session.add(param); db.session.commit()
        registrar_auditoria("CREAR", "Parametro", f"Nuevo: {param.clave}")
        return jsonify(param.to_dict()), 201
    return jsonify([p.to_dict() for p in ParametroSistema.query.all()])

@bp.route("/api/admin/parametros/<int:pid>", methods=["PUT", "DELETE"])
@login_required
def api_parametro_sistema_detalle(pid):
    param = ParametroSistema.query.get_or_404(pid)
    if request.method == "PUT":
        data = request.json
        param.valor = data.get('valor', param.valor)
        param.descripcion = data.get('descripcion', param.descripcion)
        db.session.commit()
        registrar_auditoria("EDITAR", "Parametro", f"Cambio en {param.clave}")
        return jsonify(param.to_dict())
    if request.method == "DELETE":
        db.session.delete(param); db.session.commit()
        registrar_auditoria("ELIMINAR", "Parametro", f"Eliminado ID {pid}")
        return jsonify({"message": "Eliminado"})

@bp.route("/api/admin/cotizaciones", methods=["GET", "POST"])
@login_required
def api_cotizaciones_sistema():
    if request.method == "POST":
        data = request.json
        cot = Cotizacion(
            fecha=datetime.strptime(data['fecha'], "%Y-%m-%d").date(),
            moneda_origen=data['moneda_origen'],
            moneda_destino=data['moneda_destino'],
            compra=data['compra'],
            venta=data['venta']
        )
        db.session.add(cot); db.session.commit()
        registrar_auditoria("CREAR", "Cotizacion", f"Cotización del {cot.fecha}")
        return jsonify(cot.to_dict()), 201
    return jsonify([c.to_dict() for c in Cotizacion.query.order_by(Cotizacion.fecha.desc()).limit(50).all()])

@bp.route("/api/admin/cotizaciones/<int:cid>", methods=["PUT", "DELETE"])
@login_required
def api_cotizacion_sistema_detalle(cid):
    cot = Cotizacion.query.get_or_404(cid)
    if request.method == "PUT":
        data = request.json
        cot.compra = data['compra']
        cot.venta = data['venta']
        db.session.commit()
        registrar_auditoria("EDITAR", "Cotizacion", f"Edición ID {cid}")
        return jsonify(cot.to_dict())
    if request.method == "DELETE":
        db.session.delete(cot); db.session.commit()
        registrar_auditoria("ELIMINAR", "Cotizacion", f"Baja ID {cid}")
        return jsonify({"message": "Eliminado"})

@bp.route("/api/admin/aplicaciones", methods=["GET"])
@login_required
@admin_required
def api_aplicaciones():
    apps = Aplicacion.query.order_by(Aplicacion.modulo, Aplicacion.nombre).all()
    return jsonify([a.to_dict() for a in apps])

@bp.route("/api/admin/roles", methods=["GET"])
@login_required
@admin_required
def api_admin_roles():
    roles = Role.query.order_by(Role.name).all()
    return jsonify([r.to_json_dict() for r in roles])

@bp.route("/api/admin/roles/<int:id_rol>", methods=["GET", "PUT"])
@login_required
@admin_required
def api_rol_detalle(id_rol):
    rol = Role.query.get_or_404(id_rol)
    if request.method == "PUT":
        data = request.json
        if 'aplicaciones_ids' in data:
            rol.aplicaciones = []
            for app_id in data['aplicaciones_ids']:
                app = Aplicacion.query.get(app_id)
                if app:
                    rol.aplicaciones.append(app)
            db.session.commit()
            registrar_auditoria("PERMISOS", "Rol", f"Actualizados permisos para rol {rol.name}")
            return jsonify({"message": "Permisos actualizados"})
        rol.name = data.get('name', rol.name)
        rol.description = data.get('description', rol.description)
        db.session.commit()
        return jsonify(rol.to_json_dict())

    permisos = [app.id for app in rol.aplicaciones]
    return jsonify({**rol.to_json_dict(), "permisos": permisos})