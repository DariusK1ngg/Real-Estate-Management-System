from flask import Blueprint, request, jsonify, render_template, session
from flask_login import login_required, current_user
from extensions import db
# CORRECCIÓN: Eliminado 'Banco' de los imports porque usas EntidadFinanciera
from models import EntidadFinanciera, CuentaBancaria, DepositoBancario, Caja, MovimientoCaja, Cotizacion
from datetime import datetime
from sqlalchemy import desc
from decimal import Decimal  # Mantenemos esto para arreglar el error de sumas
from utils import role_required, registrar_auditoria

bp = Blueprint('tesoreria', __name__)

# ==========================================
# VISTAS HTML
# ==========================================

@bp.route("/admin/tesoreria/movimientos")
@login_required
@role_required('Cajero', 'Admin')
def tesoreria_movimientos(): 
    return render_template("tesoreria/movimientos.html")

@bp.route("/admin/tesoreria/reportes")
@login_required
@role_required('Cajero', 'Admin')
def tesoreria_reportes(): 
    return render_template("tesoreria/reportes.html")

@bp.route("/admin/tesoreria/definiciones")
@login_required
@role_required('Admin', 'Cajero')
def tesoreria_definiciones(): 
    return render_template("tesoreria/definiciones.html")

# ==========================================
# APIS DE ESTADO Y APERTURA DE CAJA
# ==========================================

@bp.route("/api/admin/caja/estado", methods=["GET"])
@login_required
def api_caja_estado():
    # Verificar si hay una caja abierta en la sesión
    caja_id = session.get("caja_id")
    
    if caja_id:
        caja = Caja.query.get(caja_id)
        if caja and caja.abierta:
            return jsonify({
                "abierta": True,
                "caja_abierta": True,
                "caja_descripcion": caja.descripcion,
                "saldo_actual": float(caja.saldo_actual),
                "mensaje": f"Caja Abierta: {caja.descripcion}"
            })
    
    # Si no hay sesión
    return jsonify({
        "abierta": False,
        "caja_abierta": False,
        "caja_descripcion": "",
        "saldo_actual": 0.0,
        "mensaje": "No hay caja abierta"
    })

@bp.route("/api/admin/caja/abrir", methods=["POST"])
@login_required
def api_abrir_caja():
    data = request.json
    caja_id_seleccionada = data.get("caja_id", 1)
    
    # Usamos Decimal para evitar errores futuros en cálculos
    try:
        monto_apertura = Decimal(str(data.get("monto_apertura", 0)))
    except:
        monto_apertura = Decimal(0)
    
    caja = Caja.query.get(caja_id_seleccionada)
    if not caja:
        # Crear caja por defecto si no existe (Caja 1)
        caja = Caja(id=caja_id_seleccionada, descripcion="Caja General", sucursal="Central", saldo_actual=0, abierta=False)
        db.session.add(caja)
        db.session.commit()

    if caja.abierta:
        return jsonify({"error": "Esta caja ya está abierta"}), 400
        
    caja.abierta = True
    caja.saldo_actual = monto_apertura
    caja.fecha_apertura = datetime.now() # Registramos fecha apertura
    
    # Registrar Movimiento Inicial
    apertura = MovimientoCaja(
        caja_id=caja.id,
        tipo_movimiento="ingreso",
        monto=monto_apertura,
        concepto="Apertura de Caja",
        fecha_hora=datetime.now(),
        usuario_id=current_user.id
    )
    db.session.add(apertura)
    db.session.commit()
    
    session["caja_id"] = caja.id
    registrar_auditoria("APERTURA", "Caja", f"Apertura Caja {caja.descripcion} con {monto_apertura:,.0f}")
    return jsonify({"ok": True, "message": f"Caja '{caja.descripcion}' abierta con Gs. {monto_apertura:,.0f}"})

