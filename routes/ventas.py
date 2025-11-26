from flask import Blueprint, render_template, request, jsonify, Response
from flask_login import login_required, current_user
from extensions import db
from models import Cliente, Servicio, Cuota, Contrato, Funcionario, Profesion, TipoCliente, Ciudad, Barrio, TipoDocumento
from datetime import datetime, date
from sqlalchemy import or_, desc
from utils import role_required, get_param, clean, registrar_auditoria

bp = Blueprint('ventas', __name__)

# --- VISTAS ---

@bp.route("/admin/ventas/movimientos")
@login_required
@role_required('Empleado', 'Vendedor', 'Admin')
def ventas_movimientos(): 
    return render_template("ventas/movimientos.html")

@bp.route("/admin/ventas/nueva")
@login_required
@role_required('Empleado', 'Vendedor', 'Admin')
def ventas_nueva(): 
    return render_template("ventas/nueva_factura.html", now=date.today().isoformat())

@bp.route("/admin/ventas/reportes")
@login_required
@role_required('Empleado', 'Vendedor', 'Admin')
def ventas_reportes(): return render_template("ventas/reportes.html")

@bp.route("/admin/ventas/definiciones")
@login_required
@role_required('Empleado', 'Vendedor', 'Admin')
def ventas_definiciones(): return render_template("ventas/definiciones.html")

@bp.route("/admin/ventas/definiciones/clientes")
@login_required
@role_required('Empleado', 'Vendedor', 'Cajero', 'Admin')
def ventas_definiciones_clientes(): 
    return render_template("ventas/definiciones.html", active_tab='clientes')

# --- API AUXILIARES (Para llenar los Selects del Formulario Cliente) ---

@bp.route("/api/admin/profesiones")
@login_required
def api_profesiones():
    return jsonify([p.to_dict() for p in Profesion.query.all()])

@bp.route("/api/admin/tipos-cliente")
@login_required
def api_tipos_cliente():
    return jsonify([t.to_dict() for t in TipoCliente.query.all()])

@bp.route("/api/admin/tipos-documentos")
@login_required
def api_tipos_documentos():
    return jsonify([t.to_dict() for t in TipoDocumento.query.all()])

@bp.route("/api/admin/ciudades")
@login_required
def api_ciudades():
    return jsonify([c.to_dict() for c in Ciudad.query.all()])

@bp.route("/api/admin/barrios")
@login_required
def api_barrios():
    ciudad_id = request.args.get('ciudad_id')
    query = Barrio.query
    if ciudad_id:
        query = query.filter_by(ciudad_id=ciudad_id)
    return jsonify([b.to_dict() for b in query.all()])

# --- API CLIENTES (CRUD COMPLETO) ---

@bp.route("/api/admin/clientes", methods=["GET", "POST"])
@login_required
def api_clientes_crud():
    # POST: Crear Cliente Completo
    if request.method == "POST":
        data = request.json
        if Cliente.query.filter_by(documento=data['documento']).first():
            return jsonify({"error": "El documento ya está registrado"}), 400
        
        try:
            c = Cliente(
                tipo_documento_id=int(data.get('tipo_documento_id')) if data.get('tipo_documento_id') else None,
                documento=data['documento'],
                nombre=data['nombre'].title(),
                apellido=data['apellido'].title(),
                profesion_id=int(data.get('profesion_id')) if data.get('profesion_id') else None,
                tipo_cliente_id=int(data.get('tipo_cliente_id')) if data.get('tipo_cliente_id') else None,
                ciudad_id=int(data.get('ciudad_id')) if data.get('ciudad_id') else None,
                barrio_id=int(data.get('barrio_id')) if data.get('barrio_id') else None,
                telefono=data.get('telefono'),
                email=data.get('email'),
                direccion=data.get('direccion'),
                estado=data.get('estado', 'activo'),
                activo=True
            )
            db.session.add(c)
            db.session.commit()
            registrar_auditoria("CREAR", "Cliente", f"Alta de cliente {c.nombre} {c.apellido}")
            return jsonify(c.to_dict())
        except Exception as e:
            db.session.rollback()
            return jsonify({"error": str(e)}), 500
    
    # GET: Listar Todos
    clientes = Cliente.query.filter_by(activo=True).order_by(Cliente.nombre).all()
    return jsonify([c.to_dict() for c in clientes])

