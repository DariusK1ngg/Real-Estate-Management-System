from flask import Blueprint, render_template
from flask_login import login_required
from extensions import db
from models import AuditLog
from utils import admin_required

bp = Blueprint('audit', __name__)

@bp.route("/admin/audit/logs")
@login_required
@admin_required
def audit_logs_view():
    # Obtenemos los últimos 100 eventos de auditoría
    logs = AuditLog.query.order_by(AuditLog.fecha.desc()).limit(100).all()
    return render_template("audit/logs.html", logs=logs)