@bp.route("/api/admin/caja/cerrar", methods=["POST"])
@login_required
def api_cerrar_caja():
    caja_id = session.get("caja_id")
    if not caja_id:
        return jsonify({"error": "No hay ninguna caja abierta en esta sesión"}), 400
        
    caja = Caja.query.get(caja_id)
    if not caja or not caja.abierta:
        session.pop("caja_id", None)
        return jsonify({"error": "La caja no existe o ya está cerrada"}), 400
    
    saldo_cierre = caja.saldo_actual
    
    # Registrar Movimiento de Cierre (Egreso para dejar en 0 o ajuste)
    cierre = MovimientoCaja(
        caja_id=caja.id,
        tipo_movimiento="egreso",
        monto=saldo_cierre,
        concepto="Cierre de Caja (Retiro de Fondos)",
        fecha_hora=datetime.now(),
        usuario_id=current_user.id
    )
    db.session.add(cierre)
    
    caja.abierta = False
    caja.saldo_actual = 0
    caja.ultimo_arqueo = datetime.now()
    db.session.commit()
    
    session.pop("caja_id", None)
    registrar_auditoria("CIERRE", "Caja", f"Cierre Caja {caja.descripcion} con saldo {saldo_cierre:,.0f}")
    return jsonify({"ok": True, "message": f"Caja '{caja.descripcion}' cerrada con saldo Gs. {saldo_cierre:,.0f}"})

# ==========================================
# APIS DE GESTIÓN BANCARIA
# ==========================================

@bp.route("/api/admin/bancos", methods=["GET"])
@login_required
def api_bancos():
    # Usamos EntidadFinanciera en lugar de Banco
    try:
        bancos = EntidadFinanciera.query.all()
        return jsonify([b.to_dict() for b in bancos])
    except:
        return jsonify([])

@bp.route("/api/admin/entidades-financieras", methods=["GET", "POST"])
@login_required
@role_required('Admin', 'Cajero')
def api_entidades_financieras():
    if request.method == "POST":
        data = request.json
        if not data.get('nombre'): return jsonify({"error": "El nombre es requerido"}), 400
        if EntidadFinanciera.query.filter_by(nombre=data['nombre']).first(): return jsonify({"error": "La entidad ya existe"}), 400
        entidad = EntidadFinanciera(nombre=data['nombre'])
        db.session.add(entidad); db.session.commit()
        registrar_auditoria("CREAR", "EntidadFinanciera", f"Nueva entidad: {entidad.nombre}")
        return jsonify(entidad.to_dict()), 201
    return jsonify([e.to_dict() for e in EntidadFinanciera.query.order_by(EntidadFinanciera.nombre).all()])

@bp.route("/api/admin/entidades-financieras/<int:eid>", methods=["PUT", "DELETE"])
@login_required
@role_required('Admin', 'Cajero')
def api_entidad_financiera_detalle(eid):
    entidad = EntidadFinanciera.query.get_or_404(eid)
    if request.method == "PUT":
        data = request.json
        if not data.get('nombre'): return jsonify({"error": "El nombre es requerido"}), 400
        if EntidadFinanciera.query.filter(EntidadFinanciera.id != eid, EntidadFinanciera.nombre == data['nombre']).first():
            return jsonify({"error": "Ese nombre ya está en uso"}), 400
        entidad.nombre = data['nombre']
        db.session.commit()
        registrar_auditoria("EDITAR", "EntidadFinanciera", f"Editada entidad ID {eid}")
        return jsonify(entidad.to_dict())
    if request.method == "DELETE":
        if entidad.cuentas: return jsonify({"error": "No se puede eliminar, tiene cuentas asociadas."}), 400
        db.session.delete(entidad); db.session.commit()
        registrar_auditoria("ELIMINAR", "EntidadFinanciera", f"Eliminada entidad ID {eid}")
        return jsonify({"message": "Entidad eliminada"})

