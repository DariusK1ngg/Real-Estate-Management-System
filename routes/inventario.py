from flask import Blueprint, render_template, request, jsonify, Response
from flask_login import login_required
from extensions import db
from models import Fraccionamiento, Lote, ListaPrecioLote, CondicionPago, Contrato, Cuota
from datetime import datetime, timedelta, date
from utils import role_required, admin_required, get_param, clean
from fpdf import FPDF
from num2words import num2words
import locale

bp = Blueprint('inventario', __name__)

@bp.route("/admin/inventario/movimientos")
@login_required
@role_required('Empleado', 'Vendedor')
def inventario_movimientos(): return render_template("inventario/movimientos.html")

@bp.route("/admin/inventario/reportes")
@login_required
@role_required('Empleado', 'Vendedor')
def inventario_reportes(): return render_template("inventario/reportes.html")

@bp.route("/admin/inventario/definiciones")
@login_required
@role_required('Admin', 'Empleado', 'Vendedor')
def inventario_definiciones(): return render_template("inventario/definiciones_fraccionamientos.html")

@bp.route("/admin/inventario/fraccionamientos/<int:fraccionamiento_id>")
@login_required
@role_required('Admin', 'Empleado', 'Vendedor')
def inventario_fraccionamiento_detalle(fraccionamiento_id):
    fraccionamiento = Fraccionamiento.query.get_or_404(fraccionamiento_id)
    return render_template("inventario/fraccionamiento_detalle.html", fraccionamiento=fraccionamiento)

@bp.route("/api/fraccionamientos", methods=["GET"])
def api_fraccionamientos_geojson_list(): 
    fracs = Fraccionamiento.query.all()
    return jsonify({"type": "FeatureCollection", "features": [f.to_feature() for f in fracs]})

@bp.route("/api/fraccionamientos/<int:fid>/lotes", methods=["GET"])
def api_lotes_by_frac(fid): 
    lotes = Lote.query.filter_by(fraccionamiento_id=fid).all()
    return jsonify({"type": "FeatureCollection", "features": [l.to_feature() for l in lotes]})
    
@bp.route("/api/lotes", methods=["GET"])
def api_lotes_all():
    lotes = Lote.query.all()
    return jsonify({"type": "FeatureCollection", "features": [l.to_feature() for l in lotes]})

@bp.route("/api/admin/fraccionamientos", methods=["GET"])
@login_required
def api_fraccionamientos_lista():
    search = request.args.get('q', '')
    query = Fraccionamiento.query
    if search: query = query.filter(Fraccionamiento.nombre.ilike(f'%{search}%'))
    return jsonify([f.to_dict() for f in query.order_by(Fraccionamiento.nombre).all()])

@bp.route("/api/admin/fraccionamientos/<int:fid>/detalle", methods=["GET"])
@login_required
def api_fraccionamiento_detalle_completo(fid):
    frac = Fraccionamiento.query.get_or_404(fid)
    lotes = Lote.query.filter_by(fraccionamiento_id=fid).order_by(Lote.manzana, Lote.numero_lote).all()
    data = frac.to_dict()
    data['lotes'] = [l.to_feature()['properties'] for l in lotes]
    return jsonify(data)

@bp.route("/api/admin/fraccionamientos", methods=["POST"])
@login_required
@admin_required
def api_admin_crear_fraccionamiento():
    data = request.get_json(force=True)
    if not data.get('nombre') or not data.get('geojson'): return jsonify({"error": "Datos incompletos"}), 400
    f = Fraccionamiento(nombre=data["nombre"], descripcion=data.get("descripcion", ""), geojson=data["geojson"], ciudad_id=data.get("ciudad_id"))
    db.session.add(f); db.session.commit()
    return jsonify({"ok": True, "id": f.id}), 201

