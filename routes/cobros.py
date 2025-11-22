from flask import Blueprint, render_template, request, jsonify, session, Response
from flask_login import login_required, current_user
from extensions import db
from models import Pago, Cuota, Caja, MovimientoCaja, CuentaBancaria, DepositoBancario
from datetime import datetime
from decimal import Decimal
from utils import role_required, get_param, clean
from fpdf import FPDF
from num2words import num2words
import locale

bp = Blueprint('cobros', __name__)

@bp.route("/admin/cobros/movimientos")
@login_required
@role_required('Cajero')
def cobros_movimientos(): return render_template("cobros/movimientos.html")

@bp.route("/admin/cobros/reportes")
@login_required
@role_required('Cajero')
def cobros_reportes(): return render_template("cobros/reportes.html")

@bp.route("/admin/cobros/definiciones")
@login_required
@role_required('Admin', 'Cajero')
def cobros_definiciones(): return render_template("cobros/definiciones.html")

@bp.route("/api/admin/clientes/<int:cliente_id>/cuotas")
@login_required
def api_get_cuotas_por_cliente(cliente_id):
    cuotas = Cuota.query.filter(Cuota.contrato.has(cliente_id=cliente_id), Cuota.estado.in_(['pendiente', 'vencida'])).order_by(Cuota.fecha_vencimiento).all()
    return jsonify([c.to_dict() for c in cuotas])

@bp.route("/api/admin/pagos", methods=["POST"])
@login_required
def api_registrar_pago():
    data = request.get_json(force=True)
    forma_id = int(data.get("forma_pago_id"))
    monto = Decimal(str(data["monto"]))
    
    caja = None
    if forma_id == 1: # Efectivo
        caja_id = session.get("caja_id")
        if not caja_id: return jsonify({"error": "Caja no abierta en sesión"}), 403
        caja = Caja.query.get(caja_id)
        if not caja or not caja.abierta: return jsonify({"error": "Caja cerrada"}), 403

    cuota = Cuota.query.get(int(data["cuota_id"]))
    if not cuota or cuota.estado == 'pagada': return jsonify({"error": "Cuota inválida"}), 400
    
    pago = Pago(
        contrato_id=cuota.contrato_id, cuota_id=cuota.id, fecha_pago=datetime.strptime(data["fecha_pago"], "%Y-%m-%d"),
        monto=monto, forma_pago_id=forma_id, referencia=data.get("referencia"), observaciones=data.get("observaciones"),
        usuario_id=current_user.id, cuenta_bancaria_id=data.get("cuenta_bancaria_id")
    )
    db.session.add(pago)
    
    cuota.estado = 'pagada'; cuota.fecha_pago = pago.fecha_pago; cuota.valor_pagado = monto
    
    if forma_id == 1 and caja:
        mov = MovimientoCaja(caja_id=caja.id, tipo_movimiento="ingreso", monto=monto, concepto=f"Cobro cuota {cuota.numero_cuota}", fecha_hora=datetime.now(), pago_id=pago.id, usuario_id=current_user.id)
        db.session.add(mov); caja.saldo_actual = (caja.saldo_actual or 0) + monto
    elif data.get("cuenta_bancaria_id"):
        cta = CuentaBancaria.query.get(data["cuenta_bancaria_id"])
        if cta:
            dep = DepositoBancario(cuenta_id=cta.id, fecha_deposito=pago.fecha_pago, monto=monto, referencia="Cobro Auto", concepto="Cobro Cuota", estado='confirmado', usuario_id=current_user.id)
            db.session.add(dep); cta.saldo = (cta.saldo or 0) + monto

    db.session.commit()
    return jsonify({"ok": True, "message": "Pago registrado", "pago_id": pago.id})

@bp.route("/admin/cobros/recibo/<int:pago_id>")
@login_required
def generar_recibo_pdf(pago_id):
    pago = Pago.query.get_or_404(pago_id)
    try: letras = num2words(int(pago.monto), lang='es')
    except: letras = str(int(pago.monto))
    
    class PDF(FPDF):
        def header(self): self.set_font('Arial','B',14); self.cell(0,10,'RECIBO',0,1,'C')
    
    pdf = PDF(); pdf.add_page(); pdf.set_font('Arial','',12)
    pdf.cell(0,10, clean(f"Recibí de: {pago.contrato.cliente.nombre}"), 0, 1)
    pdf.cell(0,10, clean(f"La suma de: {letras.upper()}"), 0, 1)
    pdf.cell(0,10, f"Monto: {int(pago.monto):,}", 0, 1)
    return Response(pdf.output(dest='S').encode('latin-1'), mimetype="application/pdf")