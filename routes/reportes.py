from flask import Blueprint, request, jsonify, render_template
from flask_login import login_required
from extensions import db
from models import Gasto, Venta, Cliente, Funcionario, MovimientoCaja, DepositoBancario, Lote, ListaPrecioLote, Fraccionamiento, Contrato, Cuota, Pago
from datetime import datetime, timedelta

bp = Blueprint('reportes', __name__)

# --- VISTAS HTML ---
@bp.route("/admin/inventario/reportes/inmuebles")
@login_required
def reporte_inmuebles_view():
    lotes = Lote.query.join(Fraccionamiento).order_by(Fraccionamiento.nombre, Lote.manzana, Lote.numero_lote).all()
    return render_template("reportes/listado_inmuebles.html", lotes=lotes)

@bp.route("/admin/inventario/reportes/precios")
@login_required
def reporte_precios_view():
    precios = ListaPrecioLote.query.join(Lote).join(Fraccionamiento).order_by(Fraccionamiento.nombre, Lote.manzana).all()
    return render_template("reportes/listado_precios.html", precios=precios)

@bp.route("/admin/inventario/reportes/contratos")
@login_required
def reporte_contratos_view(): 
    contratos = Contrato.query.order_by(Contrato.fecha_contrato.desc()).all()
    return render_template("reportes/listado_contratos.html", contratos=contratos)

@bp.route("/admin/cobros/reportes/arqueo")
@login_required
def reporte_arqueo_view(): return render_template("reportes/arqueo_caja.html")

@bp.route("/admin/tesoreria/reportes/extracto")
@login_required
def reporte_extracto_view(): return render_template("reportes/extracto_bancario.html")

# --- APIS DE DATOS ---

@bp.route("/api/reportes/gastos/resumen", methods=["POST"])
@login_required
def api_reporte_gastos():
    data = request.json
    desde = datetime.strptime(data['fecha_desde'], "%Y-%m-%d").date()
    hasta = datetime.strptime(data['fecha_hasta'], "%Y-%m-%d").date()
    
    gastos = Gasto.query.filter(Gasto.fecha_factura >= desde, Gasto.fecha_factura <= hasta, Gasto.estado != 'anulado').all()
    resumen = {}
    detalles = []
    total = 0
    for g in gastos:
        cat = g.categoria.nombre
        resumen[cat] = resumen.get(cat, 0) + float(g.monto)
        total += float(g.monto)
        detalles.append(g.to_dict())
        
    return jsonify({"detalles": detalles, "resumen": [{"nombre": k, "total": v} for k, v in resumen.items()], "total_general": total})

@bp.route("/api/reportes/ventas/resumen", methods=["POST"])
@login_required
def api_reporte_ventas_resumen():
    data = request.json
    tipo = data.get('tipo') # 'vendedor', 'ranking'
    fecha_desde = datetime.strptime(data['fecha_desde'], "%Y-%m-%d").date()
    fecha_hasta = datetime.strptime(data['fecha_hasta'], "%Y-%m-%d").date()

    query = db.session.query(
        Venta.id, Venta.fecha_venta, Venta.total, Venta.numero_factura,
        Cliente.nombre.label('cliente_nombre'), Cliente.apellido.label('cliente_apellido'),
        Funcionario.nombre.label('vendedor_nombre'), Funcionario.apellido.label('vendedor_apellido')
    ).join(Cliente, Venta.cliente_id == Cliente.id)\
     .outerjoin(Funcionario, Venta.vendedor_id == Funcionario.id)\
     .filter(Venta.fecha_venta >= fecha_desde, Venta.fecha_venta <= fecha_hasta, Venta.estado == 'emitida')

    ventas = query.all()
    
    resultados = []
    
    if tipo == 'vendedores':
        agrupado = {}
        for v in ventas:
            vend = f"{v.vendedor_nombre} {v.vendedor_apellido}" if v.vendedor_nombre else "Sin Vendedor"
            if vend not in agrupado: agrupado[vend] = {'cantidad': 0, 'total': 0}
            agrupado[vend]['cantidad'] += 1
            agrupado[vend]['total'] += float(v.total)
        
        resultados = [{"label": k, "cantidad": v['cantidad'], "total": v['total']} for k, v in agrupado.items()]

    elif tipo == 'ranking':
        agrupado = {}
        for v in ventas:
            cli = f"{v.cliente_nombre} {v.cliente_apellido}"
            if cli not in agrupado: agrupado[cli] = {'cantidad': 0, 'total': 0}
            agrupado[cli]['cantidad'] += 1
            agrupado[cli]['total'] += float(v.total)
        
        resultados = [{"label": k, "cantidad": v['cantidad'], "total": v['total']} for k, v in agrupado.items()]
        resultados.sort(key=lambda x: x['total'], reverse=True)

    return jsonify(resultados)