@bp.route("/api/admin/fraccionamientos/<int:fid>", methods=["PATCH", "DELETE"])
@login_required
@admin_required
def api_admin_fraccionamientos_gestion(fid):
    f = Fraccionamiento.query.get_or_404(fid)
    if request.method == "DELETE":
        if f.lotes: return jsonify({"error": "Tiene lotes asociados"}), 400
        db.session.delete(f); db.session.commit()
        return jsonify({"message": "Eliminado"})
    if request.method == "PATCH":
        d = request.get_json(force=True)
        f.nombre = d.get("nombre", f.nombre)
        f.descripcion = d.get("descripcion", f.descripcion)
        f.comision_inmobiliaria = d.get("comision_inmobiliaria", f.comision_inmobiliaria)
        f.comision_propietario = d.get("comision_propietario", f.comision_propietario)
        if 'ciudad_id' in d: f.ciudad_id = int(d['ciudad_id']) if d['ciudad_id'] else None
        db.session.commit()
        return jsonify(f.to_dict())

@bp.route("/api/admin/lotes", methods=["POST"])
@login_required
@admin_required
def api_admin_create_lote(): 
    d = request.get_json(force=True)
    l = Lote(numero_lote=str(d["numero_lote"]), manzana=str(d["manzana"]), precio=float(d["precio"]), metros_cuadrados=int(d["metros_cuadrados"]), estado=str(d["estado"]), geojson=d["geojson"], fraccionamiento_id=int(d["fraccionamiento_id"]))
    db.session.add(l); db.session.commit()
    return jsonify({"ok": True, "id": l.id})

@bp.route("/api/admin/lotes/<int:lid>", methods=["PATCH", "DELETE"])
@login_required
@admin_required
def api_admin_update_delete_lote(lid):
    l = Lote.query.get_or_404(lid)
    if request.method == "DELETE":
        if l.contratos: return jsonify({"error": "Lote con contratos"}), 400
        db.session.delete(l); db.session.commit(); return jsonify({"ok": True})
    if request.method == "PATCH":
        d = request.get_json(force=True)
        l.manzana = d.get("manzana", l.manzana)
        l.numero_lote = d.get("numero_lote", l.numero_lote)
        l.precio = d.get("precio", l.precio)
        l.metros_cuadrados = d.get("metros_cuadrados", l.metros_cuadrados)
        l.estado = d.get("estado", l.estado)
        if "geojson" in d: l.geojson = d["geojson"]
        db.session.commit(); return jsonify({"ok": True})

@bp.route("/api/admin/lotes/<int:lote_id>/precios", methods=["GET", "POST"])
@login_required
@role_required('Admin', 'Empleado')
def api_lista_precios_lote(lote_id):
    lote = Lote.query.get_or_404(lote_id)
    if request.method == "POST":
        d = request.json
        np = ListaPrecioLote(lote_id=lote_id, condicion_pago_id=d['condicion_pago_id'], cantidad_cuotas=d['cantidad_cuotas'], precio_cuota=d['precio_cuota'], precio_total=d['precio_total'])
        db.session.add(np)
        cp = CondicionPago.query.get(d['condicion_pago_id'])
        if cp and 'contado' in cp.nombre.lower(): lote.precio = d['precio_total']
        if int(d['cantidad_cuotas']) == 130: lote.precio_financiado_130 = d['precio_total']; lote.precio_cuota_130 = d['precio_cuota']
        db.session.commit()
        return jsonify(np.to_dict()), 201
    return jsonify([p.to_dict() for p in ListaPrecioLote.query.filter_by(lote_id=lote_id).all()])

@bp.route("/api/admin/lista-precios/<int:pid>", methods=["DELETE"])
@login_required
def api_delete_lista_precio(pid):
    p = ListaPrecioLote.query.get_or_404(pid)
    db.session.delete(p); db.session.commit(); return jsonify({"message": "Eliminado"})

