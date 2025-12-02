from flask import Blueprint, request, jsonify, render_template, Response
from flask_login import login_required
from extensions import db
from models import Gasto, Venta, Cliente, Funcionario, MovimientoCaja, DepositoBancario, Lote, ListaPrecioLote, Fraccionamiento, Contrato, Cuota, Pago
from datetime import datetime, timedelta
from fpdf import FPDF
from sqlalchemy import func

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
    tipo = data.get('tipo') 
    
    # Convertir fechas
    try:
        fecha_desde = datetime.strptime(data['fecha_desde'], "%Y-%m-%d").date()
        fecha_hasta = datetime.strptime(data['fecha_hasta'], "%Y-%m-%d").date()
    except:
        return jsonify({"error": "Fechas inválidas"}), 400

    # Consulta base sobre CUOTAS tipo 'servicio'
    query = db.session.query(
        Cuota.observaciones, 
        Cuota.estado,
        func.count(Cuota.id).label('cantidad'),
        func.sum(Cuota.valor_cuota).label('total')
    ).filter(
        Cuota.tipo == 'servicio',
        Cuota.fecha_vencimiento >= fecha_desde,
        Cuota.fecha_vencimiento <= fecha_hasta
    )

    resultados = []

    if tipo == 'servicios_tipo':
        # Agrupar por Nombre del Servicio (guardado en observaciones)
        data_db = query.group_by(Cuota.observaciones).all()
        for row in data_db:
            resultados.append({
                "label": row.observaciones or "Varios",
                "cantidad": int(row.cantidad),
                "total": float(row.total or 0)
            })
            
    elif tipo == 'servicios_estado':
        # Agrupar por Estado (Pendiente vs Pagado)
        data_db = query.group_by(Cuota.estado).all()
        for row in data_db:
            label = row.estado.upper()
            resultados.append({
                "label": label,
                "cantidad": int(row.cantidad),
                "total": float(row.total or 0)
            })

    # Ordenar por total descendente
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

@bp.route("/admin/reportes/liquidacion-propietario", methods=["GET"])
@login_required
def reporte_liquidacion_view():
    """Muestra el formulario para sacar el reporte."""
    fraccionamientos = Fraccionamiento.query.order_by(Fraccionamiento.nombre).all()
    return render_template("reportes/liquidacion_propietario.html", fraccionamientos=fraccionamientos)

