from flask import Blueprint, render_template, request, jsonify, Response
from flask_login import login_required, current_user
from extensions import db
from models import Fraccionamiento, Lote, Contrato, Cuota, Cliente, ListaPrecioLote, Funcionario
from datetime import datetime, timedelta, date
from utils import role_required, admin_required, get_param, clean, registrar_auditoria
from sqlalchemy import or_, desc
from dateutil.relativedelta import relativedelta
from fpdf import FPDF
from num2words import num2words
import locale

bp = Blueprint('inventario', __name__)

@bp.route("/api/inventario/vendedores-activos")
@login_required
def api_vendedores_activos():
    # Filtra solo los que tienen el check de vendedor y están activos
    vendedores = Funcionario.query.filter_by(es_vendedor=True, estado='activo').all()
    return jsonify([f.to_dict() for f in vendedores])

# --- VISTAS HTML ---

@bp.route("/admin/inventario/movimientos")
@login_required
@role_required('Empleado', 'Vendedor', 'Admin')
def inventario_movimientos():
    return render_template("inventario/movimientos.html")

@bp.route("/admin/inventario/contratos/nuevo")
@login_required
@role_required('Empleado', 'Vendedor', 'Admin')
def inventario_nuevo_contrato():
    return render_template("inventario/movimientos_contratos_nuevo.html", now=date.today().isoformat())

@bp.route("/admin/inventario/reportes")
@login_required
def inventario_reportes(): return render_template("inventario/reportes.html")

@bp.route("/admin/inventario/definiciones")
@login_required
def inventario_definiciones(): return render_template("inventario/definiciones_fraccionamientos.html")

@bp.route("/admin/inventario/fraccionamientos/<int:fraccionamiento_id>")
@login_required
def inventario_fraccionamiento_detalle(fraccionamiento_id):
    fraccionamiento = Fraccionamiento.query.get_or_404(fraccionamiento_id)
    return render_template("inventario/fraccionamiento_detalle.html", fraccionamiento=fraccionamiento)

# ==========================================
# APIs PÚBLICAS (PARA EL MAPA)
# ==========================================

@bp.route("/api/fraccionamientos", methods=["GET"])
def public_fraccionamientos():
    # Usado por main.js y admin.js para cargar el mapa
    fracs = Fraccionamiento.query.all()
    features = [f.to_feature() for f in fracs]
    return jsonify({"type": "FeatureCollection", "features": features})

@bp.route("/api/lotes", methods=["GET"])
def public_lotes():
    # Usado por main.js y admin.js
    frac_id = request.args.get('fraccionamiento_id')
    query = Lote.query.filter_by(activo=True)
    if frac_id:
        query = query.filter_by(fraccionamiento_id=frac_id)
    
    lotes = query.all()
    features = [l.to_feature() for l in lotes]
    return jsonify({"type": "FeatureCollection", "features": features})

# ==========================================
# APIs ADMINISTRATIVAS (GESTIÓN DE MAPA)
# ==========================================

@bp.route("/api/admin/fraccionamientos", methods=["GET", "POST"])
@login_required
def api_admin_fraccionamientos():
    # GET: Lista simple para selects
    if request.method == "GET":
        q = request.args.get('q')
        query = Fraccionamiento.query
        if q:
            query = query.filter(Fraccionamiento.nombre.ilike(f"%{q}%"))
        fracs = query.order_by(Fraccionamiento.nombre).all()
        return jsonify([f.to_dict() for f in fracs])

    # POST: Crear Fraccionamiento desde el Mapa
    if request.method == "POST":
        data = request.json
        
        # --- BLOQUE DE SEGURIDAD: VALIDAR DUPLICADO ---
        nombre_limpio = data['nombre'].strip()
        existe = Fraccionamiento.query.filter(Fraccionamiento.nombre.ilike(nombre_limpio)).first()
        if existe:
            return jsonify({"error": f"Ya existe un fraccionamiento con el nombre '{nombre_limpio}'"}), 400

        try:
            nuevo = Fraccionamiento(
                nombre=nombre_limpio,
                descripcion=data.get('descripcion'),
                ciudad_id=int(data['ciudad_id']) if data.get('ciudad_id') else None,
                geojson=data['geojson']
            )
            db.session.add(nuevo)
            db.session.commit()
            registrar_auditoria("CREAR", "Fraccionamiento", f"Creado fraccionamiento: {nuevo.nombre}")
            return jsonify({"ok": True, "id": nuevo.id})
        except Exception as e:
            db.session.rollback()
            return jsonify({"error": str(e)}), 500

