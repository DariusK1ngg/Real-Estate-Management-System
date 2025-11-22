from flask import Blueprint, render_template, request, jsonify, Response
from flask_login import login_required, current_user
from extensions import db
from models import Cliente, Venta, VentaDetalle, TipoComprobante, Talonario, Funcionario, Lote, Contrato, Cuota
from datetime import datetime, date, timedelta
from sqlalchemy import or_
from utils import role_required, get_param, clean, registrar_auditoria # <--- IMPORTANTE: Importar registrar_auditoria
from fpdf import FPDF
from num2words import num2words
import locale

bp = Blueprint('ventas', __name__)

@bp.route("/admin/ventas/definiciones")
@login_required
@role_required('Empleado', 'Vendedor')
def ventas_definiciones(): return render_template("ventas/definiciones.html")

@bp.route("/admin/ventas/definiciones/clientes")
@login_required
@role_required('Empleado', 'Vendedor', 'Cajero')
def ventas_definiciones_clientes(): return render_template("ventas/definiciones_clientes.html")

@bp.route("/admin/ventas/movimientos")
@login_required
@role_required('Empleado', 'Vendedor')
def ventas_movimientos(): return render_template("ventas/movimientos.html")

@bp.route("/admin/ventas/movimientos/contratos/nuevo")
@login_required
@role_required('Empleado', 'Vendedor')
def ventas_movimientos_contratos_nuevo(): return render_template("ventas/movimientos_contratos_nuevo.html")

@bp.route("/admin/ventas/reportes")
@login_required
@role_required('Empleado', 'Vendedor')
def ventas_reportes(): return render_template("ventas/reportes.html")

@bp.route("/api/admin/clientes", methods=["GET", "POST"])
@login_required
@role_required('Admin', 'Vendedor', 'Empleado')
def api_clientes():
    if request.method == "POST":
        data = request.json
        # Validación básica
        if Cliente.query.filter_by(documento=data["documento"]).first():
            return jsonify({"error": "Ya existe un cliente con este documento"}), 400
        
        try:
            nuevo_cliente = Cliente(
                tipo_documento_id=data.get('tipo_documento_id'), 
                documento=data['documento'],
                nombre=data['nombre'].strip().title(), 
                apellido=data['apellido'].strip().title(),
                telefono=data.get('telefono'), 
                email=data.get('email'),
                direccion=data.get('direccion'),
                ciudad_id=int(data['ciudad_id']) if data.get('ciudad_id') else None,
                barrio_id=int(data['barrio_id']) if data.get('barrio_id') else None,
                profesion_id=data.get('profesion_id'),
                tipo_cliente_id=data.get('tipo_cliente_id'),
                estado=data.get('estado', 'activo'),
                activo=True # Por defecto activo
            )
            db.session.add(nuevo_cliente)
            db.session.commit()

            # --- AUDITORÍA ---
            registrar_auditoria("CREAR", "Cliente", f"Se registró al cliente {nuevo_cliente.nombre} {nuevo_cliente.apellido} ({nuevo_cliente.documento})")
            # -----------------

            return jsonify(nuevo_cliente.to_dict()), 201
        except Exception as e:
            db.session.rollback()
            return jsonify({"error": str(e)}), 500

    # GET: Solo mostrar clientes activos (Soft Delete)
    clientes = Cliente.query.filter_by(activo=True).order_by(Cliente.nombre).all()
    return jsonify([c.to_dict() for c in clientes])