@bp.route("/api/reportes/arqueo", methods=["POST"])
@login_required
def api_reporte_arqueo():
    d = request.json
    desde = datetime.strptime(d['fecha_desde'], "%Y-%m-%d")
    hasta = datetime.strptime(d['fecha_hasta'], "%Y-%m-%d") + timedelta(days=1)
    movs = MovimientoCaja.query.filter(MovimientoCaja.caja_id == d['caja_id'], MovimientoCaja.fecha_hora >= desde, MovimientoCaja.fecha_hora < hasta).all()
    ingresos = sum(m.monto for m in movs if m.tipo_movimiento == 'ingreso')
    egresos = sum(m.monto for m in movs if m.tipo_movimiento == 'egreso')
    res = [{"fecha": m.fecha_hora.strftime("%d/%m %H:%M"), "tipo": m.tipo_movimiento, "concepto": m.concepto, "monto": float(m.monto), "usuario": m.usuario.nombre if m.usuario else ""} for m in movs]
    return jsonify({"movimientos": res, "total_ingresos": float(ingresos), "total_egresos": float(egresos), "saldo_periodo": float(ingresos-egresos)})

@bp.route("/api/reportes/extracto", methods=["POST"])
@login_required
def api_reporte_extracto():
    d = request.json
    desde = datetime.strptime(d['fecha_desde'], "%Y-%m-%d").date()
    hasta = datetime.strptime(d['fecha_hasta'], "%Y-%m-%d").date()
    deps = DepositoBancario.query.filter(DepositoBancario.cuenta_id == d['cuenta_id'], DepositoBancario.fecha_deposito >= desde, DepositoBancario.fecha_deposito <= hasta).all()
    return jsonify([{"fecha": dep.fecha_deposito.strftime("%d/%m/%Y"), "referencia": dep.referencia, "concepto": dep.concepto, "monto": float(dep.monto)} for dep in deps])

@bp.route("/api/reportes/clientes/estado-cuenta", methods=["POST"])
@login_required
def api_reporte_estado_cuenta():
    data = request.json
    cliente = Cliente.query.get_or_404(data['cliente_id'])
    contratos = Contrato.query.filter_by(cliente_id=cliente.id).all()
    res = {"cliente": f"{cliente.nombre} {cliente.apellido}", "documento": cliente.documento, "contratos": []}
    for c in contratos:
        cuotas = Cuota.query.filter_by(contrato_id=c.id).all()
        pagos = Pago.query.filter_by(contrato_id=c.id).all()
        res["contratos"].append({
            "numero": c.numero_contrato, "lote": c.lote.numero_lote, 
            "total_contrato": float(c.valor_total),
            "total_pagado": sum(float(p.monto) for p in pagos),
            "saldo_pendiente": sum(float(cu.valor_cuota) for cu in cuotas if cu.estado != 'pagada'),
            "cuotas_vencidas": len([cu for cu in cuotas if cu.estado == 'vencida']),
            "historial_pagos": [p.to_dict() for p in pagos]
        })
    return jsonify(res)