@bp.route("/api/admin/fraccionamientos/<int:id>", methods=["GET", "PATCH", "DELETE"])
@bp.route("/api/admin/fraccionamientos/<int:id>/detalle", methods=["GET"])
@login_required
def api_admin_fraccionamiento_detalle(id):
    f = Fraccionamiento.query.get_or_404(id)
    
    if request.method == "GET":
        # Usado en la vista de detalle para ver lotes asociados
        if request.endpoint.endswith('detalle'): # Detalle completo con lotes
            lotes = [{"id": l.id, "numero_lote": l.numero_lote, "manzana": l.manzana, "estado": l.estado} for l in f.lotes]
            d = f.to_dict()
            d['lotes'] = lotes
            return jsonify(d)
        return jsonify(f.to_dict())

    if request.method == "PATCH":
        data = request.json
        cambios = []
        try:
            if 'nombre' in data:
                nuevo_nombre = data['nombre'].strip()
                if f.nombre != nuevo_nombre: 
                    existe = Fraccionamiento.query.filter(
                        Fraccionamiento.nombre.ilike(nuevo_nombre),
                        Fraccionamiento.id != id 
                    ).first()
                    
                    if existe:
                         return jsonify({"error": f"Ya existe otro fraccionamiento con el nombre '{nuevo_nombre}'"}), 400

                    cambios.append(f"Nombre: {f.nombre} -> {nuevo_nombre}")
                f.nombre = nuevo_nombre

            if 'descripcion' in data: f.descripcion = data['descripcion']
            if 'ciudad_id' in data: f.ciudad_id = int(data['ciudad_id']) if data['ciudad_id'] else None
            if 'comision_propietario' in data: f.comision_propietario = data['comision_propietario']
            if 'comision_inmobiliaria' in data: f.comision_inmobiliaria = data['comision_inmobiliaria']
            if 'geojson' in data: 
                f.geojson = data['geojson']
                cambios.append("Se actualizó el mapa/polígono")

            db.session.commit()
            if cambios:
                registrar_auditoria("EDITAR", "Fraccionamiento", f"Editado {f.nombre}: {', '.join(cambios)}")
            return jsonify({"ok": True})
        except Exception as e:
            db.session.rollback()
            return jsonify({"error": str(e)}), 500

    if request.method == "DELETE":
        if f.lotes:
            return jsonify({"error": "No se puede eliminar, tiene lotes asociados"}), 400
        nombre = f.nombre
        db.session.delete(f)
        db.session.commit()
        registrar_auditoria("ELIMINAR", "Fraccionamiento", f"Eliminado: {nombre}")
        return jsonify({"ok": True})

