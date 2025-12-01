import os
from flask import Flask, render_template
from extensions import db, bcrypt, login_manager, migrate, csrf
from models import Funcionario, Role, Cargo, Aplicacion
from dotenv import load_dotenv
from datetime import date
import click

# Importar Blueprints
from routes import auth, base, rrhh, tesoreria, gastos, ventas, inventario, cobros, reportes, audit, search

load_dotenv()

app = Flask(__name__, template_folder='templates', static_folder='static', static_url_path='/static')
app.secret_key = os.getenv("SECRET_KEY", "inmobiliaria_yeizon")
app.config["SQLALCHEMY_DATABASE_URI"] = f"mysql+pymysql://{os.getenv('DB_USER')}:{os.getenv('DB_PASS')}@{os.getenv('DB_HOST')}/{os.getenv('DB_NAME')}"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# Inicializar Extensiones
db.init_app(app)
bcrypt.init_app(app)
login_manager.init_app(app)
migrate.init_app(app, db) # Migraciones
csrf.init_app(app)        # Protección CSRF

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
app.register_blueprint(audit.bp)
app.register_blueprint(search.bp)

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

@app.cli.command("cargar-roles")
def cargar_roles_command():
    """Carga los roles iniciales del sistema si no existen."""
    try:
        # Definimos los roles basados en tu archivo datos_base.sql
        roles_data = [
            {'id': 1, 'name': 'Admin', 'description': 'Acceso total al sistema'},
            {'id': 2, 'name': 'Vendedor', 'description': 'Acceso a módulo de ventas, inventario y clientes'},
            {'id': 3, 'name': 'Cajero', 'description': 'Acceso a módulo de cobros, tesorería y arqueos'},
            {'id': 4, 'name': 'Empleado', 'description': 'Acceso de consulta y tareas administrativas básicas'}
        ]

        print("Verificando roles...")
        for r in roles_data:
            # Buscamos si existe por ID o por Nombre
            rol_existente = Role.query.filter((Role.id == r['id']) | (Role.name == r['name'])).first()
            
            if not rol_existente:
                nuevo_rol = Role(id=r['id'], name=r['name'], description=r['description'])
                db.session.add(nuevo_rol)
                print(f" [+] Creando rol: {r['name']}")
            else:
                print(f" [v] El rol {r['name']} ya existe.")
        
        db.session.commit()
        print("--- Carga de roles finalizada ---")
        
    except Exception as e:
        db.session.rollback()
        print(f"Error cargando roles: {e}")