@bp.route("/api/admin/contratos", methods=["GET", "POST"])
@login_required
def api_contratos():
    if request.method == "POST":
        d = request.get_json(force=True)
        if Contrato.query.filter_by(numero_contrato=d["numero_contrato"]).first(): return jsonify({"error": "Contrato duplicado"}), 400
        lote = Lote.query.get(d["lote_id"])
        if not lote: return jsonify({"error": "Lote inexistente"}), 404
        
        valor_total = float(d.get("valor_total", 0))
        cantidad_cuotas = int(d.get("cantidad_cuotas", 0))
        valor_cuota = float(d.get("valor_cuota", 0))
        
        if 'precio_id' in d and d['precio_id']:
            plan = ListaPrecioLote.query.get(d['precio_id'])
            if plan:
                valor_total = float(plan.precio_total)
                cantidad_cuotas = plan.cantidad_cuotas
                valor_cuota = float(plan.precio_cuota)

        if cantidad_cuotas > 0 and valor_cuota == 0: valor_cuota = valor_total / cantidad_cuotas

        c = Contrato(
            numero_contrato=d["numero_contrato"], cliente_id=d["cliente_id"], lote_id=d["lote_id"],
            fecha_contrato=datetime.strptime(d["fecha_contrato"], "%Y-%m-%d").date(),
            valor_total=valor_total, cuota_inicial=float(d.get("cuota_inicial", 0)),
            cantidad_cuotas=cantidad_cuotas, valor_cuota=valor_cuota,
            tipo_contrato=d.get("tipo_contrato", "venta"), observaciones=d.get("observaciones")
        )
        db.session.add(c); db.session.commit()

        for i in range(1, c.cantidad_cuotas + 1):
            venc = c.fecha_contrato + timedelta(days=30*i)
            db.session.add(Cuota(contrato_id=c.id, numero_cuota=i, fecha_vencimiento=venc, valor_cuota=c.valor_cuota))
            
        lote.estado = "vendido" if c.tipo_contrato == "venta" else "reservado"
        db.session.commit()
        return jsonify({"ok": True, "id": c.id}), 201

    return jsonify([c.to_dict() for c in Contrato.query.order_by(Contrato.fecha_contrato.desc()).all()])

@bp.route("/api/admin/contratos/<int:cid>", methods=["GET", "PATCH"])
@login_required
def api_contrato_detalle(cid):
    c = Contrato.query.get_or_404(cid)
    if request.method == "PATCH":
        d = request.get_json(force=True)
        if 'numero_contrato' in d: c.numero_contrato = d['numero_contrato']
        if 'estado' in d: c.estado = d['estado']
        c.observaciones = d.get('observaciones', c.observaciones)
        db.session.commit()
        return jsonify({"ok": True})
    return jsonify(c.to_dict())

@bp.route("/admin/inventario/contrato_pdf/<int:contrato_id>")
@login_required
def generar_contrato_pdf(contrato_id):
    contrato = Contrato.query.get_or_404(contrato_id)
    cliente = contrato.cliente
    lote = contrato.lote
    
    empresa_nombre = get_param('EMPRESA_NOMBRE', 'INMOBILIARIA TU HOGAR S.A.')
    try: valor_letras = num2words(int(contrato.valor_total), lang='es').upper()
    except: valor_letras = str(int(contrato.valor_total))

    class PDF(FPDF):
        def header(self):
            self.set_font('Helvetica', 'B', 14); self.cell(0, 10, clean('CONTRATO DE COMPRA-VENTA'), 0, 1, 'C'); self.ln(5)
    
    pdf = PDF(); pdf.add_page(); pdf.set_font('Helvetica', '', 10)
    
    txt = f"En la fecha {contrato.fecha_contrato}, entre {empresa_nombre} y {cliente.nombre} {cliente.apellido} con CI {cliente.documento}, acuerdan la venta del Lote {lote.numero_lote} Manzana {lote.manzana} por Gs. {int(contrato.valor_total):,} ({valor_letras})."
    pdf.multi_cell(0, 5, clean(txt))
    
    return Response(pdf.output(dest='S').encode('latin-1'), mimetype="application/pdf")