@bp.route("/api/admin/lotes", methods=["POST"])
@login_required
def api_admin_lotes_crear():
    data = request.json
    # Verificar si ya existe el lote en ese fraccionamiento y manzana
    lote_existente = Lote.query.filter_by(
        fraccionamiento_id=data['fraccionamiento_id'],
        manzana=data['manzana'],
        numero_lote=data['numero_lote'],
        activo=True
    ).first()
    
    if lote_existente:
        return jsonify({"error": f"El Lote {data['numero_lote']} de la Manzana {data['manzana']} ya existe en este fraccionamiento."}), 400
    try:
        nuevo = Lote(
            numero_lote=data['numero_lote'],
            manzana=data['manzana'],
            precio=data['precio'],
            metros_cuadrados=data['metros_cuadrados'],
            estado=data.get('estado', 'disponible'),
            fraccionamiento_id=data['fraccionamiento_id'],
            geojson=data['geojson'],
            activo=True
        )
        db.session.add(nuevo)
        db.session.commit()
        registrar_auditoria("CREAR", "Lote", f"Creado Lote {nuevo.numero_lote} Mz {nuevo.manzana} en Fracc ID {nuevo.fraccionamiento_id}")
        return jsonify({"ok": True, "id": nuevo.id})
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

@bp.route("/api/admin/lotes/<int:id>", methods=["PATCH", "DELETE"])
@login_required
def api_admin_lotes_detalle(id):
    lote = Lote.query.get_or_404(id)
    
    if request.method == "PATCH":
        data = request.json
        cambios = []
        try:
            if 'precio' in data and float(data['precio']) != float(lote.precio):
                cambios.append(f"Precio: {lote.precio} -> {data['precio']}")
                lote.precio = data['precio']
            
            if 'estado' in data and data['estado'] != lote.estado:
                cambios.append(f"Estado: {lote.estado} -> {data['estado']}")
                lote.estado = data['estado']
            
            if 'metros_cuadrados' in data: lote.metros_cuadrados = data['metros_cuadrados']
            if 'numero_lote' in data: lote.numero_lote = data['numero_lote']
            if 'manzana' in data: lote.manzana = data['manzana']
            if 'geojson' in data: lote.geojson = data['geojson']

            db.session.commit()
            if cambios:
                registrar_auditoria("EDITAR", "Lote", f"Lote {lote.numero_lote} (Mz {lote.manzana}): {', '.join(cambios)}")
            return jsonify({"ok": True})
        except Exception as e:
            db.session.rollback()
            return jsonify({"error": str(e)}), 500

    if request.method == "DELETE":
        # Baja lógica
        try:
            lote.activo = False
            db.session.commit()
            registrar_auditoria("ELIMINAR", "Lote", f"Eliminado Lote {lote.numero_lote} Mz {lote.manzana}")
            return jsonify({"ok": True})
        except Exception as e:
            return jsonify({"error": str(e)}), 500

# ==========================================
# API CONTRATOS (CRUD)
# ==========================================