@app.cli.command("sembrar-datos")
def sembrar_datos_command():
    """Carga todos los datos base del sistema usando ORM (Python)."""
    from models import (
        TipoDocumento, TipoCliente, Profesion, FormaPago, Impuesto, 
        CondicionPago, TipoComprobante, Ciudad, Barrio, Cargo, Role, 
        Aplicacion, ParametroSistema, EntidadFinanciera, CategoriaGasto, 
        Proveedor, Funcionario
    )
    from datetime import date
    
    print(">>> Iniciando carga de datos estándar...")

    try:
        # 1. TIPOS DE DOCUMENTO
        datos = [
            (1, 'Cédula de Identidad (CI)'), (2, 'RUC'), 
            (3, 'Pasaporte'), (4, 'Carnet de Extranjería')
        ]
        for _id, nombre in datos:
            if not TipoDocumento.query.get(_id):
                db.session.add(TipoDocumento(id=_id, nombre=nombre))
        print(" [OK] Tipos de Documento")

        # 2. TIPOS DE CLIENTE
        datos = [(1, 'Persona Física'), (2, 'Persona Jurídica'), (3, 'Inversionista')]
        for _id, nombre in datos:
            if not TipoCliente.query.get(_id):
                db.session.add(TipoCliente(id=_id, nombre=nombre))
        print(" [OK] Tipos de Cliente")

        # 3. PROFESIONES
        profesiones = [
            (1, 'Comerciante'), (2, 'Empleado Privado'), (3, 'Funcionario Público'),
            (4, 'Abogado/a'), (5, 'Médico/a'), (6, 'Ingeniero/a'), (7, 'Docente'),
            (8, 'Arquitecto/a'), (9, 'Contador/a'), (10, 'Jubilado/a'), 
            (11, 'Estudiante'), (12, 'Empresario/a')
        ]
        for _id, nombre in profesiones:
            if not Profesion.query.get(_id):
                db.session.add(Profesion(id=_id, nombre=nombre))
        print(" [OK] Profesiones")

        # 4. FORMAS DE PAGO
        pagos = [
            (1, 'Efectivo'), (2, 'Transferencia Bancaria'), (3, 'Cheque'),
            (4, 'Tarjeta de Débito'), (5, 'Tarjeta de Crédito')
        ]
        for _id, nombre in pagos:
            if not FormaPago.query.get(_id):
                db.session.add(FormaPago(id=_id, nombre=nombre))
        print(" [OK] Formas de Pago")

        # 5. IMPUESTOS
        impuestos = [(1, 'IVA 10%', 10.00), (2, 'IVA 5%', 5.00), (3, 'Exenta', 0.00)]
        for _id, nombre, porc in impuestos:
            if not Impuesto.query.get(_id):
                db.session.add(Impuesto(id=_id, nombre=nombre, porcentaje=porc))
        print(" [OK] Impuestos")

        # 6. CONDICIONES DE PAGO
        condiciones = [
            (1, 'Contado', 0), (2, 'Crédito 30 días', 30),
            (3, 'Crédito 60 días', 60), (4, 'Financiación Propia (Cuotas)', 0)
        ]
        for _id, nombre, dias in condiciones:
            if not CondicionPago.query.get(_id):
                db.session.add(CondicionPago(id=_id, nombre=nombre, dias=dias))
        print(" [OK] Condiciones de Pago")

        # 7. TIPOS DE COMPROBANTE
        comprobantes = [
            (1, 'Factura'), (2, 'Recibo de Dinero'),
            (3, 'Nota de Crédito'), (4, 'Nota de Presupuesto')
        ]
        for _id, nombre in comprobantes:
            if not TipoComprobante.query.get(_id):
                db.session.add(TipoComprobante(id=_id, nombre=nombre))
        print(" [OK] Tipos de Comprobante")

        # 8. CIUDADES
        ciudades = [
            (1, 'Encarnación'), (2, 'Asunción'), (3, 'Ciudad del Este'),
            (4, 'Cambyretá'), (5, 'Hohenau'), (6, 'Bella Vista'),
            (7, 'San Lorenzo'), (8, 'Luque'), (9, 'Villarrica'), (10, 'Coronel Bogado')
        ]
        for _id, nombre in ciudades:
            if not Ciudad.query.get(_id):
                db.session.add(Ciudad(id=_id, nombre=nombre))
        db.session.commit()
        print(" [OK] Ciudades")

        # 9. BARRIOS
        barrios = [
            (1, 'Centro', 1), (2, 'Barrio San Pedro', 1), (3, 'Barrio San Isidro', 1),
            (4, 'Barrio Pacú Cua', 1), (5, 'Villa Morra', 2), (6, 'Recoleta', 2),
            (7, 'Centro', 4), (8, 'Centro', 5)
        ]
        for _id, nombre, ciudad_id in barrios:
            if not Barrio.query.get(_id):
                db.session.add(Barrio(id=_id, nombre=nombre, ciudad_id=ciudad_id))
        print(" [OK] Barrios")

        # 10. CARGOS
        cargos = [
            (1, 'Administrador General'), (2, 'Gerente de Ventas'), (3, 'Vendedor'),
            (4, 'Cajero'), (5, 'Secretario/a'), (6, 'Cobrador')
        ]
        for _id, nombre in cargos:
            if not Cargo.query.get(_id):
                db.session.add(Cargo(id=_id, nombre=nombre))
        print(" [OK] Cargos")

        # 11. ROLES (CORREGIDO)
        roles = [
            (1, 'Admin', 'Acceso total al sistema'),
            (2, 'Vendedor', 'Acceso a módulo de ventas, inventario y clientes'),
            (3, 'Cajero', 'Acceso a módulo de cobros, tesorería y arqueos'),
            (4, 'Empleado', 'Acceso de consulta y tareas administrativas básicas')
        ]
        for _id, name, desc in roles:
            if not Role.query.get(_id):
                db.session.add(Role(id=_id, name=name, description=desc))
        print(" [OK] Roles")

        # 12. APLICACIONES
        apps = [
            (1, 'Gestión de Usuarios', 'user_manage', 'Seguridad'),
            (2, 'Gestión de Roles', 'role_manage', 'Seguridad'),
            (3, 'Mapa Interactivo', 'map_view', 'Inventario'),
            (4, 'ABM Lotes', 'lote_manage', 'Inventario'),
            (5, 'Cargar Venta', 'sale_create', 'Ventas'),
            (6, 'Registrar Cobro', 'payment_create', 'Cobros'),
            (7, 'Arqueo de Caja', 'cash_audit', 'Tesoreria'),
            (8, 'Reportes Financieros', 'fin_reports', 'Reportes')
        ]
        for _id, nombre, clave, mod in apps:
            if not Aplicacion.query.get(_id):
                db.session.add(Aplicacion(id=_id, nombre=nombre, clave=clave, modulo=mod))
        print(" [OK] Aplicaciones")

        # 13. PARAMETROS DEL SISTEMA
        params = [
            (1, 'EMPRESA_NOMBRE', 'Inmobiliaria Von Knobloch', 'Nombre comercial de la empresa'),
            (2, 'EMPRESA_RUC', '80012345-6', 'RUC de la empresa'),
            (3, 'EMPRESA_DIRECCION', 'Calle Mcal. Estigarribia c/ Tomás R. Pereira', 'Dirección fiscal'),
            (4, 'MONEDA_DEFECTO', 'PYG', 'Moneda predeterminada'),
            (5, 'IVA_DEFECTO', '10', 'Porcentaje de IVA por defecto'),
            (6, 'INTERES_MORA_DIARIO', '0.0275', 'Tasa diaria de interés por atraso (2.75%)')
        ]
        for _id, clave, valor, desc in params:
            if not ParametroSistema.query.get(_id):
                db.session.add(ParametroSistema(id=_id, clave=clave, valor=valor, descripcion=desc))
        print(" [OK] Parámetros")

        # 14. ENTIDADES FINANCIERAS
        bancos = [
            (1, 'Banco Itaú Paraguay'), (2, 'Banco Atlas'), (3, 'Banco Nacional de Fomento (BNF)'),
            (4, 'Banco Continental'), (5, 'Visión Banco'), (6, 'Cooperativa Universitaria')
        ]
        for _id, nombre in bancos:
            if not EntidadFinanciera.query.get(_id):
                db.session.add(EntidadFinanciera(id=_id, nombre=nombre))
        print(" [OK] Bancos")

        # 15. CATEGORÍAS DE GASTO
        cats_gasto = [
            (1, 'Servicios Básicos', 'ANDE, ESSAP, Internet'),
            (2, 'Sueldos y Jornales', 'Pago de nómina'),
            (3, 'Mantenimiento', 'Reparaciones de oficina o lotes'),
            (4, 'Publicidad', 'Redes sociales, radio, tv'),
            (5, 'Insumos de Oficina', 'Papelería, tinta, etc.')
        ]
        for _id, nombre, desc in cats_gasto:
            if not CategoriaGasto.query.get(_id):
                db.session.add(CategoriaGasto(id=_id, nombre=nombre, descripcion=desc))
        print(" [OK] Categorías de Gasto")

        # 16. PROVEEDORES BASE
        provs = [
            (1, 'ANDE', '80000000-1', '160', 'Avda. España'),
            (2, 'Librería Central', '5556667-8', '0981-111222', 'Centro'),
            (3, 'Facebook Ads', 'Extranjero', '-', 'Online')
        ]
        for _id, razon, ruc, tel, dir in provs:
            if not Proveedor.query.get(_id):
                db.session.add(Proveedor(id=_id, razon_social=razon, ruc=ruc, telefono=tel, direccion=dir))
        print(" [OK] Proveedores")

        db.session.commit()
        print(">>> CARGA DE DATOS COMPLETADA EXITOSAMENTE <<<")

    except Exception as e:
        db.session.rollback()
        print(f"X ERROR DURANTE LA CARGA: {e}")

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True, host='0.0.0.0', port=5000)