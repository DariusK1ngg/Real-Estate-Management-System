import os
from flask import Flask, render_template
from extensions import db, bcrypt, login_manager
from models import Funcionario, Role, Cargo, Aplicacion
from dotenv import load_dotenv
from datetime import date
import click

# Importar Blueprints
from routes import auth, base, rrhh, tesoreria, gastos, ventas, inventario, cobros, reportes

load_dotenv()

app = Flask(__name__, template_folder='templates', static_folder='static', static_url_path='/static')
app.secret_key = os.getenv("SECRET_KEY", "inmobiliaria_yeizon")
app.config["SQLALCHEMY_DATABASE_URI"] = f"mysql+pymysql://{os.getenv('DB_USER')}:{os.getenv('DB_PASS')}@{os.getenv('DB_HOST')}/{os.getenv('DB_NAME')}"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# Inicializar Extensiones
db.init_app(app)
bcrypt.init_app(app)
login_manager.init_app(app)

@login_manager.user_loader
def load_user(user_id):
    return Funcionario.query.get(int(user_id))

# Registrar Blueprints
app.register_blueprint(auth.bp)
app.register_blueprint(base.bp)
app.register_blueprint(rrhh.bp)
app.register_blueprint(tesoreria.bp)
app.register_blueprint(gastos.bp)
app.register_blueprint(ventas.bp)
app.register_blueprint(inventario.bp)
app.register_blueprint(cobros.bp)
app.register_blueprint(reportes.bp)

# Manejo de Errores
@app.errorhandler(404)
def not_found(error): return render_template('errors/404.html'), 404

@app.errorhandler(500)
def internal_error(error): return render_template('errors/500.html'), 500

# Comandos CLI
@app.cli.command("init-db")
def init_db_command():
    db.create_all()
    print("Base de datos inicializada.")

@app.cli.command("create-admin")
@click.argument("usuario")
@click.argument("password")
def create_admin(usuario, password):
    # Lógica simplificada para crear admin rápido
    rol = Role.query.filter_by(name='Admin').first()
    if not rol: rol = Role(name='Admin'); db.session.add(rol)
    cargo = Cargo.query.filter_by(nombre='Administrador').first()
    if not cargo: cargo = Cargo(nombre='Administrador'); db.session.add(cargo)
    db.session.commit()
    
    u = Funcionario(nombre='Admin', apellido='System', documento='000', usuario=usuario, cargo_id=cargo.id, fecha_ingreso=date.today(), estado='activo')
    u.set_password(password)
    u.roles.append(rol)
    db.session.add(u); db.session.commit()
    print(f"Admin {usuario} creado.")

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True, host='0.0.0.0', port=5000)