@bp.route("/api/admin/contratos", methods=["GET", "POST"])
@login_required
def api_contratos():
    # --- GET: LISTADO DE CONTRATOS ---
    if request.method == "GET":
        try:
            query = Contrato.query.join(Cliente).join(Lote).join(Fraccionamiento)
            q = request.args.get('q', '')
            if q:
                search = f"%{q}%"
                query = query.filter(or_(
                    Cliente.nombre.ilike(search), Cliente.apellido.ilike(search),
                    Cliente.documento.ilike(search), Contrato.numero_contrato.ilike(search),
                    Lote.numero_lote.ilike(search)
                ))
            
            estado = request.args.get('estado')
            if estado and estado != 'todos':
                query = query.filter(Contrato.estado == estado)

            contratos = query.order_by(Contrato.fecha_contrato.desc()).all()
            return jsonify([c.to_dict() for c in contratos])
        except Exception as e:
            print(f"Error listando contratos: {str(e)}")
            return jsonify({"error": "Error al cargar la lista"}), 500

    # --- POST: CREAR NUEVO CONTRATO ---
    if request.method == "POST":
        try:
            # 1. Obtener datos con seguridad
            d = request.get_json(force=True)
            print("Datos recibidos:", d) # Esto aparecerá en tu consola para depurar

            # 2. Validaciones básicas
            if not d.get("cliente_id"):
                return jsonify({"error": "El Cliente es obligatorio"}), 400
            if not d.get("lote_id"):
                return jsonify({"error": "El Lote es obligatorio"}), 400
            if not d.get("numero_contrato"):
                return jsonify({"error": "El Nro de Contrato es obligatorio"}), 400

            # 3. Validar duplicados
            if Contrato.query.filter_by(numero_contrato=d["numero_contrato"]).first(): 
                return jsonify({"error": "El número de contrato ya existe"}), 400
            
            # 4. Validar estado del lote
            lote = Lote.query.get(d["lote_id"])
            if not lote: return jsonify({"error": "Lote no encontrado"}), 404
            
            # Permitimos vender si está disponible o reservado
            if lote.estado not in ['disponible', 'reservado']:
                return jsonify({"error": f"El lote no se puede vender, está: {lote.estado}"}), 400

            # 5. Convertir Fechas (Manejo seguro)
            try:
                fecha_con = datetime.strptime(d["fecha_contrato"], "%Y-%m-%d").date()
            except ValueError:
                return jsonify({"error": "Formato de fecha de contrato inválido"}), 400

            fecha_venc_entrega = None
            if d.get("fecha_vencimiento_entrega"):
                try:
                    fecha_venc_entrega = datetime.strptime(d["fecha_vencimiento_entrega"], "%Y-%m-%d").date()
                except:
                    pass # Si falla, se deja null

            # 6. Convertir Números (Manejo seguro)
            # El JS ya debería mandar números limpios, pero aseguramos en el backend
            try:
                val_total = float(d.get("valor_total", 0))
                val_cuota = float(d.get("valor_cuota", 0))
                val_inicial = float(d.get("cuota_inicial", 0))
                cant_cuotas = int(d.get("cantidad_cuotas", 1))
                cliente_id_int = int(d["cliente_id"])
                vendedor_id_int = int(d["vendedor_id"]) if d.get("vendedor_id") else None
            except ValueError as ve:
                print("Error de conversión numérica:", ve)
                return jsonify({"error": "Error en los montos o IDs numéricos"}), 400

            # 7. Crear el Objeto Contrato
            c = Contrato(
                numero_contrato=d["numero_contrato"],
                cliente_id=cliente_id_int,
                lote_id=lote.id,
                vendedor_id=vendedor_id_int,
                fecha_contrato=fecha_con,
                valor_total=val_total,
                cuota_inicial=val_inicial,
                fecha_vencimiento_entrega=fecha_venc_entrega,
                cantidad_cuotas=cant_cuotas,
                valor_cuota=val_cuota,
                tipo_contrato=d.get("tipo_contrato", "venta"),
                uso=d.get("uso"),
                moneda=d.get("moneda"),
                medida_tiempo=d.get("medida_tiempo"),
                doc_modelo_contrato=d.get("doc_modelo_contrato"),
                doc_comp_interno=d.get("doc_comp_interno"),
                doc_identidad=d.get("doc_identidad"),
                doc_factura_servicios=d.get("doc_factura_servicios"),
                doc_ingresos=d.get("doc_ingresos"),
                observaciones=d.get("observaciones"),
                estado='activo'
            )
            db.session.add(c)
            db.session.flush() # Genera el ID del contrato sin confirmar todavía

            # 8. Generar Cuotas
            # Si vienen generadas desde el JS (tabla)
            if 'cuotas_generadas' in d and d['cuotas_generadas']:
                for item in d['cuotas_generadas']:
                     # Limpieza extra del monto por si acaso viene con puntos
                     monto_limpio = str(item['monto']).replace('.', '').replace(',', '.')
                     
                     # Conversión de fecha DD/MM/YYYY a YYYY-MM-DD
                     try:
                         fecha_venc = datetime.strptime(item['vencimiento'], "%d/%m/%Y").date()
                     except:
                         # Fallback de emergencia
                         fecha_venc = fecha_con + timedelta(days=30 * int(item['numero']))

                     cuota = Cuota(
                        contrato_id=c.id,
                        numero_cuota=int(item['numero']),
                        fecha_vencimiento=fecha_venc,
                        valor_cuota=float(monto_limpio),
                        estado='pendiente',
                        tipo='cuota'
                    )
                     db.session.add(cuota)
            else:
                # Si no hay tabla, generarlas matemáticamente (Respaldo)
                for i in range(1, cant_cuotas + 1):
                    vencimiento = fecha_con + relativedelta(months=i-1)
                    cuota = Cuota(
                        contrato_id=c.id,
                        numero_cuota=i,
                        fecha_vencimiento=vencimiento,
                        valor_cuota=val_cuota,
                        estado='pendiente',
                        tipo='cuota'
                    )
                    db.session.add(cuota)

            # 9. Actualizar estado del lote
            lote.estado = "vendido" if c.tipo_contrato == "venta" else "reservado"
            
            db.session.commit()
            registrar_auditoria("CREAR", "Contrato", f"Nuevo contrato {c.numero_contrato} (Cliente ID {c.cliente_id})")
            return jsonify({"ok": True, "id": c.id}), 201

        except Exception as e:
            db.session.rollback()
            import traceback
            traceback.print_exc() # Esto imprimirá el error real en tu consola negra (servidor)
            return jsonify({"error": f"Error interno: {str(e)}"}), 500