@bp.route("/admin/reportes/liquidacion-propietario/pdf", methods=["POST"])
@login_required
def generar_liquidacion_pdf():
    """Genera el PDF con los cálculos de comisión."""
    frac_id = request.form.get('fraccionamiento_id')
    fecha_ini = request.form.get('fecha_desde')
    fecha_fin = request.form.get('fecha_hasta')

    # 1. Validaciones
    if not frac_id or not fecha_ini or not fecha_fin:
        return "Faltan datos para generar el reporte", 400

    fraccionamiento = Fraccionamiento.query.get_or_404(frac_id)
    f_desde = datetime.strptime(fecha_ini, "%Y-%m-%d")
    f_hasta = datetime.strptime(fecha_fin, "%Y-%m-%d") + timedelta(days=1) # Incluir todo el día final

    # 2. Consultar Pagos de ese Fraccionamiento en el rango de fechas
    # Join: Pago -> Contrato -> Lote -> Fraccionamiento
    pagos = Pago.query.join(Contrato).join(Lote).filter(
        Lote.fraccionamiento_id == frac_id,
        Pago.fecha_pago >= f_desde,
        Pago.fecha_pago < f_hasta
    ).order_by(Pago.fecha_pago).all()

    # 3. Configurar PDF
    class PDF(FPDF):
        def header(self):
            self.set_font('Arial', 'B', 14)
            self.cell(0, 10, 'LIQUIDACIÓN DE PROPIETARIO', 0, 1, 'C')
            self.set_font('Arial', '', 10)
            self.cell(0, 10, f"Generado el: {datetime.now().strftime('%d/%m/%Y %H:%M')}", 0, 1, 'R')
            self.line(10, 30, 200, 30)
            self.ln(5)

        def footer(self):
            self.set_y(-15)
            self.set_font('Arial', 'I', 8)
            self.cell(0, 10, f'Página {self.page_no()}', 0, 0, 'C')

    pdf = PDF('L', 'mm', 'A4') # Horizontal para que quepan las columnas
    pdf.add_page()
    pdf.set_font('Arial', '', 11)

    # 4. Datos del Encabezado
    pdf.set_font('Arial', 'B', 12)
    pdf.cell(40, 10, "Fraccionamiento:", 0, 0)
    pdf.set_font('Arial', '', 12)
    pdf.cell(0, 10, fraccionamiento.nombre.upper(), 0, 1)
    
    pdf.set_font('Arial', 'B', 11)
    pdf.cell(40, 8, f"Período:", 0, 0)
    pdf.set_font('Arial', '', 11)
    pdf.cell(0, 8, f"Del {fecha_ini} al {fecha_fin}", 0, 1)
    
    pdf.cell(0, 5, "", 0, 1) # Espacio

    # 5. Tabla de Detalles
    # Encabezados
    pdf.set_fill_color(200, 220, 255)
    pdf.set_font('Arial', 'B', 9)
    
    # Definir anchos
    w_fecha = 25
    w_cliente = 50
    w_lote = 25
    w_cuota = 15
    w_monto = 30
    w_inmob = 35
    w_prop = 35
    
    pdf.cell(w_fecha, 8, "Fecha", 1, 0, 'C', 1)
    pdf.cell(w_cliente, 8, "Cliente", 1, 0, 'C', 1)
    pdf.cell(w_lote, 8, "Lote", 1, 0, 'C', 1)
    pdf.cell(w_cuota, 8, "N.Cuota", 1, 0, 'C', 1)
    pdf.cell(w_monto, 8, "Monto Pagado", 1, 0, 'C', 1)
    pdf.cell(w_inmob, 8, f"Inmob. ({fraccionamiento.comision_inmobiliaria}%)", 1, 0, 'C', 1)
    pdf.cell(w_prop, 8, f"Prop. ({fraccionamiento.comision_propietario}%)", 1, 1, 'C', 1)

    pdf.set_font('Arial', '', 9)
    
    total_recaudado = 0
    total_inmobiliaria = 0
    total_propietario = 0

    for p in pagos:
        # Cálculos Matemáticos
        monto = float(p.monto)
        # Porcentajes definidos en el fraccionamiento
        com_inmob_pct = float(fraccionamiento.comision_inmobiliaria or 0) / 100
        com_prop_pct = float(fraccionamiento.comision_propietario or 0) / 100
        
        monto_inmob = monto * com_inmob_pct
        monto_prop = monto * com_prop_pct
        
        # Sumar totales
        total_recaudado += monto
        total_inmobiliaria += monto_inmob
        total_propietario += monto_prop

        # Datos visuales
        cliente_nom = f"{p.contrato.cliente.nombre} {p.contrato.cliente.apellido}"
        lote_nom = f"Mz{p.contrato.lote.manzana}-L{p.contrato.lote.numero_lote}"
        n_cuota = str(p.cuota.numero_cuota) if p.cuota else "Ent" # Ent = Entrega inicial
        
        pdf.cell(w_fecha, 7, p.fecha_pago.strftime("%d/%m/%Y"), 1)
        pdf.cell(w_cliente, 7, cliente_nom[:23], 1) # Cortar nombres largos
        pdf.cell(w_lote, 7, lote_nom, 1, 0, 'C')
        pdf.cell(w_cuota, 7, n_cuota, 1, 0, 'C')
        pdf.cell(w_monto, 7, f"{int(monto):,}".replace(',', '.'), 1, 0, 'R')
        pdf.cell(w_inmob, 7, f"{int(monto_inmob):,}".replace(',', '.'), 1, 0, 'R')
        pdf.cell(w_prop, 7, f"{int(monto_prop):,}".replace(',', '.'), 1, 1, 'R')

    # 6. Totales Finales
    pdf.ln(5)
    pdf.set_font('Arial', 'B', 10)
    pdf.cell(w_fecha + w_cliente + w_lote + w_cuota, 8, "TOTALES GENERALES:", 0, 0, 'R')
    pdf.cell(w_monto, 8, f"{int(total_recaudado):,}".replace(',', '.'), 1, 0, 'R')
    pdf.cell(w_inmob, 8, f"{int(total_inmobiliaria):,}".replace(',', '.'), 1, 0, 'R')
    pdf.cell(w_prop, 8, f"{int(total_propietario):,}".replace(',', '.'), 1, 1, 'R')
    
    # Resumen de Liquidación
    pdf.ln(10)
    pdf.set_fill_color(240, 240, 240)
    pdf.cell(0, 10, "RESUMEN A LIQUIDAR", 1, 1, 'C', 1)
    
    pdf.cell(100, 10, "A FAVOR DE LA INMOBILIARIA:", 1)
    pdf.cell(0, 10, f"Gs. {int(total_inmobiliaria):,}".replace(',', '.'), 1, 1, 'R')
    
    pdf.cell(100, 10, "A FAVOR DEL PROPIETARIO:", 1)
    pdf.cell(0, 10, f"Gs. {int(total_propietario):,}".replace(',', '.'), 1, 1, 'R')

    return Response(pdf.output(dest='S').encode('latin-1'), mimetype="application/pdf")