@bp.route("/api/admin/cuentas-bancarias", methods=["GET", "POST"])
@login_required
@role_required('Admin', 'Cajero')
def api_cuentas_bancarias():
    if request.method == "POST":
        data = request.json
        # Ajuste: Aceptamos 'entidad_id' O 'banco_id' según tu frontend
        entidad_id = data.get('entidad_id') or data.get('banco_id')
        
        if not entidad_id: return jsonify({"error": "Falta seleccionar Banco/Entidad"}), 400
        
        if CuentaBancaria.query.filter_by(numero_cuenta=data['numero_cuenta']).first():
            return jsonify({"error": "Ese número de cuenta ya existe"}), 400
            
        # CORRECCIÓN: Convertir saldo inicial a Decimal
        saldo_ini = Decimal(str(data.get('saldo_inicial', 0)))

        cuenta = CuentaBancaria(
            entidad_id=entidad_id, 
            numero_cuenta=data['numero_cuenta'], 
            titular=data['titular'], 
            tipo_cuenta=data['tipo_cuenta'], 
            moneda=data['moneda'],
            saldo=saldo_ini
        )
        db.session.add(cuenta); db.session.commit()
        registrar_auditoria("CREAR", "CuentaBancaria", f"Nueva cuenta {cuenta.numero_cuenta}")
        return jsonify(cuenta.to_dict()), 201
    
    # GET
    cuentas = CuentaBancaria.query.order_by(CuentaBancaria.numero_cuenta).all()
    # Aseguramos que el saldo se envíe como float para JSON
    res = []
    for c in cuentas:
        d = c.to_dict()
        d['saldo'] = float(c.saldo) if c.saldo else 0.0
        # Agregamos campo 'banco' para compatibilidad
        d['banco'] = c.entidad.nombre if c.entidad else "N/A"
        res.append(d)
    return jsonify(res)

@bp.route("/api/admin/cuentas-bancarias/<int:cid>", methods=["PUT", "DELETE"])
@login_required
@role_required('Admin', 'Cajero')
def api_cuenta_bancaria_detalle(cid):
    cuenta = CuentaBancaria.query.get_or_404(cid)
    if request.method == "PUT":
        data = request.json
        cuenta.entidad_id = data.get('entidad_id', cuenta.entidad_id)
        cuenta.numero_cuenta = data.get('numero_cuenta', cuenta.numero_cuenta)
        cuenta.titular = data.get('titular', cuenta.titular)
        cuenta.tipo_cuenta = data.get('tipo_cuenta', cuenta.tipo_cuenta)
        cuenta.moneda = data.get('moneda', cuenta.moneda)
        db.session.commit()
        registrar_auditoria("EDITAR", "CuentaBancaria", f"Modificada cuenta {cuenta.numero_cuenta}")
        return jsonify(cuenta.to_dict())
    if request.method == "DELETE":
        if cuenta.depositos: return jsonify({"error": "No se puede eliminar, tiene depósitos asociados."}), 400
        db.session.delete(cuenta); db.session.commit()
        registrar_auditoria("ELIMINAR", "CuentaBancaria", f"Eliminada cuenta ID {cid}")
        return jsonify({"message": "Cuenta eliminada"})

@bp.route("/api/admin/depositos", methods=["GET", "POST"])
@login_required
@role_required('Admin', 'Cajero')
def api_depositos():
    if request.method == "POST":
        data = request.json
        if not all(k in data for k in ['cuenta_id', 'fecha_deposito', 'monto']):
            return jsonify({"error": "Faltan datos requeridos"}), 400
            
        cuenta = CuentaBancaria.query.get(data['cuenta_id'])
        if not cuenta: return jsonify({"error": "La cuenta bancaria no existe"}), 404
        
        try:
            # CORRECCIÓN PRINCIPAL: Decimal para el monto
            monto = Decimal(str(data['monto']))
            fecha = datetime.strptime(data['fecha_deposito'], "%Y-%m-%d").date()
            
            deposito = DepositoBancario(
                cuenta_id=data['cuenta_id'],
                fecha_deposito=fecha,
                monto=monto, 
                referencia=data.get('referencia'),
                concepto=data.get('concepto'), 
                usuario_id=current_user.id
            )
            
            # CORRECCIÓN: Suma segura entre Decimal y Decimal (o 0)
            saldo_actual = cuenta.saldo if cuenta.saldo else Decimal(0)
            cuenta.saldo = saldo_actual + monto
            
            # --- NUEVO: Si se indica que viene de CAJA, registrar el egreso ---
            origen = data.get('origen_fondos')
            if origen == 'caja':
                caja_id = session.get('caja_id')
                if caja_id:
                    caja = Caja.query.get(caja_id)
                    if caja and caja.abierta:
                        mov = MovimientoCaja(
                            caja_id=caja.id,
                            tipo_movimiento='egreso',
                            monto=monto,
                            concepto=f"Depósito a Banco - Cta {cuenta.numero_cuenta}",
                            fecha_hora=datetime.now(),
                            usuario_id=current_user.id
                        )
                        db.session.add(mov)
                        caja.saldo_actual = (caja.saldo_actual or Decimal(0)) - monto

            db.session.add(deposito)
            db.session.commit()
            registrar_auditoria("CREAR", "DepositoBancario", f"Depósito de {monto:,.0f} en Cta {cuenta.numero_cuenta}")
            return jsonify(deposito.to_dict()), 201
            
        except Exception as e:
            db.session.rollback()
            return jsonify({"error": f"Error interno: {str(e)}"}), 500
            
    # GET
    depositos = DepositoBancario.query.order_by(DepositoBancario.fecha_deposito.desc()).limit(100).all()
    # Aseguramos float en la respuesta JSON
    res = []
    for d in depositos:
        itm = d.to_dict()
        itm['monto'] = float(d.monto)
        res.append(itm)
    return jsonify(res)

