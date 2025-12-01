from flask import Blueprint, render_template, request, jsonify, session
from flask_login import login_required, current_user
from extensions import db
from models import Gasto, CategoriaGasto, Proveedor, Caja, MovimientoCaja, CuentaBancaria, DepositoBancario
from datetime import datetime
from utils import role_required, registrar_auditoria # <--- IMPORTAR

bp = Blueprint('gastos', __name__)

@bp.route("/admin/gastos/movimientos")
@login_required
@role_required('Cajero', 'Empleado')
def gastos_movimientos(): return render_template("gastos/movimientos.html", date_today=datetime.now().strftime('%Y-%m-%d'))

@bp.route("/admin/gastos/definiciones")
@login_required
@role_required('Cajero', 'Empleado')
def gastos_definiciones(): return render_template("gastos/definiciones.html")

@bp.route("/admin/gastos/reportes")
@login_required
@role_required('Cajero', 'Empleado')
def gastos_reportes(): return render_template("gastos/reportes.html")

@bp.route("/api/admin/gastos", methods=["GET", "POST"])
@login_required
@role_required('Admin', 'Cajero', 'Empleado')
def api_gastos():
    if request.method == "POST":
        data = request.json
        if not all(k in data for k in ['proveedor_id', 'categoria_gasto_id', 'fecha_factura', 'monto']):
            return jsonify({"error": "Faltan datos"}), 400
        gasto = Gasto(
            proveedor_id=data['proveedor_id'], 
            categoria_gasto_id=data['categoria_gasto_id'],
            detalle=data.get('detalle'),
            numero_factura=data.get('numero_factura'),
            fecha_factura=datetime.strptime(data['fecha_factura'], "%Y-%m-%d").date(),
            monto=float(data['monto']), estado='pendiente'
        )
        db.session.add(gasto)
        db.session.commit()
        registrar_auditoria("CREAR", "Gasto", f"Nuevo gasto registrado por Gs. {gasto.monto:,.0f} (Prov ID: {gasto.proveedor_id})") # <--- AUDITORIA
        return jsonify(gasto.to_dict()), 201
    
    gastos = Gasto.query.order_by(Gasto.fecha_factura.desc()).all()
    return jsonify([g.to_dict() for g in gastos])

@bp.route("/api/admin/gastos/<int:gid>", methods=["DELETE"])
@login_required
@role_required('Admin', 'Cajero', 'Empleado')
def api_gasto_delete(gid):
    gasto = Gasto.query.get_or_404(gid)
    if gasto.estado == 'anulado': return jsonify({"error": "Ya anulado"}), 400
    gasto.estado = 'anulado'
    db.session.commit()
    registrar_auditoria("ANULAR", "Gasto", f"Se anuló el gasto ID {gid}") # <--- AUDITORIA
    return jsonify({"message": "Anulado"})

@bp.route("/api/admin/gastos/<int:gasto_id>/pagar", methods=["POST"])
@login_required
def api_pagar_gasto(gasto_id):
    gasto = Gasto.query.get_or_404(gasto_id)
    if gasto.estado == 'pagado': return jsonify({"error": "Ya pagado"}), 400

    data = request.json
    metodo = data.get('metodo_pago')
    fecha_pago = datetime.strptime(data['fecha_pago'], "%Y-%m-%d").date()
    
    try:
        if metodo == 'efectivo':
            caja_id = session.get("caja_id")
            if not caja_id: return jsonify({"error": "Debe abrir una caja para pagar en efectivo"}), 400
            caja = Caja.query.get(caja_id)
            if not caja.abierta: return jsonify({"error": "Caja cerrada"}), 400
            if caja.saldo_actual < gasto.monto: return jsonify({"error": f"Saldo insuficiente en caja (Gs. {caja.saldo_actual:,.0f})"}), 400
            
            mov = MovimientoCaja(
                caja_id=caja.id, tipo_movimiento='egreso', monto=gasto.monto,
                concepto=f"Pago Gasto #{gasto.numero_factura or gasto.id}",
                fecha_hora=datetime.now(), usuario_id=current_user.id
            )
            db.session.add(mov)
            caja.saldo_actual -= gasto.monto

        elif metodo == 'banco':
            cuenta = CuentaBancaria.query.get(data.get('cuenta_id'))
            if not cuenta: return jsonify({"error": "Cuenta inválida"}), 400
            if cuenta.saldo < gasto.monto: return jsonify({"error": f"Saldo insuficiente en banco (Gs. {cuenta.saldo:,.0f})"}), 400
            
            debito = DepositoBancario(
                cuenta_id=cuenta.id, fecha_deposito=fecha_pago, monto=-gasto.monto,
                referencia=data.get('referencia'), concepto=f"Pago Gasto #{gasto.id}",
                estado='confirmado', usuario_id=current_user.id
            )
            db.session.add(debito)
            cuenta.saldo -= gasto.monto
        
        gasto.estado = 'pagado'
        gasto.fecha_pago = fecha_pago
        db.session.commit()
        registrar_auditoria("PAGAR", "Gasto", f"Pago de gasto ID {gasto.id} por {gasto.monto:,.0f} vía {metodo}") # <--- AUDITORIA
        return jsonify({"message": "Pago registrado"})
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

