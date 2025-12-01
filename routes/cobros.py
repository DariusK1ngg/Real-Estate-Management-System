from flask import Blueprint, render_template, request, jsonify, session, Response
from flask_login import login_required, current_user
from extensions import db
from models import Pago, Cuota, Caja, MovimientoCaja, CuentaBancaria, DepositoBancario
from datetime import datetime, date
from decimal import Decimal
from utils import role_required, get_param, clean, registrar_auditoria 
from fpdf import FPDF
from num2words import num2words
from sqlalchemy import desc

bp = Blueprint('cobros', __name__)

@bp.route("/admin/cobros/movimientos")
@login_required
@role_required('Cajero')
def cobros_movimientos(): 
    return render_template("cobros/movimientos.html")

@bp.route("/admin/cobros/reportes")
@login_required
@role_required('Cajero')
def cobros_reportes(): 
    return render_template("cobros/reportes.html")

@bp.route("/admin/cobros/definiciones")
@login_required
@role_required('Admin', 'Cajero')
def cobros_definiciones(): 
    return render_template("cobros/definiciones.html")

@bp.route("/api/admin/clientes/<int:cliente_id>/cuotas")
@login_required
def api_get_cuotas_por_cliente(cliente_id):
    cuotas = Cuota.query.filter(
        Cuota.contrato.has(cliente_id=cliente_id), 
        Cuota.estado.in_(['pendiente', 'vencida'])
    ).order_by(desc(Cuota.tipo), Cuota.fecha_vencimiento).all()
    
    data = []
    today = date.today()
    
    for c in cuotas:
        c_dict = c.to_dict()
        dias_atraso = (today - c.fecha_vencimiento).days
        interes = 0.0
        
        # Mismo cálculo visual que usaremos para validar en el pago
        if dias_atraso > 90 and c.tipo == 'cuota': 
            tasa_diaria = 0.0275 
            interes = float(c.valor_cuota) * tasa_diaria * dias_atraso
            
        c_dict['dias_atraso'] = dias_atraso if dias_atraso > 0 else 0
        c_dict['interes_mora'] = interes
        c_dict['total_pagar'] = float(c.valor_cuota) + interes
        
        data.append(c_dict)

    return jsonify(data)