@bp.route("/api/admin/depositos/<int:did>", methods=["DELETE"])
@login_required
@role_required('Admin', 'Cajero')
def api_deposito_detalle(did):
    deposito = DepositoBancario.query.get_or_404(did)
    if deposito.estado == 'anulado':
        return jsonify({"error": "El depósito ya está anulado"}), 400
    
    cuenta = deposito.cuenta
    # Restar de forma segura
    cuenta.saldo = (cuenta.saldo or Decimal(0)) - deposito.monto
    
    deposito.estado = 'anulado'
    db.session.commit()
    registrar_auditoria("ANULAR", "DepositoBancario", f"Anulado depósito ID {did}")
    return jsonify({"message": "Depósito anulado correctamente"})

@bp.route("/api/admin/transferencias", methods=["POST"])
@login_required
@role_required('Admin', 'Cajero')
def api_transferencias_bancarias():
    data = request.json
    if not all(k in data for k in ['cuenta_origen_id', 'cuenta_destino_id', 'monto', 'fecha']):
        return jsonify({"error": "Faltan datos requeridos"}), 400

    # Usamos Decimal
    try:
        monto = Decimal(str(data['monto']))
    except:
        return jsonify({"error": "Monto inválido"}), 400

    if monto <= 0:
        return jsonify({"error": "El monto debe ser positivo"}), 400

    cuenta_origen = CuentaBancaria.query.get(data['cuenta_origen_id'])
    cuenta_destino = CuentaBancaria.query.get(data['cuenta_destino_id'])
    
    if not cuenta_origen or not cuenta_destino:
        return jsonify({"error": "Una o ambas cuentas no existen"}), 404
    
    saldo_origen = cuenta_origen.saldo or Decimal(0)
    if saldo_origen < monto:
        return jsonify({"error": "Saldo insuficiente en la cuenta de origen"}), 400
    
    try:
        fecha_transferencia = datetime.strptime(data['fecha'], "%Y-%m-%d").date()
        concepto = data.get('concepto', 'Transferencia entre cuentas')
        
        moneda_origen = cuenta_origen.moneda
        moneda_destino = cuenta_destino.moneda
        monto_debito = monto
        monto_credito = monto 

        # Lógica de conversión si son monedas distintas
        if moneda_origen != moneda_destino:
            cotizacion = Cotizacion.query.filter_by(
                fecha=fecha_transferencia,
                moneda_origen=moneda_origen if moneda_origen == 'USD' else moneda_destino,
                moneda_destino=moneda_destino if moneda_origen == 'USD' else moneda_origen
            ).first()
            
            if not cotizacion:
                cotizacion = Cotizacion.query.order_by(Cotizacion.fecha.desc()).first()
            
            if not cotizacion:
                return jsonify({"error": "No hay cotización registrada para realizar la conversión."}), 400

            # Convertimos tasas a Decimal
            compra = Decimal(str(cotizacion.compra))
            venta = Decimal(str(cotizacion.venta))
            rate = compra if moneda_origen == 'USD' else venta
            
            if moneda_origen == 'USD' and moneda_destino == 'PYG':
                monto_credito = monto * rate
            elif moneda_origen == 'PYG' and moneda_destino == 'USD':
                monto_credito = monto / rate
        
        cuenta_origen.saldo = (cuenta_origen.saldo or Decimal(0)) - monto_debito
        cuenta_destino.saldo = (cuenta_destino.saldo or Decimal(0)) + monto_credito
        
        egreso = DepositoBancario(
            cuenta_id=cuenta_origen.id,
            fecha_deposito=fecha_transferencia,
            monto=-monto_debito, 
            referencia=f"Transferencia a Cta. {cuenta_destino.numero_cuenta}",
            concepto=f"{concepto} (Envío {moneda_origen})",
            estado="confirmado",
            usuario_id=current_user.id
        )
        ingreso = DepositoBancario(
            cuenta_id=cuenta_destino.id,
            fecha_deposito=fecha_transferencia,
            monto=monto_credito,
            referencia=f"Transferencia de Cta. {cuenta_origen.numero_cuenta}",
            concepto=f"{concepto} (Recepción {moneda_destino})",
            estado="confirmado",
            usuario_id=current_user.id
        )
        
        db.session.add(egreso)
        db.session.add(ingreso)
        db.session.commit()
        
        registrar_auditoria("TRANSFERENCIA", "Tesoreria", f"Transf. {monto:,.0f} {moneda_origen} de Cta {cuenta_origen.numero_cuenta} a {cuenta_destino.numero_cuenta}")
        
        return jsonify({"message": "Transferencia realizada con éxito"}), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": "Error interno del servidor", "details": str(e)}), 500