# --- PROVEEDORES ---
@bp.route("/api/admin/proveedores", methods=["GET", "POST"])
@login_required
@role_required('Admin', 'Empleado')
def api_proveedores():
    if request.method == "POST":
        data = request.json
        p = Proveedor(razon_social=data['razon_social'], ruc=data['ruc'], telefono=data.get('telefono'), direccion=data.get('direccion'))
        db.session.add(p); db.session.commit()
        registrar_auditoria("CREAR", "Proveedor", f"Alta proveedor {p.razon_social}") # <--- AUDITORIA
        return jsonify(p.to_dict())
    return jsonify([p.to_dict() for p in Proveedor.query.all()])

@bp.route("/api/admin/proveedores/<int:pid>", methods=["GET", "PUT", "DELETE"])
@login_required
@role_required('Admin', 'Empleado')
def api_proveedor_detalle(pid):
    proveedor = Proveedor.query.get_or_404(pid)
    if request.method == "PUT":
        data = request.json
        if 'ruc' in data and data['ruc'] != proveedor.ruc and Proveedor.query.filter_by(ruc=data['ruc']).first():
            return jsonify({"error": "Ya existe otro proveedor con ese RUC"}), 400
        proveedor.razon_social = data.get('razon_social', proveedor.razon_social)
        proveedor.ruc = data.get('ruc', proveedor.ruc)
        proveedor.telefono = data.get('telefono', proveedor.telefono)
        proveedor.direccion = data.get('direccion', proveedor.direccion)
        db.session.commit()
        registrar_auditoria("EDITAR", "Proveedor", f"Modificación proveedor ID {pid}") # <--- AUDITORIA
        return jsonify(proveedor.to_dict())
    if request.method == "DELETE":
        if proveedor.gastos: return jsonify({"error": "No se puede eliminar, tiene gastos asociados."}), 400
        db.session.delete(proveedor)
        db.session.commit()
        registrar_auditoria("ELIMINAR", "Proveedor", f"Baja proveedor ID {pid}") # <--- AUDITORIA
        return jsonify({"message": "Proveedor eliminado"})
    return jsonify(proveedor.to_dict())

# --- CATEGORÍAS ---
@bp.route("/api/admin/categorias-gasto", methods=["GET", "POST"])
@login_required
@role_required('Admin', 'Empleado')
def api_categorias():
    if request.method == "POST":
        c = CategoriaGasto(nombre=request.json['nombre'], descripcion=request.json.get('descripcion'))
        db.session.add(c); db.session.commit()
        registrar_auditoria("CREAR", "CategoriaGasto", f"Nueva categoría: {c.nombre}") # <--- AUDITORIA
        return jsonify(c.to_dict())
    return jsonify([c.to_dict() for c in CategoriaGasto.query.all()])

@bp.route("/api/admin/categorias-gasto/<int:cid>", methods=["GET", "PUT", "DELETE"])
@login_required
@role_required('Admin', 'Empleado')
def api_categoria_gasto_detalle(cid):
    categoria = CategoriaGasto.query.get_or_404(cid)
    if request.method == "PUT":
        data = request.json
        if 'nombre' in data and data['nombre'] != categoria.nombre and CategoriaGasto.query.filter_by(nombre=data['nombre']).first():
            return jsonify({"error": "Ya existe otra categoría con ese nombre"}), 400
        categoria.nombre = data.get('nombre', categoria.nombre)
        categoria.descripcion = data.get('descripcion', categoria.descripcion)
        db.session.commit()
        registrar_auditoria("EDITAR", "CategoriaGasto", f"Editada categoría ID {cid}") # <--- AUDITORIA
        return jsonify(categoria.to_dict())
    if request.method == "DELETE":
        if categoria.gastos: return jsonify({"error": "No se puede eliminar, tiene gastos asociados."}), 400
        db.session.delete(categoria); db.session.commit()
        registrar_auditoria("ELIMINAR", "CategoriaGasto", f"Eliminada categoría ID {cid}") # <--- AUDITORIA
        return jsonify({"message": "Categoría eliminada"})
    return jsonify(categoria.to_dict())