@bp.route("/api/admin/contratos/<int:id>", methods=["GET", "PATCH"])
@login_required
def api_contrato_detalle(id):
    c = Contrato.query.get_or_404(id)
    if request.method == "GET": return jsonify(c.to_dict())

    if request.method == "PATCH":
        d = request.get_json()
        cambios = []
        if 'observaciones' in d: c.observaciones = d['observaciones']
        if 'numero_contrato' in d and d['numero_contrato'] != c.numero_contrato:
            cambios.append(f"N° Contrato: {c.numero_contrato} -> {d['numero_contrato']}")
            c.numero_contrato = d['numero_contrato']
        
        # Cambio de Estado
        if 'estado' in d and d['estado'] != c.estado:
            viejo = c.estado
            nuevo = d['estado']
            c.estado = nuevo
            cambios.append(f"Estado {viejo} -> {nuevo}")
            
            if nuevo == 'rescindido':
                c.lote.estado = 'disponible'
                Cuota.query.filter(Cuota.contrato_id == c.id, Cuota.estado != 'pagada').delete()
                cambios.append("Lote liberado y deuda eliminada")

        db.session.commit()
        if cambios: registrar_auditoria("EDITAR", "Contrato", f"ID {c.id}: {'; '.join(cambios)}")
        return jsonify({"ok": True})

# --- GENERACIÓN DE PDF ---

