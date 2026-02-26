from flask import Blueprint, render_template, request, jsonify, Response
from flask_login import login_required, current_user
from extensions import db
from models import Cliente, Servicio, Cuota, Contrato, Funcionario, Profesion, TipoCliente, Ciudad, Barrio, TipoDocumento
from datetime import datetime, date
from sqlalchemy import or_, desc
from utils import role_required, get_param, clean, registrar_auditoria

bp = Blueprint('ventas', __name__)

# --- VISTAS (PÁGINAS HTML) ---

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

# --- RUTAS DE DEFINICIONES (PESTAÑAS) ---

@bp.route("/admin/ventas/definiciones")
@login_required
@role_required('Empleado', 'Vendedor', 'Admin')
def ventas_definiciones(): 
    # Pestaña por defecto: Servicios
    return render_template("ventas/definiciones.html", active_tab='servicios')

@bp.route("/admin/ventas/definiciones/clientes")
@login_required
@role_required('Empleado', 'Vendedor', 'Cajero', 'Admin')
def ventas_definiciones_clientes(): 
    # Esta ruta arregla el error del Dashboard
    return render_template("ventas/definiciones.html", active_tab='clientes')

# --- APIS AUXILIARES (PARA EL FORMULARIO DE CLIENTES) ---

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
    
    # GET Listado
    # --- CAMBIAR ORDEN LISTA CLIENTES (Cliente.nombre.desc()) ---
    clientes = Cliente.query.filter_by(activo=True).order_by(Cliente.nombre).all()
    return jsonify([c.to_dict() for c in clientes])

@bp.route("/api/admin/clientes/<int:id>", methods=["GET", "PUT", "DELETE"])
@login_required
def api_cliente_individual(id):
    c = Cliente.query.get_or_404(id)
    
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
            db.session.rollback()
            return jsonify({"error": str(e)}), 500

    if request.method == "DELETE":
        try:
            c.activo = False
            c.estado = 'inactivo'
            db.session.commit()
            registrar_auditoria("ELIMINAR", "Cliente", f"Baja de cliente ID {c.id}")
            return jsonify({"message": "Cliente eliminado"})
        except Exception as e:
            db.session.rollback()
            return jsonify({"error": str(e)}), 500
    
    return jsonify(c.to_dict())

# --- API SERVICIOS (CATÁLOGO) ---

@bp.route("/api/admin/servicios", methods=["GET", "POST"])
@login_required
def api_servicios():
    if request.method == "POST":
        data = request.json
        try:
            s = Servicio(
                nombre=data['nombre'],
                precio_defecto=float(data.get('precio_defecto', 0)),
                activo=True
            )
            db.session.add(s)
            db.session.commit()
            return jsonify({"ok": True, "id": s.id})
        except Exception as e:
            db.session.rollback()
            return jsonify({"error": str(e)}), 500
            
    servicios = Servicio.query.filter_by(activo=True).all()
    return jsonify([s.to_dict() for s in servicios])

@bp.route("/api/admin/servicios/<int:sid>", methods=["DELETE"])
@login_required
def api_eliminar_servicio(sid):
    s = Servicio.query.get_or_404(sid)
    try:
        s.activo = False
        db.session.commit()
        return jsonify({"ok": True})
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

# --- API VENTAS (CARGA Y LISTADO) ---