@bp.route("/api/admin/pagos", methods=["POST"])
@login_required
def api_registrar_pago():
    data = request.get_json(force=True)
    
    # 1. Validaciones básicas de entrada
    try:
        forma_id = int(data.get("forma_pago_id"))
        monto_recibido = Decimal(str(data["monto"]))
        fecha_pago_dt = datetime.strptime(data["fecha_pago"], "%Y-%m-%d")
        fecha_pago_date = fecha_pago_dt.date()
    except (ValueError, TypeError):
        return jsonify({"error": "Datos de pago inválidos"}), 400

    # 2. Obtener y Validar Cuota
    cuota = Cuota.query.get(int(data["cuota_id"]))
    if not cuota or cuota.estado == 'pagada': 
        return jsonify({"error": "Cuota inválida o ya pagada"}), 400
    
    # ---------------------------------------------------------
    # 3. LÓGICA DE SEGURIDAD: Recálculo de Interés (Backend)
    # ---------------------------------------------------------
    dias_atraso = (fecha_pago_date - cuota.fecha_vencimiento).days
    interes_calculado = Decimal(0)
    
    # Aplicar Mora solo si supera los 90 días (Regla de Negocio)
    if dias_atraso > 90 and cuota.tipo == 'cuota':
        tasa_diaria = Decimal("0.0275") # Tasa diaria (ajustar si es necesario)
        interes_calculado = cuota.valor_cuota * tasa_diaria * dias_atraso

    total_minimo_requerido = cuota.valor_cuota + interes_calculado
    
    # Validamos que el monto cubra el total (con un pequeño margen de 50 Gs por redondeo)
    if monto_recibido < (total_minimo_requerido - Decimal(50)):
        return jsonify({
            "error": "Monto insuficiente. Se detectaron intereses por mora.",
            "detalle": f"La deuda total es {total_minimo_requerido:,.0f} (Cuota: {cuota.valor_cuota:,.0f} + Mora: {interes_calculado:,.0f})",
            "dias_atraso": dias_atraso
        }), 400
    # ---------------------------------------------------------

    # 4. Procesamiento de Caja / Banco
    cuenta_bancaria_id = data.get("cuenta_bancaria_id")
    if cuenta_bancaria_id:
        cuenta_bancaria_id = int(cuenta_bancaria_id)

    caja = None
    if forma_id == 1: # Efectivo
        caja_id = session.get("caja_id")
        if not caja_id: return jsonify({"error": "Caja no abierta en sesión"}), 403
        caja = Caja.query.get(caja_id)
        if not caja or not caja.abierta: return jsonify({"error": "Caja cerrada"}), 403

    # 5. Registro del Pago
    # Si hay mora, la agregamos a la observación automáticamente
    obs_sistema = data.get("observaciones", "")
    if interes_calculado > 0:
        obs_sistema += f" [Incluye mora: {interes_calculado:,.0f} Gs por {dias_atraso} días de atraso]"

    pago = Pago(
        contrato_id=cuota.contrato_id, 
        cuota_id=cuota.id, 
        fecha_pago=fecha_pago_dt,
        monto=monto_recibido, 
        forma_pago_id=forma_id, 
        referencia=data.get("referencia"), 
        observaciones=obs_sistema.strip(),
        usuario_id=current_user.id, 
        cuenta_bancaria_id=cuenta_bancaria_id
    )
    db.session.add(pago)
    
    # Actualizar estado de la cuota
    cuota.estado = 'pagada'
    cuota.fecha_pago = pago.fecha_pago
    cuota.valor_pagado = monto_recibido 
    
    # Auditoría y Movimientos de Dinero
    audit_detalle = f"Pago cuota {cuota.numero_cuota} ({cuota.contrato.numero_contrato}). Total: {monto_recibido:,.0f}"

    if forma_id == 1 and caja:
        mov = MovimientoCaja(
            caja_id=caja.id, 
            tipo_movimiento="ingreso", 
            monto=monto_recibido, 
            concepto=f"Cobro {cuota.tipo.title()} {cuota.numero_cuota} - {cuota.contrato.cliente.nombre}", 
            fecha_hora=datetime.now(), 
            pago_id=pago.id, 
            usuario_id=current_user.id
        )
        db.session.add(mov)
        caja.saldo_actual = (caja.saldo_actual or 0) + monto_recibido
        audit_detalle += " (Efectivo)"
        
    elif cuenta_bancaria_id:
        cta = CuentaBancaria.query.get(cuenta_bancaria_id)
        if cta:
            dep = DepositoBancario(
                cuenta_id=cta.id, 
                fecha_deposito=pago.fecha_pago, 
                monto=monto_recibido, 
                referencia=data.get("referencia", "Cobro Auto"), 
                concepto=f"Cobro {cuota.tipo.title()} {cuota.numero_cuota}", 
                estado='confirmado', 
                usuario_id=current_user.id
            )
            db.session.add(dep)
            cta.saldo = (cta.saldo or 0) + monto_recibido
            audit_detalle += f" (Banco {cta.entidad.nombre})"

    db.session.commit()
    registrar_auditoria("CREAR", "Pago", audit_detalle) 
    return jsonify({"ok": True, "message": "Pago registrado correctamente", "pago_id": pago.id})

@bp.route("/admin/cobros/recibo/<int:pago_id>")
@login_required
def generar_recibo_pdf(pago_id):
    pago = Pago.query.get_or_404(pago_id)
    try: letras = num2words(int(pago.monto), lang='es')
    except: letras = str(int(pago.monto))
    
    class PDF(FPDF):
        def header(self): self.set_font('Arial','B',14); self.cell(0,10,'RECIBO DE DINERO',0,1,'C')
    
    pdf = PDF(); pdf.add_page(); pdf.set_font('Arial','',12)
    pdf.cell(0,10, clean(f"Recibí de: {pago.contrato.cliente.nombre} {pago.contrato.cliente.apellido}"), 0, 1)
    pdf.cell(0,10, clean(f"La suma de: {letras.upper()} GUARANIES"), 0, 1)
    pdf.cell(0,10, clean(f"Concepto: Pago de {pago.cuota.tipo} N° {pago.cuota.numero_cuota} ({pago.cuota.observaciones or ''})"), 0, 1)
    pdf.cell(0,10, f"Monto: {int(pago.monto):,}", 0, 1)
    return Response(pdf.output(dest='S').encode('latin-1'), mimetype="application/pdf")