@bp.route("/api/admin/clientes/<int:cid>", methods=["GET", "PUT", "DELETE"])
@login_required
@role_required('Admin', 'Cajero', 'Empleado')
def api_cliente_detalle(cid):
    cliente = Cliente.query.get_or_404(cid)
    
    if request.method == "PUT":
        data = request.json
        if 'documento' in data and data['documento'] != cliente.documento and Cliente.query.filter_by(documento=data['documento']).first():
            return jsonify({"error": "Ya existe otro cliente con ese documento"}), 400
        
        # Guardar valores anteriores para el log
        valores_antiguos = f"{cliente.nombre} {cliente.apellido}"

        cliente.tipo_documento_id = data.get('tipo_documento_id', cliente.tipo_documento_id)
        cliente.documento = data.get('documento', cliente.documento)
        cliente.nombre = data.get('nombre', cliente.nombre)
        cliente.apellido = data.get('apellido', cliente.apellido)
        cliente.telefono = data.get('telefono', cliente.telefono)
        cliente.email = data.get('email', cliente.email)
        cliente.direccion = data.get('direccion', cliente.direccion)
        if 'ciudad_id' in data: cliente.ciudad_id = int(data['ciudad_id']) if data['ciudad_id'] else None
        if 'barrio_id' in data: cliente.barrio_id = int(data['barrio_id']) if data['barrio_id'] else None
        cliente.profesion_id = data.get('profesion_id', cliente.profesion_id)
        cliente.tipo_cliente_id = data.get('tipo_cliente_id', cliente.tipo_cliente_id)
        cliente.estado = data.get('estado', cliente.estado)
        
        db.session.commit()

        # --- AUDITORÍA ---
        registrar_auditoria("EDITAR", "Cliente", f"Se modificó al cliente ID {cid}. Anterior: {valores_antiguos}")
        # -----------------

        return jsonify(cliente.to_dict())

    if request.method == "DELETE":
        # SOFT DELETE: No borramos, solo desactivamos
        cliente.activo = False
        cliente.estado = 'inactivo'
        
        db.session.commit()

        # --- AUDITORÍA ---
        registrar_auditoria("ELIMINAR", "Cliente", f"Se eliminó (soft) al cliente {cliente.nombre} {cliente.apellido} ({cliente.documento})")
        # -----------------

        return jsonify({"message": "Cliente eliminado exitosamente."})
    
    return jsonify(cliente.to_dict())

@bp.route("/api/admin/clientes/buscar")
@login_required
def api_buscar_clientes(): 
    query = request.args.get("q", "")
    search_term = f"%{query}%"
    # Filtrar solo activos en la búsqueda también
    clientes = Cliente.query.filter(
        Cliente.activo == True,
        or_(
            (Cliente.nombre + " " + Cliente.apellido).ilike(search_term), 
            Cliente.documento.ilike(search_term)
        )
    ).limit(10).all()
    return jsonify([c.to_dict() for c in clientes])

@bp.route("/api/admin/lotes-disponibles")
@login_required
def api_lotes_disponibles(): 
    # Asegurar filtrar lotes activos si implementaste soft delete en lotes también
    lotes = Lote.query.filter(Lote.estado.in_(["disponible", "reservado"]), Lote.activo == True).all()
    return jsonify([{"id": l.id, "texto": f"{l.fraccionamiento.nombre} - M{l.manzana} L{l.numero_lote} - Gs. {int(l.precio):,}", "precio": float(l.precio)} for l in lotes])

@bp.route("/api/admin/vendedores")
@login_required
def api_buscar_vendedores():
    vendedores = Funcionario.query.filter_by(es_vendedor=True, estado='activo').all()
    return jsonify([v.to_dict() for v in vendedores])

@bp.route("/api/admin/ventas", methods=["GET", "POST"])
@login_required
@role_required('Admin', 'Vendedor', 'Empleado')
def api_ventas():
    if request.method == "POST":
        data = request.json
        if not all(k in data for k in ['cliente_id', 'fecha_venta', 'detalles']): return jsonify({"error": "Faltan datos"}), 400
        if not data['detalles']: return jsonify({"error": "Sin detalles"}), 400
        
        tipo_factura = TipoComprobante.query.filter(db.func.lower(TipoComprobante.nombre) == 'factura').first()
        if not tipo_factura:
            tipo_factura = TipoComprobante(nombre="Factura")
            db.session.add(tipo_factura); db.session.commit()
            
        talonario = Talonario.query.filter_by(activo=True, tipo_comprobante_id=tipo_factura.id).first()
        if not talonario: return jsonify({"error": "No hay talonario activo para Facturas"}), 400
        
        if talonario.numero_actual > talonario.numero_fin:
            talonario.activo = False; db.session.commit()
            return jsonify({"error": f"Talonario {talonario.timbrado} agotado"}), 400
            
        nro_factura = f"{talonario.punto_expedicion}-{talonario.caja}-{talonario.numero_actual:07d}"
        if Venta.query.filter_by(numero_factura=nro_factura).first(): return jsonify({"error": "Error de concurrencia en numeración"}), 400
        
        try:
            total_factura = sum(float(item['subtotal']) for item in data['detalles'])
            nueva_venta = Venta(
                cliente_id=data['cliente_id'], vendedor_id=data.get('vendedor_id'), talonario_id=talonario.id,
                fecha_venta=datetime.strptime(data['fecha_venta'], "%Y-%m-%d").date(), 
                numero_factura=nro_factura, total=total_factura
            )
            db.session.add(nueva_venta)
            talonario.numero_actual += 1
            db.session.flush()
            
            for item in data['detalles']:
                detalle = VentaDetalle(
                    venta_id=nueva_venta.id, lote_id=item.get('lote_id'), impuesto_id=item.get('impuesto_id'),
                    descripcion=item['descripcion'], cantidad=int(item['cantidad']), 
                    precio_unitario=float(item['precio_unitario']), subtotal=float(item['subtotal'])
                )
                db.session.add(detalle)
            db.session.commit()

            # --- AUDITORÍA ---
            registrar_auditoria("CREAR", "Venta", f"Venta registrada N° {nro_factura} por Gs. {total_factura:,.0f}")
            # -----------------

            return jsonify(nueva_venta.to_dict()), 201
        except Exception as e:
            db.session.rollback(); return jsonify({"error": str(e)}), 500
            
    ventas = Venta.query.order_by(Venta.fecha_venta.desc()).all()
    return jsonify([v.to_dict() for v in ventas])

