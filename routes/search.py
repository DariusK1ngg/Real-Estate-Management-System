from flask import Blueprint, request, jsonify
from flask_login import login_required
from models import Cliente, Lote, Contrato
from sqlalchemy import or_

bp = Blueprint('search', __name__)

@bp.route("/api/global-search")
@login_required
def global_search():
    query = request.args.get("q", "").strip()
    if not query or len(query) < 2:
        return jsonify([])

    search_term = f"%{query}%"
    results = []

    # 1. Buscar Clientes
    clientes = Cliente.query.filter(
        Cliente.activo == True,
        or_(
            Cliente.nombre.ilike(search_term),
            Cliente.apellido.ilike(search_term),
            Cliente.documento.ilike(search_term)
        )
    ).limit(5).all()

    for c in clientes:
        results.append({
            "category": "Clientes",
            "title": f"{c.nombre} {c.apellido}",
            "subtitle": f"CI: {c.documento}",
            "url": "#", # Aquí podrías redirigir a un perfil si tuvieras
            "icon": "fas fa-user"
        })

    # 2. Buscar Lotes
    lotes = Lote.query.filter(
        Lote.activo == True,
        or_(
            Lote.numero_lote.ilike(search_term),
            Lote.manzana.ilike(search_term)
        )
    ).limit(5).all()

    for l in lotes:
        estado_icon = "fa-check-circle" if l.estado == 'disponible' else "fa-ban"
        results.append({
            "category": "Lotes",
            "title": f"Lote {l.numero_lote} - Manzana {l.manzana}",
            "subtitle": f"{l.fraccionamiento.nombre} ({l.estado})",
            "url": "#", # Podrías redirigir al mapa
            "icon": f"fas {estado_icon}"
        })

    # 3. Buscar Contratos
    contratos = Contrato.query.filter(
        Contrato.numero_contrato.ilike(search_term)
    ).limit(5).all()

    for c in contratos:
        results.append({
            "category": "Contratos",
            "title": f"Contrato N° {c.numero_contrato}",
            "subtitle": f"Cliente: {c.cliente.nombre} {c.cliente.apellido}",
            "url": "#", 
            "icon": "fas fa-file-contract"
        })

    return jsonify(results)