@bp.route("/api/admin/clientes/<int:id>", methods=["GET", "PUT", "DELETE"])
@login_required
def api_cliente_individual(id):
    c = Cliente.query.get_or_404(id)
    
    if request.method == "GET":
        return jsonify(c.to_dict())
    
    if request.method == "PUT":
        data = request.json
        try:
            c.tipo_documento_id = int(data.get('tipo_documento_id')) if data.get('tipo_documento_id') else None
            c.documento = data.get('documento', c.documento)
            c.nombre = data.get('nombre', c.nombre).title()
            c.apellido = data.get('apellido', c.apellido).title()
            c.profesion_id = int(data.get('profesion_id')) if data.get('profesion_id') else None
            c.tipo_cliente_id = int(data.get('tipo_cliente_id')) if data.get('tipo_cliente_id') else None
            c.ciudad_id = int(data.get('ciudad_id')) if data.get('ciudad_id') else None
            c.barrio_id = int(data.get('barrio_id')) if data.get('barrio_id') else None
            c.telefono = data.get('telefono', c.telefono)
            c.email = data.get('email', c.email)
            c.direccion = data.get('direccion', c.direccion)
            c.estado = data.get('estado', c.estado)
            
            db.session.commit()
            registrar_auditoria("EDITAR", "Cliente", f"Modificación de cliente ID {c.id}")
            return jsonify(c.to_dict())
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    if request.method == "DELETE":
        c.activo = False # Soft delete
        c.estado = 'inactivo'
        db.session.commit()
        registrar_auditoria("ELIMINAR", "Cliente", f"Baja de cliente ID {c.id}")
        return jsonify({"message": "Cliente eliminado"})

# --- API SERVICIOS Y VENTAS (EXISTENTE) ---

@bp.route("/api/admin/servicios", methods=["GET", "POST"])
@login_required
def api_servicios():
    if request.method == "POST":
        data = request.json
        try:
            s = Servicio(nombre=data['nombre'], precio_defecto=float(data.get('precio_defecto', 0)), activo=True)
            db.session.add(s); db.session.commit()
            return jsonify({"ok": True, "id": s.id})
        except Exception as e: return jsonify({"error": str(e)}), 500
    servicios = Servicio.query.filter_by(activo=True).all()
    return jsonify([s.to_dict() for s in servicios])

@bp.route("/api/admin/servicios/<int:sid>", methods=["DELETE"])
@login_required
def api_eliminar_servicio(sid):
    s = Servicio.query.get_or_404(sid); s.activo = False; db.session.commit(); return jsonify({"ok": True})

@bp.route("/api/admin/ventas", methods=["GET"])
@login_required
def api_ventas_historial():
    servicios = Cuota.query.filter_by(tipo='servicio').order_by(desc(Cuota.id)).limit(100).all()
    data = []
    for s in servicios:
        cli = f"{s.contrato.cliente.nombre} {s.contrato.cliente.apellido}" if s.contrato and s.contrato.cliente else "N/A"
        data.append({"id": s.id, "fecha": s.fecha_vencimiento.strftime("%d/%m/%Y"), "numero": f"SERV-{s.id}", "cliente_nombre": cli, "concepto": s.observaciones, "total": float(s.valor_cuota), "estado": s.estado})
    return jsonify(data)

@bp.route("/api/admin/ventas/cargar-deuda", methods=["POST"])
@login_required
def api_cargar_deuda():
    data = request.json
    contrato = Contrato.query.get(data.get('contrato_id'))
    if not contrato: return jsonify({"error": "Contrato no encontrado"}), 404
    try:
        created_ids = []
        for item in data['items']:
            monto = float(item['monto'])
            last_cuota = Cuota.query.filter_by(contrato_id=contrato.id).order_by(Cuota.numero_cuota.desc()).first()
            next_num = (last_cuota.numero_cuota + 1) if last_cuota else 1
            servicio_nombre = Servicio.query.get(int(item['servicio_id'])).nombre
            nueva = Cuota(contrato_id=contrato.id, numero_cuota=next_num, fecha_vencimiento=datetime.strptime(data.get('fecha_vencimiento'), "%Y-%m-%d"), valor_cuota=monto, estado='pendiente', tipo='servicio', observaciones=servicio_nombre)
            db.session.add(nueva); db.session.flush(); created_ids.append(nueva.id)
        db.session.commit()
        registrar_auditoria("CREAR", "Deuda", f"Carga de servicios a contrato {contrato.numero_contrato}")
        return jsonify({"ok": True}), 201
    except Exception as e: db.session.rollback(); return jsonify({"error": str(e)}), 500

@bp.route("/api/admin/ventas/<int:id>", methods=["DELETE"])
@login_required
def api_eliminar_servicio_cargado(id):
    c = Cuota.query.get_or_404(id)
    if c.estado != 'pendiente' or c.tipo != 'servicio': return jsonify({"error": "No eliminable"}), 400
    db.session.delete(c); db.session.commit(); return jsonify({"ok": True})

@bp.route("/api/admin/clientes/buscar")
@login_required
def api_buscar_clientes(): 
    q = f"%{request.args.get('q', '')}%"
    clientes = Cliente.query.filter(Cliente.activo == True, or_((Cliente.nombre + " " + Cliente.apellido).ilike(q), Cliente.documento.ilike(q))).limit(10).all()
    return jsonify([c.to_dict() for c in clientes])

@bp.route("/api/admin/clientes/<int:cid>/contratos-activos")
@login_required
def api_contratos_activos_cliente(cid):
    cs = Contrato.query.filter_by(cliente_id=cid, estado='activo').all()
    return jsonify([{"id": c.id, "numero": c.numero_contrato, "lote": c.lote.numero_lote} for c in cs])