@bp.route("/api/admin/ventas/<int:venta_id>", methods=["GET", "DELETE"])
@login_required
@role_required('Admin', 'Vendedor', 'Empleado')
def api_venta_detalle(venta_id):
    venta = Venta.query.get_or_404(venta_id)
    if request.method == "DELETE":
        if venta.estado == 'anulada': return jsonify({"error": "Ya anulada"}), 400
        venta.estado = 'anulada'
        db.session.commit()

        # --- AUDITORÍA ---
        registrar_auditoria("ANULAR", "Venta", f"Anulación de factura N° {venta.numero_factura}")
        # -----------------

        return jsonify({"message": "Anulada"})
    return jsonify(venta.to_dict())

@bp.route("/admin/ventas/factura_pdf/<int:venta_id>")
@login_required
@role_required('Admin', 'Vendedor', 'Empleado')
def generar_factura_pdf(venta_id):
    venta = Venta.query.get_or_404(venta_id)
    cliente = venta.cliente
    try: monto_en_letras = num2words(int(venta.total), lang='es')
    except: monto_en_letras = str(int(venta.total))

    empresa_nombre = get_param('EMPRESA_NOMBRE', 'INMOBILIARIA TU HOGAR S.A.')
    empresa_dir = get_param('EMPRESA_DIRECCION', 'Ruta 6ta, Km 45')
    
    class PDF(FPDF):
        def header(self):
            self.set_font('Helvetica', 'B', 14); self.cell(0, 10, clean(empresa_nombre), 0, 1, 'L')
            self.set_font('Helvetica', '', 9); self.cell(0, 5, clean(empresa_dir), 0, 1, 'L'); self.ln(10)
    
    pdf = PDF(); pdf.add_page()
    pdf.set_font('Helvetica', 'B', 12); pdf.cell(0, 10, clean(f'FACTURA N° {venta.numero_factura}'), 0, 1, 'R')
    pdf.ln(5)
    pdf.set_font('Helvetica', '', 10)
    pdf.cell(0, 5, clean(f"Cliente: {cliente.nombre} {cliente.apellido}"), 0, 1)
    pdf.cell(0, 5, clean(f"RUC/CI: {cliente.documento}"), 0, 1)
    pdf.ln(5)
    
    pdf.set_font('Helvetica', 'B', 10)
    pdf.cell(20, 8, "Cant.", 1); pdf.cell(100, 8, "Descripcion", 1); pdf.cell(35, 8, "Unitario", 1); pdf.cell(35, 8, "Subtotal", 1); pdf.ln()
    pdf.set_font('Helvetica', '', 10)
    for item in venta.detalles:
        pdf.cell(20, 8, str(item.cantidad), 1)
        pdf.cell(100, 8, clean(item.descripcion), 1)
        pdf.cell(35, 8, "{:,.0f}".format(item.precio_unitario).replace(',', '.'), 1, 0, 'R')
        pdf.cell(35, 8, "{:,.0f}".format(item.subtotal).replace(',', '.'), 1, 0, 'R'); pdf.ln()
    
    pdf.ln(5)
    pdf.set_font('Helvetica', 'B', 10)
    pdf.cell(155, 8, "TOTAL:", 0, 0, 'R')
    pdf.cell(35, 8, "{:,.0f}".format(venta.total).replace(',', '.'), 0, 1, 'R')
    pdf.set_font('Helvetica', 'I', 8); pdf.cell(0, 10, clean(f"Son: {monto_en_letras.upper()} GUARANIES"), 0, 1)

    return Response(pdf.output(dest='S').encode('latin-1'), mimetype="application/pdf", headers={"Content-Disposition": f"inline; filename=factura_{venta.numero_factura}.pdf"})