@bp.route("/api/admin/ventas", methods=["GET", "POST"])
@login_required
def api_ventas_general():
    # GET: Listar Historial
    if request.method == "GET":
        # --- CAMBIAR ORDEN TABLA SERVICIOS CARGADOS ---
        # .order_by(desc(Cuota.id)) = Descendente (Nuevos primero)
        # .order_by(Cuota.id)       = Ascendente (Viejos primero)
        servicios_cargados = Cuota.query.filter_by(tipo='servicio').order_by(desc(Cuota.id)).limit(100).all()
        data = []
        for s in servicios_cargados:
            cliente_nombre = "Desconocido"
            cliente_doc = "-"
            if s.contrato and s.contrato.cliente:
                cliente_nombre = f"{s.contrato.cliente.nombre} {s.contrato.cliente.apellido}"
                cliente_doc = s.contrato.cliente.documento
            
            data.append({
                "id": s.id,
                "fecha": s.fecha_vencimiento.strftime("%d/%m/%Y"),
                "numero": f"SERV-{s.id}",
                "cliente_nombre": cliente_nombre,
                "cliente_documento": cliente_doc,
                "concepto": s.observaciones,
                "total": float(s.valor_cuota),
                "estado": s.estado
            })
        return jsonify(data)

    # POST: Cargar Deuda
    if request.method == "POST":
        data = request.json
        if not data.get('contrato_id'): return jsonify({"error": "Debe seleccionar un contrato"}), 400
        
        contrato = Contrato.query.get(data['contrato_id'])
        if not contrato: return jsonify({"error": "Contrato no encontrado"}), 404
        
        try:
            created_ids = []
            for item in data['items']:
                servicio_id = int(item['servicio_id'])
                servicio = Servicio.query.get(servicio_id)
                monto = float(item['monto'])
                
                last_cuota = Cuota.query.filter_by(contrato_id=contrato.id).order_by(Cuota.numero_cuota.desc()).first()
                next_num = (last_cuota.numero_cuota + 1) if last_cuota else 1
                
                nueva_cuota = Cuota(
                    contrato_id=contrato.id,
                    numero_cuota=next_num,
                    fecha_vencimiento=datetime.strptime(data.get('fecha_vencimiento', date.today().isoformat()), "%Y-%m-%d").date(),
                    valor_cuota=monto,
                    estado='pendiente',
                    tipo='servicio',
                    observaciones=f"{servicio.nombre}"
                )
                db.session.add(nueva_cuota)
                db.session.flush()
                created_ids.append(nueva_cuota.id)
            
            db.session.commit()
            registrar_auditoria("CREAR", "Deuda", f"Se cargaron {len(created_ids)} servicios al contrato {contrato.numero_contrato}")
            return jsonify({"ok": True})
            
        except Exception as e:
            db.session.rollback()
            return jsonify({"error": str(e)}), 500

@bp.route("/api/admin/ventas/<int:id>", methods=["DELETE"])
@login_required
def api_eliminar_servicio_cargado(id):
    cuota = Cuota.query.get_or_404(id)
    if cuota.estado != 'pendiente' or cuota.tipo != 'servicio':
        return jsonify({"error": "No se puede eliminar"}), 400
    
    try:
        db.session.delete(cuota)
        db.session.commit()
        registrar_auditoria("ELIMINAR", "Deuda", f"Se eliminó el servicio pendiente ID {id}")
        return jsonify({"ok": True})
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

@bp.route("/api/admin/clientes/buscar")
@login_required
def api_buscar_clientes(): 
    query = request.args.get("q", "")
    search_term = f"%{query}%"
    clientes = Cliente.query.filter(
        Cliente.activo == True,
        or_(
            (Cliente.nombre + " " + Cliente.apellido).ilike(search_term), 
            Cliente.documento.ilike(search_term)
        )
    ).limit(10).all()
    return jsonify([c.to_dict() for c in clientes])

@bp.route("/api/admin/clientes/<int:cid>/contratos-activos")
@login_required
def api_contratos_activos_cliente(cid):
    contratos = Contrato.query.filter_by(cliente_id=cid, estado='activo').all()
    return jsonify([{"id": c.id, "numero": c.numero_contrato, "lote": c.lote.numero_lote, "manzana": c.lote.manzana} for c in contratos])

# --- RUTA AGREGADA PARA BUSCADOR NATIVO ---
@bp.route("/api/ventas/clientes/buscar_simple")
@login_required
def buscar_clientes_simple_ventas():
    search = request.args.get('q', '')
    if not search or len(search) < 2:
        return jsonify([])

    resultados = Cliente.query.filter(
        Cliente.activo == True,
        or_(
            Cliente.nombre.ilike(f'%{search}%'),
            Cliente.apellido.ilike(f'%{search}%'),
            Cliente.documento.ilike(f'%{search}%')
        )
    ).limit(10).all()

    data = []
    for c in resultados:
        nombre_completo = f"{c.nombre} {c.apellido}".strip()
        data.append({
            'id': c.id,
            'texto': f"{nombre_completo} - {c.documento}"
        })
    
    return jsonify(data)