# ==========================================
# APIS PARA ARQUEO DE CAJA
# ==========================================

@bp.route("/api/admin/caja/movimientos")
@login_required
def api_get_movimientos():
    caja_id = session.get("caja_id")
    filtro_fecha = request.args.get('fecha')
    
    query = MovimientoCaja.query
    
    if caja_id and not filtro_fecha:
        query = query.filter_by(caja_id=caja_id)
    elif filtro_fecha:
        try:
            fecha_dt = datetime.strptime(filtro_fecha, '%Y-%m-%d')
            query = query.filter(db.func.date(MovimientoCaja.fecha_hora) == fecha_dt.date())
        except: pass

    # Ordenar por el más reciente arriba
    movimientos = query.order_by(desc(MovimientoCaja.fecha_hora)).all()
    
    data = []
    for m in movimientos:
        fecha_fmt = m.fecha_hora.strftime("%d/%m/%Y %H:%M:%S")
        
        # Categoría opcional (si tu modelo no lo tiene, ponemos General)
        cat = getattr(m, 'categoria', 'General') or 'General'

        data.append({
            "id": m.id,
            "fecha": fecha_fmt,
            "concepto": m.concepto,
            "tipo": m.tipo_movimiento.upper(), # Convertimos enum a string upper
            "monto": float(m.monto),
            "usuario": m.usuario.nombre if m.usuario else "Sistema",
            "categoria": cat
        })
        
    return jsonify(data)

@bp.route("/api/admin/caja/ingreso-egreso-manual", methods=["POST"])
@login_required
def api_movimiento_manual():
    caja_id = session.get("caja_id")
    if not caja_id: return jsonify({"error": "Debe abrir caja primero"}), 400
    
    caja = Caja.query.get(caja_id)
    if not caja.abierta: return jsonify({"error": "La caja está cerrada"}), 400
    
    data = request.json
    try:
        tipo = data.get("tipo") 
        monto = Decimal(str(data.get("monto", 0)))
        concepto = data.get("concepto")
        
        if monto <= 0: return jsonify({"error": "Monto inválido"}), 400
        
        mov = MovimientoCaja(
            caja_id=caja.id,
            tipo_movimiento=tipo,
            monto=monto,
            concepto=concepto,
            fecha_hora=datetime.now(),
            usuario_id=current_user.id
            # categoria='manual' # Descomentar si tienes ese campo
        )
        db.session.add(mov)
        
        saldo_actual = caja.saldo_actual or Decimal(0)
        if tipo == 'ingreso':
            caja.saldo_actual = saldo_actual + monto
        else:
            caja.saldo_actual = saldo_actual - monto
            
        db.session.commit()
        registrar_auditoria("MOV_MANUAL", "Caja", f"{tipo.upper()} de {monto} en Caja {caja.id}")
        return jsonify({"ok": True})
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500