@bp.route("/admin/inventario/contrato_pdf/<int:contrato_id>")
@login_required
def generar_contrato_pdf(contrato_id):
    c = Contrato.query.get_or_404(contrato_id)
    
    # Datos Generales
    empresa = get_param('EMPRESA_NOMBRE', 'INMOBILIARIA VON KNOBLOCH')
    ciudad_empresa = get_param('EMPRESA_CIUDAD', 'Encarnación')
    
    # Datos Cliente
    cliente_nombre = f"{c.cliente.nombre} {c.cliente.apellido}"
    cliente_doc = c.cliente.documento
    cliente_dir = c.cliente.direccion or "Asunción, Paraguay"
    
    # Datos Lote
    lote_nro = c.lote.numero_lote
    manzana = c.lote.manzana
    fraccionamiento = c.lote.fraccionamiento.nombre
    ciudad_lote = c.lote.fraccionamiento.ciudad.nombre if c.lote.fraccionamiento.ciudad else "N/A"
    superficie = c.lote.metros_cuadrados
    
    # Datos Financieros
    moneda = "Gs." if c.moneda == 'GS' else "USD"
    total_fmt = f"{moneda} {int(c.valor_total):,}".replace(',', '.')
    entrega_fmt = f"{moneda} {int(c.cuota_inicial):,}".replace(',', '.')
    cuota_fmt = f"{moneda} {int(c.valor_cuota):,}".replace(',', '.')
    saldo = float(c.valor_total) - float(c.cuota_inicial)
    saldo_fmt = f"{moneda} {int(saldo):,}".replace(',', '.')
    
    # Convertir a letras
    try:
        total_letras = num2words(c.valor_total, lang='es').upper()
    except:
        total_letras = "......................."

    # Configuración PDF
    pdf = FPDF()
    pdf.add_page()
    pdf.set_margins(25, 25, 25)
    
    # Encabezado
    pdf.set_font('Arial', 'B', 14)
    pdf.cell(0, 10, clean("CONTRATO PRIVADO DE COMPRA-VENTA"), 0, 1, 'C')
    pdf.ln(10)
    
    # Cuerpo del Contrato
    pdf.set_font('Arial', '', 11)
    
    texto_intro = f"""En la ciudad de {clean(ciudad_empresa)}, República del Paraguay, a los {c.fecha_contrato.day} días del mes de {c.fecha_contrato.month} del año {c.fecha_contrato.year}, se reúnen para celebrar el presente contrato:

POR UNA PARTE: La firma {clean(empresa)}, en adelante denominada "LA VENDEDORA".

Y POR OTRA PARTE: El/La Sr./Sra. {clean(cliente_nombre)}, con Documento de Identidad N° {cliente_doc}, domiciliado en {clean(cliente_dir)}, en adelante denominado "EL COMPRADOR".

Ambas partes convienen en celebrar el presente CONTRATO DE COMPRA-VENTA DE INMUEBLE, sujeto a las siguientes cláusulas y condiciones:
"""
    pdf.multi_cell(0, 6, texto_intro)
    pdf.ln(5)
    
    texto_clausulas = f"""PRIMERA - OBJETO: LA VENDEDORA da en venta a EL COMPRADOR un lote de terreno individualizado como Lote N° {clean(lote_nro)} de la Manzana {clean(manzana)}, perteneciente al Fraccionamiento denominado "{clean(fraccionamiento)}", situado en el distrito de {clean(ciudad_lote)}, con una superficie de {superficie} m².

SEGUNDA - PRECIO Y FORMA DE PAGO: El precio total de la venta se fija en la suma de {clean(total_fmt)} ({clean(total_letras)}), que EL COMPRADOR se obliga a abonar de la siguiente manera:
a) Una entrega inicial de {clean(entrega_fmt)} a la firma del presente contrato.
b) El saldo de {clean(saldo_fmt)}, pagadero en {c.cantidad_cuotas} cuotas mensuales y consecutivas de {clean(cuota_fmt)} cada una.

TERCERA - VENCIMIENTOS: Las cuotas vencerán el día {c.fecha_contrato.day} de cada mes. La falta de pago de tres (3) cuotas consecutivas o alternadas facultará a LA VENDEDORA a rescindir el presente contrato de pleno derecho, sin necesidad de interpelación judicial o extrajudicial alguna.

CUARTA - USO: El inmueble objeto de este contrato será destinado exclusivamente para uso {clean(c.uso or 'VIVIENDA')}, obligándose EL COMPRADOR a respetar las normas municipales vigentes.

QUINTA - JURISDICCIÓN: Para todos los efectos legales derivados de este contrato, las partes se someten a la jurisdicción de los Tribunales de la ciudad de {clean(ciudad_empresa)}, renunciando a cualquier otro fuero que pudiera corresponderles.

En prueba de conformidad, se firman dos ejemplares de un mismo tenor y a un solo efecto, en el lugar y fecha indicados al principio.
"""
    pdf.multi_cell(0, 6, texto_clausulas)
    
    pdf.ln(30)
    
    # Firmas
    y = pdf.get_y()
    
    pdf.line(30, y, 90, y)
    pdf.text(45, y + 5, "LA VENDEDORA")
    
    pdf.line(120, y, 180, y)
    pdf.text(135, y + 5, "EL COMPRADOR")
    
    # Anexo: Tabla de Cuotas
    pdf.add_page()
    pdf.set_font('Arial', 'B', 12)
    pdf.cell(0, 10, "ANEXO: PLAN DE PAGOS", 0, 1, 'C')
    pdf.ln(5)
    
    pdf.set_font('Arial', 'B', 10)
    pdf.set_fill_color(230, 230, 230)
    pdf.cell(30, 8, "Nro Cuota", 1, 0, 'C', True)
    pdf.cell(50, 8, "Vencimiento", 1, 0, 'C', True)
    pdf.cell(50, 8, "Monto", 1, 1, 'C', True)
    pdf.ln()
    
    pdf.set_font('Arial', '', 10)
    for cuota in c.cuotas:
        pdf.cell(30, 7, str(cuota.numero_cuota), 1, 0, 'C')
        pdf.cell(50, 7, cuota.fecha_vencimiento.strftime("%d/%m/%Y"), 1, 0, 'C')
        pdf.cell(50, 7, f"{int(cuota.valor_cuota):,}".replace(',', '.'), 1, 1, 'R')
        pdf.ln()

    return Response(pdf.output(dest='S').encode('latin-1'), mimetype="application/pdf", headers={'Content-Disposition':f'inline;filename=Contrato_{c.numero_contrato}.pdf'})

