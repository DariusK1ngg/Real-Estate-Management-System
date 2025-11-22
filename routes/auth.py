from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required, current_user
from models import Funcionario, Lote, Cliente, Contrato
from utils import role_required # Importante para admin_mapa

bp = Blueprint('auth', __name__)

@bp.route("/")
def index():
    return render_template("index.html")

@bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated: 
        return redirect(url_for('auth.admin_dashboard'))
    
    if request.method == "POST":
        user = Funcionario.query.filter_by(usuario=request.form.get("username")).first()
        if user and user.check_password(request.form.get("password")):
            if user.estado == 'activo':
                login_user(user)
                return redirect(request.args.get('next') or url_for('auth.admin_dashboard'))
            else: 
                flash("Este usuario está inactivo.", "warning")
        else: 
            flash("Usuario o contraseña incorrectos.", "danger")
            
    return render_template("login.html")

@bp.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("auth.index"))

@bp.route("/admin/dashboard")
@login_required
def admin_dashboard():
    stats = {
        "total_lotes": Lote.query.count(), 
        "disponibles": Lote.query.filter_by(estado="disponible").count(),
        "reservados": Lote.query.filter_by(estado="reservado").count(), 
        "vendidos": Lote.query.filter_by(estado="vendido").count(),
        "total_clientes": Cliente.query.count(), 
        "contratos_activos": Contrato.query.filter_by(estado="activo").count()
    }
    return render_template("dashboard.html", **stats)

@bp.route("/admin")
@login_required
def admin(): 
    return redirect(url_for("auth.admin_dashboard"))

@bp.route("/admin/mapa")
@login_required
@role_required('Empleado', 'Vendedor')
def admin_mapa(): 
    return render_template("admin.html")