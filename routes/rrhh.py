from flask import Blueprint, request, jsonify, render_template
from flask_login import login_required, current_user
from extensions import db
from models import Funcionario, Cargo, Role
from datetime import date, datetime
from utils import admin_required, registrar_auditoria # <--- IMPORTAR

bp = Blueprint('rrhh', __name__)

@bp.route("/admin/rrhh/definiciones")
@login_required
@admin_required
def rrhh_definiciones(): return render_template("rrhh/definiciones.html")

@bp.route("/admin/rrhh/definiciones/funcionarios")
@login_required
@admin_required
def rrhh_definiciones_funcionarios(): return render_template("rrhh/definiciones_funcionarios.html")

@bp.route("/admin/rrhh/definiciones/cargos")
@login_required
@admin_required
def rrhh_definiciones_cargos(): return render_template("rrhh/definiciones_cargos.html")

@bp.route("/api/admin/funcionarios", methods=["GET", "POST"])
@login_required
@admin_required
def api_admin_funcionarios():
    if request.method == "POST":
        data = request.json
        if Funcionario.query.filter_by(usuario=data['usuario']).first(): return jsonify({"error": "El nombre de usuario ya existe."}), 400
        if Funcionario.query.filter_by(documento=data['documento']).first(): return jsonify({"error": "El documento ya está registrado."}), 400
        
        fecha_ingreso_val = date.today()
        if data.get('fecha_ingreso') and data['fecha_ingreso'] != '':
            fecha_ingreso_val = datetime.strptime(data['fecha_ingreso'], "%Y-%m-%d").date()

        nuevo_funcionario = Funcionario(
            nombre=data['nombre'], apellido=data['apellido'], documento=data['documento'], 
            usuario=data['usuario'], cargo_id=data.get('cargo_id'), estado=data.get('estado', 'activo'),
            es_vendedor=data.get('es_vendedor', False), fecha_ingreso=fecha_ingreso_val
        )
        
        if data.get('password'): 
            nuevo_funcionario.set_password(data['password'])
        
        if data.get('roles_ids'):
            for role_id in data['roles_ids']:
                role = Role.query.get(int(role_id))
                if role:
                    nuevo_funcionario.roles.append(role)

        db.session.add(nuevo_funcionario)
        db.session.commit()
        registrar_auditoria("CREAR", "Funcionario", f"Alta de usuario: {nuevo_funcionario.usuario}") # <--- AUDITORIA
        return jsonify(nuevo_funcionario.to_dict()), 201
    
    funcionarios = Funcionario.query.order_by(Funcionario.nombre).all()
    return jsonify([f.to_dict() for f in funcionarios])

@bp.route("/api/admin/funcionarios/<int:fid>", methods=["GET", "PUT", "DELETE"])
@login_required
@admin_required
def api_admin_funcionario_detalle(fid):
    funcionario = Funcionario.query.get_or_404(fid)
    
    if request.method == "PUT":
        data = request.json
        if 'usuario' in data and data['usuario'] != funcionario.usuario and Funcionario.query.filter_by(usuario=data['usuario']).first():
            return jsonify({"error": "El nombre de usuario ya existe."}), 400
        if 'documento' in data and data['documento'] != funcionario.documento and Funcionario.query.filter_by(documento=data['documento']).first():
            return jsonify({"error": "El documento ya está registrado."}), 400
        
        funcionario.nombre = data.get('nombre', funcionario.nombre)
        funcionario.apellido = data.get('apellido', funcionario.apellido)
        funcionario.documento = data.get('documento', funcionario.documento)
        funcionario.usuario = data.get('usuario', funcionario.usuario)
        funcionario.cargo_id = data.get('cargo_id', funcionario.cargo_id)
        funcionario.estado = data.get('estado', funcionario.estado)
        funcionario.es_vendedor = data.get('es_vendedor', funcionario.es_vendedor)

        if data.get('password') and data['password'] != '':
            funcionario.set_password(data['password'])
        
        if 'roles_ids' in data:
            funcionario.roles = []
            for role_id in data['roles_ids']:
                role = Role.query.get(int(role_id))
                if role:
                    funcionario.roles.append(role)
        
        db.session.commit()
        registrar_auditoria("EDITAR", "Funcionario", f"Modificación de usuario: {funcionario.usuario}") # <--- AUDITORIA
        return jsonify(funcionario.to_dict())

    if request.method == "DELETE":
        if current_user.id == fid: return jsonify({"error": "No te puedes eliminar a ti mismo."}), 400
        target_name = funcionario.usuario
        db.session.delete(funcionario)
        db.session.commit()
        registrar_auditoria("ELIMINAR", "Funcionario", f"Baja de usuario: {target_name}") # <--- AUDITORIA
        return jsonify({"message": "Funcionario eliminado."})

    roles = [r.name for r in funcionario.roles]
    func_dict = funcionario.to_dict()
    func_dict['roles'] = roles
    return jsonify(func_dict)

@bp.route("/api/admin/cargos", methods=["GET", "POST"])
@login_required
@admin_required
def api_admin_cargos():
    if request.method == "POST":
        data = request.json
        if not data or not data.get('nombre'): return jsonify({"error": "El nombre del cargo es requerido."}), 400
        if Cargo.query.filter_by(nombre=data['nombre']).first(): return jsonify({"error": "Ese cargo ya existe."}), 400
        nuevo_cargo = Cargo(nombre=data['nombre'])
        db.session.add(nuevo_cargo); db.session.commit()
        registrar_auditoria("CREAR", "Cargo", f"Nuevo cargo: {nuevo_cargo.nombre}") # <--- AUDITORIA
        return jsonify(nuevo_cargo.to_dict()), 201
    return jsonify([c.to_dict() for c in Cargo.query.order_by(Cargo.nombre).all()])

@bp.route("/api/admin/cargos/<int:cid>", methods=["PUT", "DELETE"])
@login_required
@admin_required
def api_admin_cargo_detalle(cid):
    cargo = Cargo.query.get_or_404(cid)
    if request.method == "PUT":
        data = request.json
        if not data or not data.get('nombre'): return jsonify({"error": "El nombre del cargo es requerido."}), 400
        if Cargo.query.filter(Cargo.id != cid, Cargo.nombre == data['nombre']).first(): return jsonify({"error": "Ese cargo ya existe."}), 400
        cargo.nombre = data['nombre']
        db.session.commit()
        registrar_auditoria("EDITAR", "Cargo", f"Edición de cargo ID {cid}") # <--- AUDITORIA
        return jsonify(cargo.to_dict())
    if request.method == "DELETE":
        if cargo.funcionarios: return jsonify({"error": "No se puede eliminar, está asignado a funcionarios."}), 400
        db.session.delete(cargo)
        db.session.commit()
        registrar_auditoria("ELIMINAR", "Cargo", f"Baja de cargo ID {cid}") # <--- AUDITORIA
        return jsonify({"message": "Cargo eliminado."})