# --- APIS AUXILIARES (LOTES Y FRACCIONAMIENTOS) ---

@bp.route("/api/admin/fraccionamientos/<int:fid>/lotes-disponibles")
@login_required
def api_lotes_disponibles_frac(fid):
    # Usado por el formulario de nuevo contrato
    lotes = Lote.query.filter(
        Lote.fraccionamiento_id == fid,
        Lote.estado.in_(["disponible", "reservado"]),
        Lote.activo == True
    ).all()
    return jsonify([{"id": l.id, "texto": f"M{l.manzana} L{l.numero_lote} - Gs. {int(l.precio):,}", "precio": float(l.precio)} for l in lotes])

@bp.route("/api/admin/lotes/<int:lote_id>/precios", methods=["GET", "POST"])
@login_required
def api_lista_precios_lote(lote_id):
    if request.method == "GET":
        precios = ListaPrecioLote.query.filter_by(lote_id=lote_id).all()
        return jsonify([p.to_dict() for p in precios])
    
    if request.method == "POST":
        d = request.json
        p = ListaPrecioLote(
            lote_id=lote_id,
            condicion_pago_id=d['condicion_pago_id'],
            cantidad_cuotas=d['cantidad_cuotas'],
            precio_cuota=d['precio_cuota'],
            precio_total=d['precio_total']
        )
        db.session.add(p)
        db.session.commit()
        registrar_auditoria("CREAR", "ListaPrecioLote", f"Plan de pago agregado a lote ID {lote_id}")
        return jsonify({"ok": True})

@bp.route("/api/admin/lista-precios/<int:id>", methods=["DELETE"])
@login_required
def api_eliminar_precio_lote(id):
    p = ListaPrecioLote.query.get_or_404(id)
    db.session.delete(p)
    db.session.commit()
    registrar_auditoria("ELIMINAR", "ListaPrecioLote", f"Plan de pago eliminado ID {id}")
    return jsonify({"ok": True})

# --- NUEVA API PARA BÚSQUEDA SIMPLE DE CLIENTES (SIN SELECT2) ---
@bp.route("/api/inventario/clientes/buscar_simple")
@login_required
def buscar_clientes_simple():
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
        doc = c.documento or "S/D"
        data.append({
            'id': c.id,
            'texto': f"{nombre_completo} - {doc}"
        })
    
    return jsonify(data)