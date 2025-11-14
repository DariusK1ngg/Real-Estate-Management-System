import os
import json
from functools import wraps
from flask import Flask, render_template, jsonify, request, redirect, url_for, session, flash, Response
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import Enum, Text, DateTime, or_, and_
from datetime import datetime, date, timedelta
from dotenv import load_dotenv
from decimal import Decimal

from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from flask_bcrypt import Bcrypt
import click

from fpdf import FPDF
from num2words import num2words
import locale

load_dotenv()

# --- CONFIGURACIÓN DE LA APLICACIÓN ---
DB_USER = os.getenv("DB_USER", "root")
DB_PASS = os.getenv("DB_PASS", "")
DB_HOST = os.getenv("DB_HOST", "127.0.0.1")
DB_NAME = os.getenv("DB_NAME", "inmobiliaria")
SECRET_KEY = os.getenv("SECRET_KEY", "inmobiliaria_yeizon")

app = Flask(__name__, template_folder='templates', static_folder='static', static_url_path='/static')
app.secret_key = SECRET_KEY
app.config["SQLALCHEMY_DATABASE_URI"] = f"mysql+pymysql://{DB_USER}:{DB_PASS}@{DB_HOST}/{DB_NAME}"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)

bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Por favor, inicia sesión para acceder a esta página.'
login_manager.login_message_category = 'info'

# ============================
# HELPER: PARAMETRIZACIÓN
# ============================
def get_param(clave, default=""):
    """Obtiene un parámetro del sistema por su clave."""
    try:
        p = ParametroSistema.query.filter_by(clave=clave).first()
        return p.valor if p else default
    except:
        return default

# ============================
# MODELOS DE BASE DE DATOS
# ============================

# --- DEFINICIONES BASE (Tablas Maestras) ---
class TipoDocumento(db.Model):
    __tablename__ = 'tipos_documentos'
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(50), unique=True, nullable=False)
    def to_dict(self): return {'id': self.id, 'nombre': self.nombre}

class TipoCliente(db.Model):
    __tablename__ = 'tipos_cliente'
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(50), unique=True, nullable=False)
    def to_dict(self): return {'id': self.id, 'nombre': self.nombre}

class Profesion(db.Model):
    __tablename__ = 'profesiones'
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), unique=True, nullable=False)
    def to_dict(self): return {'id': self.id, 'nombre': self.nombre}

class FormaPago(db.Model):
    __tablename__ = 'formas_pago'
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(50), unique=True, nullable=False)
    def to_dict(self): return {'id': self.id, 'nombre': self.nombre}

class Impuesto(db.Model):
    __tablename__ = 'impuestos'
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(50), unique=True, nullable=False)
    porcentaje = db.Column(db.Numeric(5, 2), nullable=False)
    def to_dict(self): return {"id": self.id, "nombre": self.nombre, "porcentaje": float(self.porcentaje)}

class CondicionPago(db.Model):
    __tablename__ = 'condiciones_pago'
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(50), unique=True, nullable=False)
    dias = db.Column(db.Integer, default=0)
    def to_dict(self): return {'id': self.id, 'nombre': self.nombre, 'dias': self.dias}

class Ciudad(db.Model):
    __tablename__ = 'ciudades'
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False, unique=True)
    barrios = db.relationship('Barrio', backref='ciudad', lazy=True, cascade="all, delete-orphan")
    def to_dict(self): return {"id": self.id, "nombre": self.nombre}

class Barrio(db.Model):
    __tablename__ = 'barrios'
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    ciudad_id = db.Column(db.Integer, db.ForeignKey('ciudades.id'), nullable=False)
    def to_dict(self): return {"id": self.id, "nombre": self.nombre, "ciudad_id": self.ciudad_id, "ciudad_nombre": self.ciudad.nombre}

# --- SEGURIDAD Y USUARIOS ---
roles_funcionarios = db.Table('roles_funcionarios',
    db.Column('funcionario_id', db.Integer, db.ForeignKey('funcionarios.id'), primary_key=True),
    db.Column('role_id', db.Integer, db.ForeignKey('roles.id'), primary_key=True)
)

roles_aplicaciones = db.Table('roles_aplicaciones',
    db.Column('role_id', db.Integer, db.ForeignKey('roles.id'), primary_key=True),
    db.Column('aplicacion_id', db.Integer, db.ForeignKey('aplicaciones.id'), primary_key=True)
)

class Aplicacion(db.Model):
    __tablename__ = 'aplicaciones'
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    clave = db.Column(db.String(50), unique=True, nullable=False)
    modulo = db.Column(db.String(100))
    def to_dict(self): return {"id": self.id, "nombre": self.nombre, "clave": self.clave, "modulo": self.modulo}

class Role(db.Model):
    __tablename__ = 'roles'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), unique=True, nullable=False)
    description = db.Column(db.String(255))
    aplicaciones = db.relationship('Aplicacion', secondary=roles_aplicaciones, backref=db.backref('roles', lazy='dynamic'))
    def to_json_dict(self): return {"id": self.id, "name": self.name, "description": self.description or ""}

class Cargo(db.Model):
    __tablename__ = 'cargos'
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(80), unique=True, nullable=False)
    def to_dict(self): return {"id": self.id, "nombre": self.nombre}

class Funcionario(db.Model, UserMixin):
    __tablename__ = "funcionarios"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    nombre = db.Column(db.String(100), nullable=False)
    apellido = db.Column(db.String(100), nullable=False)
    documento = db.Column(db.String(20), nullable=False, unique=True)
    usuario = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))
    cargo_id = db.Column(db.Integer, db.ForeignKey('cargos.id'), nullable=True)
    cargo = db.relationship('Cargo', backref=db.backref('funcionarios', lazy=True))
    fecha_ingreso = db.Column(db.Date, nullable=False)
    es_vendedor = db.Column(db.Boolean, default=False)
    estado = db.Column(Enum("activo", "inactivo", name="estado_funcionario_enum"), default="activo")
    roles = db.relationship('Role', secondary=roles_funcionarios, backref=db.backref('funcionarios', lazy='dynamic'))
    def set_password(self, password): self.password_hash = bcrypt.generate_password_hash(password).decode('utf-8')
    def check_password(self, password): return bcrypt.check_password_hash(self.password_hash, password)
    def has_role(self, role_name): return any(role.name == role_name for role in self.roles)
    def to_dict(self): return {"id": self.id, "nombre_completo": f"{self.nombre} {self.apellido}", "nombre": self.nombre, "apellido": self.apellido, "documento": self.documento, "usuario": self.usuario, "cargo_id": self.cargo_id, "cargo_nombre": self.cargo.nombre if self.cargo else "N/A", "estado": self.estado, "roles": [role.name for role in self.roles]}

# --- NEGOCIO INMOBILIARIO ---

class Fraccionamiento(db.Model):
    __tablename__ = "fraccionamientos"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    ciudad_id = db.Column(db.Integer, db.ForeignKey('ciudades.id'), nullable=True)
    ciudad = db.relationship('Ciudad')
    
    nombre = db.Column(db.String(120), nullable=False)
    descripcion = db.Column(db.Text, nullable=True)
    comision_inmobiliaria = db.Column(db.Numeric(5, 2), default=0.00)
    comision_propietario = db.Column(db.Numeric(5, 2), default=0.00)
    geojson = db.Column(db.JSON, nullable=False)
    
    def to_feature(self): 
        return {
            "type": "Feature", 
            "geometry": self.geojson, 
            "properties": {
                "id": self.id, 
                "nombre": self.nombre, 
                "descripcion": self.descripcion or "",
                "ciudad_id": self.ciudad_id, # Enviamos ID al mapa
                "ciudad_nombre": self.ciudad.nombre if self.ciudad else "" # Enviamos nombre al mapa
            }
        }
        
    def to_dict(self):
        return {
            "id": self.id, 
            "nombre": self.nombre, 
            "descripcion": self.descripcion or "",
            "ciudad_id": self.ciudad_id,
            "ciudad_nombre": self.ciudad.nombre if self.ciudad else "",
            "comision_inmobiliaria": float(self.comision_inmobiliaria or 0.0),
            "comision_propietario": float(self.comision_propietario or 0.0)
        }

class Lote(db.Model):
    __tablename__ = "lotes"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    numero_lote = db.Column(db.String(50), nullable=False)
    manzana = db.Column(db.String(50), nullable=False)
    precio = db.Column(db.Numeric(12, 2), nullable=False)
    precio_financiado_130 = db.Column(db.Numeric(12, 2), nullable=True)
    precio_cuota_130 = db.Column(db.Numeric(12, 2), nullable=True)
    metros_cuadrados = db.Column(db.Integer, nullable=False)
    estado = db.Column(Enum("disponible", "reservado", "vendido", name="estado_enum"), nullable=False, default="disponible")
    geojson = db.Column(db.JSON, nullable=False)
    fraccionamiento_id = db.Column(db.Integer, db.ForeignKey("fraccionamientos.id"), nullable=False)
    fraccionamiento = db.relationship("Fraccionamiento", backref=db.backref("lotes", lazy=True, cascade="all, delete-orphan"))
    contratos = db.relationship("Contrato", backref="lote", lazy=True)
    lista_precios = db.relationship("ListaPrecioLote", backref="lote", lazy=True, cascade="all, delete-orphan")
    def to_feature(self): return {"type": "Feature", "geometry": self.geojson, "properties": {"id": self.id, "numero_lote": self.numero_lote, "manzana": self.manzana, "precio": float(self.precio), "precio_financiado_130": float(self.precio_financiado_130) if self.precio_financiado_130 else None, "precio_cuota_130": float(self.precio_cuota_130) if self.precio_cuota_130 else None, "metros_cuadrados": self.metros_cuadrados, "estado": self.estado, "fraccionamiento_id": self.fraccionamiento_id}}

class ListaPrecioLote(db.Model):
    __tablename__ = 'lista_precio_lote'
    id = db.Column(db.Integer, primary_key=True)
    lote_id = db.Column(db.Integer, db.ForeignKey('lotes.id'), nullable=False)
    condicion_pago_id = db.Column(db.Integer, db.ForeignKey('condiciones_pago.id'), nullable=False)
    cantidad_cuotas = db.Column(db.Integer, nullable=False)
    precio_cuota = db.Column(db.Numeric(12, 2), nullable=False)
    precio_total = db.Column(db.Numeric(12, 2), nullable=False)
    condicion_pago = db.relationship("CondicionPago")

    def to_dict(self):
        return {
            "id": self.id,
            "lote_id": self.lote_id,
            "condicion_pago_id": self.condicion_pago_id,
            "condicion_pago_nombre": self.condicion_pago.nombre,
            "cantidad_cuotas": self.cantidad_cuotas,
            "precio_cuota": float(self.precio_cuota),
            "precio_total": float(self.precio_total)
        }

class Cliente(db.Model):
    __tablename__ = "clientes"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    
    # CONEXIONES PARAMÉTRICAS
    tipo_documento_id = db.Column(db.Integer, db.ForeignKey('tipos_documentos.id'), nullable=True)
    tipo_documento = db.relationship('TipoDocumento')
    
    profesion_id = db.Column(db.Integer, db.ForeignKey('profesiones.id'), nullable=True)
    profesion = db.relationship('Profesion')
    
    tipo_cliente_id = db.Column(db.Integer, db.ForeignKey('tipos_cliente.id'), nullable=True)
    tipo_cliente = db.relationship('TipoCliente')

    # CONEXIONES DE DIRECCIÓN
    ciudad_id = db.Column(db.Integer, db.ForeignKey('ciudades.id'), nullable=True)
    barrio_id = db.Column(db.Integer, db.ForeignKey('barrios.id'), nullable=True)
    ciudad = db.relationship('Ciudad')
    barrio = db.relationship('Barrio')

    documento = db.Column(db.String(20), nullable=False, unique=True)
    nombre = db.Column(db.String(100), nullable=False)
    apellido = db.Column(db.String(100), nullable=False)
    telefono = db.Column(db.String(20), nullable=True)
    email = db.Column(db.String(100), nullable=True)
    direccion = db.Column(db.Text, nullable=True)
    
    fecha_registro = db.Column(db.DateTime, default=datetime.utcnow)
    estado = db.Column(Enum("activo", "inactivo", name="estado_cliente_enum"), nullable=False, default="activo")
    contratos = db.relationship("Contrato", backref="cliente", lazy=True)
    
    def to_dict(self): 
        return {
            "id": self.id, 
            "tipo_documento_id": self.tipo_documento_id,
            "tipo_documento": self.tipo_documento.nombre if self.tipo_documento else "CI",
            "documento": self.documento, 
            "nombre": self.nombre, 
            "apellido": self.apellido, 
            "nombre_completo": f"{self.nombre} {self.apellido}",
            "telefono": self.telefono or "", 
            "email": self.email or "", 
            "direccion": self.direccion or "",
            "ciudad_id": self.ciudad_id,
            "ciudad_nombre": self.ciudad.nombre if self.ciudad else "",
            "barrio_id": self.barrio_id,
            "barrio_nombre": self.barrio.nombre if self.barrio else "",
            "profesion_id": self.profesion_id,
            "tipo_cliente_id": self.tipo_cliente_id,
            "fecha_registro": self.fecha_registro.isoformat() if self.fecha_registro else None, 
            "estado": self.estado
        }

class Contrato(db.Model):
    __tablename__ = "contratos"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    numero_contrato = db.Column(db.String(50), nullable=False, unique=True)
    cliente_id = db.Column(db.Integer, db.ForeignKey("clientes.id"), nullable=False)
    lote_id = db.Column(db.Integer, db.ForeignKey("lotes.id"), nullable=False)
    fecha_contrato = db.Column(db.Date, nullable=False)
    valor_total = db.Column(db.Numeric(12, 2), nullable=False)
    cuota_inicial = db.Column(db.Numeric(12, 2), nullable=False)
    cantidad_cuotas = db.Column(db.Integer, nullable=False)
    valor_cuota = db.Column(db.Numeric(12, 2), nullable=False)
    tipo_contrato = db.Column(Enum("venta", "reserva", "alquiler", name="tipo_contrato_enum"), nullable=False, default="venta")
    estado = db.Column(Enum("activo", "cancelado", "finalizado", name="estado_contrato_enum"), nullable=False, default="activo")
    observaciones = db.Column(db.Text, nullable=True)
    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow)
    cuotas = db.relationship("Cuota", backref="contrato", lazy=True, cascade="all, delete-orphan")
    pagos = db.relationship("Pago", backref="contrato", lazy=True, cascade="all, delete-orphan")
    def to_dict(self): return {"id": self.id, "numero_contrato": self.numero_contrato, "cliente_id": self.cliente_id, "lote_id": self.lote_id, "fecha_contrato": self.fecha_contrato.isoformat() if self.fecha_contrato else None, "valor_total": float(self.valor_total), "cuota_inicial": float(self.cuota_inicial), "cantidad_cuotas": self.cantidad_cuotas, "valor_cuota": float(self.valor_cuota), "tipo_contrato": self.tipo_contrato, "estado": self.estado, "observaciones": self.observaciones, "fecha_creacion": self.fecha_creacion.isoformat() if self.fecha_creacion else None, "cliente_nombre": f"{self.cliente.nombre} {self.cliente.apellido}", "lote_info": f"{self.lote.manzana} - {self.lote.numero_lote}", "fraccionamiento": self.lote.fraccionamiento.nombre}

class Cuota(db.Model):
    __tablename__ = "cuotas"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    contrato_id = db.Column(db.Integer, db.ForeignKey("contratos.id"), nullable=False)
    numero_cuota = db.Column(db.Integer, nullable=False)
    fecha_vencimiento = db.Column(db.Date, nullable=False)
    valor_cuota = db.Column(db.Numeric(12, 2), nullable=False)
    fecha_pago = db.Column(db.Date, nullable=True)
    valor_pagado = db.Column(db.Numeric(12, 2), default=0.00)
    estado = db.Column(Enum("pendiente", "pagada", "vencida", name="estado_cuota_enum"), nullable=False, default="pendiente")
    observaciones = db.Column(db.Text, nullable=True)
    pagos = db.relationship("Pago", backref="cuota", lazy=True, cascade="all, delete-orphan")
    def to_dict(self): return {"id": self.id, "contrato_id": self.contrato_id, "numero_cuota": self.numero_cuota, "fecha_vencimiento": self.fecha_vencimiento.isoformat() if self.fecha_vencimiento else None, "valor_cuota": float(self.valor_cuota), "fecha_pago": self.fecha_pago.isoformat() if self.fecha_pago else None, "valor_pagado": float(self.valor_pagado), "estado": self.estado, "observaciones": self.observaciones, "dias_vencimiento": (self.fecha_vencimiento - date.today()).days if self.fecha_vencimiento else None}

class Pago(db.Model):
    __tablename__ = "pagos"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    contrato_id = db.Column(db.Integer, db.ForeignKey("contratos.id"), nullable=False)
    cuota_id = db.Column(db.Integer, db.ForeignKey("cuotas.id"), nullable=True)
    fecha_pago = db.Column(db.DateTime, nullable=False)
    monto = db.Column(db.Numeric(12, 2), nullable=False)
    forma_pago_id = db.Column(db.Integer, db.ForeignKey('formas_pago.id'), nullable=True)
    forma_pago_rel = db.relationship('FormaPago')
    referencia = db.Column(db.String(100), nullable=True)
    observaciones = db.Column(db.Text, nullable=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('funcionarios.id'), nullable=True)
    cuenta_bancaria_id = db.Column(db.Integer, db.ForeignKey('cuentas_bancarias.id'), nullable=True)
    cuenta_bancaria = db.relationship('CuentaBancaria')
    
    def to_dict(self): 
        return {
            "id": self.id, 
            "contrato_id": self.contrato_id, 
            "cuota_id": self.cuota_id, 
            "fecha_pago": self.fecha_pago.isoformat() if self.fecha_pago else None, 
            "monto": float(self.monto), 
            "forma_pago_id": self.forma_pago_id,
            "forma_pago": self.forma_pago_rel.nombre if self.forma_pago_rel else "N/A", 
            "referencia": self.referencia, 
            "observaciones": self.observaciones,
            "cuenta_bancaria_id": self.cuenta_bancaria_id, 
            "usuario_id": self.usuario_id
        }

class Caja(db.Model):
    __tablename__ = "cajas"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    descripcion = db.Column(db.String(100), nullable=False, unique=True)
    sucursal = db.Column(db.String(100), nullable=True)
    saldo_actual = db.Column(db.Numeric(12, 2), default=0.00)
    abierta = db.Column(db.Boolean, default=False)
    ultimo_arqueo = db.Column(db.DateTime, nullable=True)

class MovimientoCaja(db.Model):
    __tablename__ = "movimientos_caja"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    caja_id = db.Column(db.Integer, db.ForeignKey("cajas.id"), nullable=False)
    tipo_movimiento = db.Column(Enum("ingreso", "egreso", "transferencia", name="tipo_mov_caja_enum"), nullable=False)
    monto = db.Column(db.Numeric(12, 2), nullable=False)
    concepto = db.Column(db.String(255), nullable=False)
    fecha_hora = db.Column(db.DateTime, default=datetime.utcnow)
    pago_id = db.Column(db.Integer, db.ForeignKey("pagos.id"), nullable=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('funcionarios.id'), nullable=True)
    
    usuario = db.relationship("Funcionario")

class CategoriaGasto(db.Model):
    __tablename__ = "categorias_gasto"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    nombre = db.Column(db.String(100), nullable=False, unique=True)
    descripcion = db.Column(db.Text, nullable=True)
    gastos = db.relationship("Gasto", backref="categoria", lazy=True)
    
    def to_dict(self): 
        return { 
            "id": self.id, 
            "nombre": self.nombre, 
            "descripcion": self.descripcion or "" 
        }

class Proveedor(db.Model):
    __tablename__ = "proveedores"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    razon_social = db.Column(db.String(150), nullable=False)
    ruc = db.Column(db.String(20), nullable=False, unique=True)
    telefono = db.Column(db.String(30), nullable=True)
    direccion = db.Column(db.Text, nullable=True)
    gastos = db.relationship("Gasto", backref="proveedor", lazy=True)
    def to_dict(self): return { "id": self.id, "razon_social": self.razon_social, "ruc": self.ruc, "telefono": self.telefono or "", "direccion": self.direccion or "" }

class Gasto(db.Model):
    __tablename__ = "gastos"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    proveedor_id = db.Column(db.Integer, db.ForeignKey("proveedores.id"), nullable=False)
    categoria_gasto_id = db.Column(db.Integer, db.ForeignKey("categorias_gasto.id"), nullable=False)
    detalle = db.Column(db.String(255), nullable=True)
    numero_factura = db.Column(db.String(50), nullable=True)
    fecha_factura = db.Column(db.Date, nullable=False)
    monto = db.Column(db.Numeric(12, 2), nullable=False)
    estado = db.Column(Enum("pendiente", "pagado", "anulado", name="estado_gasto_enum"), nullable=False, default="pendiente")
    fecha_pago = db.Column(db.Date, nullable=True)
    def to_dict(self): return { "id": self.id, "proveedor_id": self.proveedor_id, "proveedor_nombre": self.proveedor.razon_social, "categoria_gasto_id": self.categoria_gasto_id, "categoria_nombre": self.categoria.nombre if self.categoria else "N/A", "concepto": self.categoria.nombre if self.categoria else "N/A", "detalle": self.detalle or "", "numero_factura": self.numero_factura, "fecha_factura": self.fecha_factura.isoformat(), "monto": float(self.monto), "estado": self.estado, "fecha_pago": self.fecha_pago.isoformat() if self.fecha_pago else None }

class Venta(db.Model):
    __tablename__ = "ventas"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    cliente_id = db.Column(db.Integer, db.ForeignKey("clientes.id"), nullable=False)
    vendedor_id = db.Column(db.Integer, db.ForeignKey("funcionarios.id"), nullable=True)
    
    # CONEXIÓN CON TALONARIO
    talonario_id = db.Column(db.Integer, db.ForeignKey("talonarios.id"), nullable=True)
    talonario = db.relationship("Talonario")

    fecha_venta = db.Column(db.Date, nullable=False, default=date.today)
    numero_factura = db.Column(db.String(50), nullable=False, unique=True)
    total = db.Column(db.Numeric(12, 2), nullable=False)
    estado = db.Column(Enum("emitida", "anulada", name="estado_venta_enum"), nullable=False, default="emitida")
    
    cliente = db.relationship("Cliente", backref=db.backref("ventas", lazy=True))
    vendedor = db.relationship("Funcionario", backref=db.backref("ventas", lazy=True))
    detalles = db.relationship("VentaDetalle", backref="venta", lazy=True, cascade="all, delete-orphan")

    def to_dict(self): 
        return { 
            "id": self.id, 
            "cliente_id": self.cliente_id, 
            "cliente_nombre": f"{self.cliente.nombre} {self.cliente.apellido}", 
            "vendedor_id": self.vendedor_id, 
            "vendedor_nombre": f"{self.vendedor.nombre} {self.vendedor.apellido}" if self.vendedor else "N/A", 
            "numero_factura": self.numero_factura, 
            "talonario_id": self.talonario_id,
            "total": float(self.total), 
            "estado": self.estado, 
            "detalles": [d.to_dict() for d in self.detalles] 
        }

class VentaDetalle(db.Model):
    __tablename__ = "ventas_detalle"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    venta_id = db.Column(db.Integer, db.ForeignKey("ventas.id"), nullable=False)
    lote_id = db.Column(db.Integer, db.ForeignKey("lotes.id"), nullable=True)
    
    # CONEXIÓN A IMPUESTO
    impuesto_id = db.Column(db.Integer, db.ForeignKey("impuestos.id"), nullable=True)
    impuesto = db.relationship("Impuesto")
    
    descripcion = db.Column(db.String(255), nullable=False)
    cantidad = db.Column(db.Integer, nullable=False, default=1)
    precio_unitario = db.Column(db.Numeric(12, 2), nullable=False)
    subtotal = db.Column(db.Numeric(12, 2), nullable=False)
    lote = db.relationship("Lote")
    
    def to_dict(self): 
        return { 
            "id": self.id, 
            "venta_id": self.venta_id, 
            "lote_id": self.lote_id, 
            "impuesto_id": self.impuesto_id,
            "impuesto_nombre": self.impuesto.nombre if self.impuesto else "",
            "descripcion": self.descripcion, 
            "cantidad": self.cantidad, 
            "precio_unitario": float(self.precio_unitario), 
            "subtotal": float(self.subtotal) 
        }

class EntidadFinanciera(db.Model):
    __tablename__ = "entidades_financieras"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    nombre = db.Column(db.String(100), nullable=False, unique=True)
    def to_dict(self): return {"id": self.id, "nombre": self.nombre}

class CuentaBancaria(db.Model):
    __tablename__ = "cuentas_bancarias"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    entidad_id = db.Column(db.Integer, db.ForeignKey("entidades_financieras.id"), nullable=False)
    numero_cuenta = db.Column(db.String(50), nullable=False, unique=True)
    titular = db.Column(db.String(150), nullable=False)
    tipo_cuenta = db.Column(Enum("corriente", "ahorro", name="tipo_cuenta_enum"), nullable=False)
    moneda = db.Column(Enum("PYG", "USD", name="moneda_enum"), nullable=False, default="PYG")
    saldo = db.Column(db.Numeric(14, 2), default=0.00)
    entidad = db.relationship("EntidadFinanciera", backref=db.backref("cuentas", lazy=True))
    
    def to_dict(self): 
        return {
            "id": self.id, 
            "entidad_id": self.entidad_id, 
            "entidad_nombre": self.entidad.nombre, 
            "numero_cuenta": self.numero_cuenta, 
            "titular": self.titular, 
            "tipo_cuenta": self.tipo_cuenta, 
            "moneda": self.moneda, 
            "saldo": float(self.saldo),
            "tiene_movimientos": bool(self.depositos)
        }

class DepositoBancario(db.Model):
    __tablename__ = "depositos_bancarios"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    cuenta_id = db.Column(db.Integer, db.ForeignKey("cuentas_bancarias.id"), nullable=False)
    fecha_deposito = db.Column(db.Date, nullable=False)
    monto = db.Column(db.Numeric(12, 2), nullable=False)
    referencia = db.Column(db.String(100), nullable=True)
    concepto = db.Column(db.Text, nullable=True)
    estado = db.Column(Enum("confirmado", "anulado", name="estado_deposito_enum"), nullable=False, default="confirmado")
    usuario_id = db.Column(db.Integer, db.ForeignKey('funcionarios.id'), nullable=True)
    cuenta = db.relationship("CuentaBancaria", backref=db.backref("depositos", lazy=True))
    usuario = db.relationship("Funcionario")
    def to_dict(self): return {"id": self.id, "cuenta_id": self.cuenta_id, "cuenta_info": f"{self.cuenta.entidad.nombre} - {self.cuenta.numero_cuenta}", "fecha_deposito": self.fecha_deposito.isoformat(), "monto": float(self.monto), "referencia": self.referencia or "", "concepto": self.concepto or "", "estado": self.estado, "usuario_nombre": f"{self.usuario.nombre} {self.usuario.apellido}" if self.usuario else "N/A"}

class TipoComprobante(db.Model):
    __tablename__ = 'tipos_comprobantes'
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), unique=True, nullable=False)

    def to_dict(self):
        return {"id": self.id, "nombre": self.nombre}

class Talonario(db.Model):
    __tablename__ = 'talonarios'
    id = db.Column(db.Integer, primary_key=True)
    tipo_comprobante_id = db.Column(db.Integer, db.ForeignKey('tipos_comprobantes.id'), nullable=False)
    timbrado = db.Column(db.String(50), nullable=False)
    fecha_inicio_vigencia = db.Column(db.Date, nullable=False)
    fecha_fin_vigencia = db.Column(db.Date, nullable=False)
    punto_expedicion = db.Column(db.String(3), nullable=False, default="001")
    caja = db.Column(db.String(3), nullable=False, default="001")
    numero_actual = db.Column(db.Integer, nullable=False, default=1)
    numero_fin = db.Column(db.Integer, nullable=False)
    activo = db.Column(db.Boolean, default=True)
    
    tipo_comprobante = db.relationship("TipoComprobante")

    def to_dict(self):
        return {
            "id": self.id,
            "tipo_comprobante_id": self.tipo_comprobante_id,
            "tipo_comprobante_nombre": self.tipo_comprobante.nombre if self.tipo_comprobante else "N/A",
            "timbrado": self.timbrado,
            "fecha_inicio_vigencia": self.fecha_inicio_vigencia.isoformat(),
            "fecha_fin_vigencia": self.fecha_fin_vigencia.isoformat(),
            "punto_expedicion": self.punto_expedicion,
            "caja": self.caja,
            "numero_actual": self.numero_actual,
            "numero_fin": self.numero_fin,
            "activo": self.activo
        }

class ParametroSistema(db.Model):
    __tablename__ = 'parametros_sistema'
    id = db.Column(db.Integer, primary_key=True)
    clave = db.Column(db.String(50), unique=True, nullable=False)
    valor = db.Column(db.String(255), nullable=False)
    descripcion = db.Column(db.Text, nullable=True)
    
    def to_dict(self):
        return {"id": self.id, "clave": self.clave, "valor": self.valor, "descripcion": self.descripcion}

class Cotizacion(db.Model):
    __tablename__ = 'cotizaciones'
    id = db.Column(db.Integer, primary_key=True)
    fecha = db.Column(db.Date, nullable=False, default=date.today)
    moneda_origen = db.Column(Enum("USD", "PYG", name="moneda_cot_orig_enum"), nullable=False)
    moneda_destino = db.Column(Enum("USD", "PYG", name="moneda_cot_dest_enum"), nullable=False)
    compra = db.Column(db.Numeric(10, 2), nullable=False)
    venta = db.Column(db.Numeric(10, 2), nullable=False)
    def to_dict(self): return {"id": self.id, "fecha": self.fecha.isoformat(), "moneda_origen": self.moneda_origen, "moneda_destino": self.moneda_destino, "compra": float(self.compra), "venta": float(self.venta)}


# ============================
# AUTENTICACIÓN
# ============================

@login_manager.user_loader
def load_user(user_id):
    return Funcionario.query.get(int(user_id))

def role_required(*roles):
    def wrapper(fn):
        @wraps(fn)
        def decorated_view(*args, **kwargs):
            if not current_user.is_authenticated:
                return login_manager.unauthorized()
            if not current_user.has_role('Admin') and not any(current_user.has_role(role) for role in roles):
                flash("No tienes permiso para acceder a esta página.", "danger")
                return redirect(url_for('admin_dashboard'))
            return fn(*args, **kwargs)
        return decorated_view
    return wrapper

def admin_required(f):
    return role_required('Admin')(f)

# ============================
# RUTAS PÚBLICAS Y DE LOGIN
# ============================

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated: return redirect(url_for('admin_dashboard'))
    if request.method == "POST":
        user = Funcionario.query.filter_by(usuario=request.form.get("username")).first()
        if user and user.check_password(request.form.get("password")):
            if user.estado == 'activo':
                login_user(user)
                return redirect(request.args.get('next') or url_for('admin_dashboard'))
            else: flash("Este usuario está inactivo.", "warning")
        else: flash("Usuario o contraseña incorrectos.", "danger")
    return render_template("login.html")

@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("index"))

# ============================
# RUTAS DEL PANEL DE ADMINISTRACIÓN
# ============================

@app.route("/admin")
@login_required
def admin(): return redirect(url_for("admin_dashboard"))

@app.route("/admin/dashboard")
@login_required
def admin_dashboard():
    stats = {
        "total_lotes": Lote.query.count(), "disponibles": Lote.query.filter_by(estado="disponible").count(),
        "reservados": Lote.query.filter_by(estado="reservado").count(), "vendidos": Lote.query.filter_by(estado="vendido").count(),
        "total_clientes": Cliente.query.count(), "contratos_activos": Contrato.query.filter_by(estado="activo").count()
    }
    return render_template("dashboard.html", **stats)

@app.route("/admin/mapa")
@login_required
@role_required('Empleado', 'Vendedor')
def admin_mapa(): return render_template("admin.html")

# --- RUTAS REPORTES (VISTAS) ---
@app.route("/admin/cobros/reportes/arqueo")
@login_required
def reporte_arqueo_view():
    return render_template("reportes/arqueo_caja.html")

@app.route("/admin/tesoreria/reportes/extracto")
@login_required
def reporte_extracto_view():
    return render_template("reportes/extracto_bancario.html")

@app.route("/admin/base/definiciones")
@login_required
@admin_required
def base_definiciones(): return render_template("base/definiciones.html")

@app.route("/admin/cobros/movimientos")
@login_required
@role_required('Cajero')
def cobros_movimientos(): return render_template("cobros/movimientos.html")

@app.route("/admin/cobros/reportes")
@login_required
@role_required('Cajero')
def cobros_reportes(): return render_template("cobros/reportes.html")

@app.route("/admin/cobros/definiciones")
@login_required
@role_required('Admin', 'Cajero')
def cobros_definiciones(): return render_template("cobros/definiciones.html")

@app.route("/admin/inventario/movimientos")
@login_required
@role_required('Empleado', 'Vendedor')
def inventario_movimientos(): return render_template("inventario/movimientos.html")

@app.route("/admin/inventario/reportes")
@login_required
@role_required('Empleado', 'Vendedor')
def inventario_reportes(): return render_template("inventario/reportes.html")

@app.route("/admin/inventario/definiciones")
@login_required
@role_required('Admin', 'Empleado', 'Vendedor')
def inventario_definiciones(): 
    return render_template("inventario/definiciones_fraccionamientos.html")

@app.route("/admin/inventario/fraccionamientos/<int:fraccionamiento_id>")
@login_required
@role_required('Admin', 'Empleado', 'Vendedor')
def inventario_fraccionamiento_detalle(fraccionamiento_id):
    fraccionamiento = Fraccionamiento.query.get_or_404(fraccionamiento_id)
    return render_template("inventario/fraccionamiento_detalle.html", fraccionamiento=fraccionamiento)

@app.route("/admin/rrhh/definiciones")
@login_required
@admin_required
def rrhh_definiciones(): return render_template("rrhh/definiciones.html")

@app.route("/admin/rrhh/definiciones/funcionarios")
@login_required
@admin_required
def rrhh_definiciones_funcionarios(): return render_template("rrhh/definiciones_funcionarios.html")

@app.route("/admin/rrhh/definiciones/cargos")
@login_required
@admin_required
def rrhh_definiciones_cargos(): return render_template("rrhh/definiciones_cargos.html")

@app.route("/admin/tesoreria/movimientos")
@login_required
@role_required('Cajero')
def tesoreria_movimientos(): return render_template("tesoreria/movimientos.html")

@app.route("/admin/tesoreria/reportes")
@login_required
@role_required('Cajero')
def tesoreria_reportes(): return render_template("tesoreria/reportes.html")

@app.route("/admin/tesoreria/definiciones")
@login_required
@role_required('Admin', 'Cajero')
def tesoreria_definiciones(): return render_template("tesoreria/definiciones.html")

@app.route("/admin/gastos/definiciones")
@login_required
@role_required('Cajero', 'Empleado')
def gastos_definiciones(): return render_template("gastos/definiciones.html")

@app.route("/admin/gastos/movimientos")
@login_required
@role_required('Cajero', 'Empleado')
def gastos_movimientos(): return render_template("gastos/movimientos.html")

@app.route("/admin/gastos/reportes")
@login_required
@role_required('Cajero', 'Empleado')
def gastos_reportes(): return render_template("gastos/reportes.html")

@app.route("/admin/ventas/definiciones")
@login_required
@role_required('Empleado', 'Vendedor')
def ventas_definiciones(): return render_template("ventas/definiciones.html")

@app.route("/admin/ventas/definiciones/clientes")
@login_required
@role_required('Empleado', 'Vendedor', 'Cajero')
def ventas_definiciones_clientes(): return render_template("ventas/definiciones_clientes.html")

@app.route("/admin/ventas/movimientos")
@login_required
@role_required('Empleado', 'Vendedor')
def ventas_movimientos(): return render_template("ventas/movimientos.html")

@app.route("/admin/ventas/movimientos/contratos/nuevo")
@login_required
@role_required('Empleado', 'Vendedor')
def ventas_movimientos_contratos_nuevo():
    return render_template("ventas/movimientos_contratos_nuevo.html")

@app.route("/admin/ventas/reportes")
@login_required
@role_required('Empleado', 'Vendedor')
def ventas_reportes(): return render_template("ventas/reportes.html")

# ============================
# APIS
# ============================

# --- APIs FRACCIONAMIENTOS y LOTES ---
@app.route("/api/fraccionamientos", methods=["GET"])
def api_fraccionamientos_geojson_list(): 
    fracs = Fraccionamiento.query.all()
    return jsonify({"type": "FeatureCollection", "features": [f.to_feature() for f in fracs]})

@app.route("/api/fraccionamientos/<int:fid>/lotes", methods=["GET"])
def api_lotes_by_frac(fid): 
    lotes = Lote.query.filter_by(fraccionamiento_id=fid).all()
    return jsonify({"type": "FeatureCollection", "features": [l.to_feature() for l in lotes]})
    
@app.route("/api/lotes", methods=["GET"])
def api_lotes_all():
    lotes = Lote.query.all()
    return jsonify({"type": "FeatureCollection", "features": [l.to_feature() for l in lotes]})

@app.route("/api/admin/fraccionamientos", methods=["GET"])
@login_required
def api_fraccionamientos_lista():
    search_term = request.args.get('q', '')
    query = Fraccionamiento.query
    if search_term:
        query = query.filter(Fraccionamiento.nombre.ilike(f'%{search_term}%'))
    fraccionamientos = query.order_by(Fraccionamiento.nombre).all()
    return jsonify([f.to_dict() for f in fraccionamientos])

@app.route("/api/admin/fraccionamientos/<int:fraccionamiento_id>/detalle", methods=["GET"])
@login_required
def api_fraccionamiento_detalle_completo(fraccionamiento_id):
    fraccionamiento = Fraccionamiento.query.get_or_404(fraccionamiento_id)
    lotes = Lote.query.filter_by(fraccionamiento_id=fraccionamiento_id).order_by(Lote.manzana, Lote.numero_lote).all()
    fraccionamiento_data = fraccionamiento.to_dict()
    fraccionamiento_data['lotes'] = [lote.to_feature()['properties'] for lote in lotes]
    return jsonify(fraccionamiento_data)

@app.route("/api/admin/fraccionamientos", methods=["POST"])
@login_required
@admin_required
def api_admin_crear_fraccionamiento():
    data = request.get_json(force=True)
    if not data.get('nombre') or not data.get('geojson'):
        return jsonify({"error": "Nombre y datos GeoJSON son requeridos"}), 400
    
    frac = Fraccionamiento(
        nombre=data["nombre"], 
        descripcion=data.get("descripcion", ""), 
        geojson=data["geojson"],
        ciudad_id=data.get("ciudad_id")
    )
    db.session.add(frac); db.session.commit()
    return jsonify({"ok": True, "id": frac.id}), 201

@app.route("/api/admin/fraccionamientos/<int:fid>", methods=["PATCH", "DELETE"])
@login_required
@admin_required
def api_admin_fraccionamientos_gestion(fid):
    frac = Fraccionamiento.query.get_or_404(fid)
    if request.method == "DELETE":
        if frac.lotes: return jsonify({"error": "No se puede eliminar, tiene lotes asociados."}), 400
        db.session.delete(frac); db.session.commit()
        return jsonify({"message": "Eliminado correctamente"})
    
    if request.method == "PATCH":
        data = request.get_json(force=True)
        frac.nombre = data.get("nombre", frac.nombre)
        frac.descripcion = data.get("descripcion", frac.descripcion)
        frac.comision_inmobiliaria = data.get("comision_inmobiliaria", frac.comision_inmobiliaria)
        frac.comision_propietario = data.get("comision_propietario", frac.comision_propietario)
        
        if 'ciudad_id' in data:
            frac.ciudad_id = int(data['ciudad_id']) if data['ciudad_id'] else None
            
        db.session.commit()
        return jsonify(frac.to_dict())

@app.route("/api/admin/lotes", methods=["POST"])
@login_required
@admin_required
def api_admin_create_lote(): 
    data = request.get_json(force=True)
    lote = Lote(numero_lote=str(data["numero_lote"]), manzana=str(data["manzana"]), precio=float(data["precio"]), metros_cuadrados=int(data["metros_cuadrados"]), estado=str(data["estado"]), geojson=data["geojson"], fraccionamiento_id=int(data["fraccionamiento_id"]))
    db.session.add(lote); db.session.commit()
    return jsonify({"ok": True, "id": lote.id})

@app.route("/api/admin/lotes/<int:lote_id>", methods=["PATCH", "DELETE"])
@login_required
@admin_required
def api_admin_update_delete_lote(lote_id):
    lote = Lote.query.get_or_404(lote_id)
    if request.method == "DELETE":
        if lote.contratos: return jsonify({"error": "No se puede eliminar, el lote está asociado a un contrato."}), 400
        db.session.delete(lote); db.session.commit(); return jsonify({"ok": True})
    
    if request.method == "PATCH":
        data = request.get_json(force=True)
        lote.manzana = data.get("manzana", lote.manzana)
        lote.numero_lote = data.get("numero_lote", lote.numero_lote)
        lote.precio = data.get("precio", lote.precio)
        lote.metros_cuadrados = data.get("metros_cuadrados", lote.metros_cuadrados)
        lote.estado = data.get("estado", lote.estado)
        if "geojson" in data:
            lote.geojson = data["geojson"]
        db.session.commit()
        return jsonify({"ok": True})

# --- APIs LISTA DE PRECIOS ---
@app.route("/api/admin/lotes/<int:lote_id>/precios", methods=["GET", "POST"])
@login_required
@role_required('Admin', 'Empleado')
def api_lista_precios_lote(lote_id):
    lote = Lote.query.get_or_404(lote_id)
    if request.method == "POST":
        data = request.json
        condicion_pago = CondicionPago.query.get(data['condicion_pago_id'])

        nuevo_precio = ListaPrecioLote(
            lote_id=lote_id,
            condicion_pago_id=data['condicion_pago_id'],
            cantidad_cuotas=data['cantidad_cuotas'],
            precio_cuota=data['precio_cuota'],
            precio_total=data['precio_total']
        )
        db.session.add(nuevo_precio)

        if condicion_pago and 'contado' in condicion_pago.nombre.lower():
            lote.precio = data['precio_total']

        if int(data['cantidad_cuotas']) == 130:
            lote.precio_financiado_130 = data['precio_total']
            lote.precio_cuota_130 = data['precio_cuota']

        db.session.commit()
        return jsonify(nuevo_precio.to_dict()), 201

    precios = ListaPrecioLote.query.filter_by(lote_id=lote_id).all()
    return jsonify([p.to_dict() for p in precios])

@app.route("/api/admin/lista-precios/<int:precio_id>", methods=["DELETE"])
@login_required
@role_required('Admin', 'Empleado')
def api_delete_lista_precio(precio_id):
    precio = ListaPrecioLote.query.get_or_404(precio_id)
    lote = precio.lote

    if precio.cantidad_cuotas == 130:
        lote.precio_financiado_130 = None
        lote.precio_cuota_130 = None

    if precio.condicion_pago and 'contado' in precio.condicion_pago.nombre.lower():
        lote.precio = 0

    db.session.delete(precio)
    db.session.commit()
    return jsonify({"message": "Plan de pago eliminado"})

# --- APIs RRHH ---
@app.route("/api/admin/funcionarios", methods=["GET", "POST"])
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
        return jsonify(nuevo_funcionario.to_dict()), 201
    
    funcionarios = Funcionario.query.order_by(Funcionario.nombre).all()
    return jsonify([f.to_dict() for f in funcionarios])

@app.route("/api/admin/funcionarios/<int:fid>", methods=["GET", "PUT", "DELETE"])
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
        return jsonify(funcionario.to_dict())

    if request.method == "DELETE":
        if current_user.id == fid: return jsonify({"error": "No te puedes eliminar a ti mismo."}), 400
        db.session.delete(funcionario)
        db.session.commit()
        return jsonify({"message": "Funcionario eliminado."})

    roles = [r.name for r in funcionario.roles]
    func_dict = funcionario.to_dict()
    func_dict['roles'] = roles
    return jsonify(func_dict)

@app.route("/api/admin/cargos", methods=["GET", "POST"])
@login_required
@admin_required
def api_admin_cargos():
    if request.method == "POST":
        data = request.json
        if not data or not data.get('nombre'): return jsonify({"error": "El nombre del cargo es requerido."}), 400
        if Cargo.query.filter_by(nombre=data['nombre']).first(): return jsonify({"error": "Ese cargo ya existe."}), 400
        nuevo_cargo = Cargo(nombre=data['nombre'])
        db.session.add(nuevo_cargo); db.session.commit()
        return jsonify(nuevo_cargo.to_dict()), 201
    return jsonify([c.to_dict() for c in Cargo.query.order_by(Cargo.nombre).all()])

@app.route("/api/admin/cargos/<int:cid>", methods=["PUT", "DELETE"])
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
        return jsonify(cargo.to_dict())
    if request.method == "DELETE":
        if cargo.funcionarios: return jsonify({"error": "No se puede eliminar, está asignado a funcionarios."}), 400
        db.session.delete(cargo)
        db.session.commit()
        return jsonify({"message": "Cargo eliminado."})

# --- APIs MÓDULO BASE ---
@app.route("/api/admin/aplicaciones", methods=["GET"])
@login_required
@admin_required
def api_aplicaciones():
    apps = Aplicacion.query.order_by(Aplicacion.modulo, Aplicacion.nombre).all()
    return jsonify([a.to_dict() for a in apps])

@app.route("/api/admin/roles", methods=["GET"])
@login_required
@admin_required
def api_admin_roles():
    roles = Role.query.filter(Role.name != 'Admin').order_by(Role.name).all()
    return jsonify([r.to_json_dict() for r in roles])

@app.route("/api/admin/roles/<int:id_rol>", methods=["GET", "PUT"])
@login_required
@admin_required
def api_rol_detalle(id_rol):
    rol = Role.query.get_or_404(id_rol)
    if request.method == "PUT":
        data = request.json
        if 'aplicaciones_ids' in data:
            rol.aplicaciones = []
            for app_id in data['aplicaciones_ids']:
                app = Aplicacion.query.get(app_id)
                if app:
                    rol.aplicaciones.append(app)
            db.session.commit()
            return jsonify({"message": "Permisos actualizados"})
        rol.name = data.get('name', rol.name)
        rol.description = data.get('description', rol.description)
        db.session.commit()
        return jsonify(rol.to_json_dict())

    permisos = [app.id for app in rol.aplicaciones]
    return jsonify({**rol.to_json_dict(), "permisos": permisos})

# --- HELPER PARA LIMPIEZA DE TEXTO (SOLUCIÓN A ERRORES DE PDF) ---
def clean(text):
    """Elimina caracteres no compatibles con Latin-1 para evitar errores en FPDF"""
    if not text: return ""
    return str(text).encode('latin-1', 'replace').decode('latin-1')

# --- API Recibo PDF ---
@app.route("/admin/cobros/recibo/<int:pago_id>")
@login_required
def generar_recibo_pdf(pago_id):
    pago = Pago.query.get_or_404(pago_id)
    
    try:
        monto_en_letras = num2words(int(pago.monto), lang='es')
    except:
        monto_en_letras = str(int(pago.monto))

    try: locale.setlocale(locale.LC_TIME, 'es_ES.UTF-8')
    except locale.Error: 
        try: locale.setlocale(locale.LC_TIME, 'es_ES')
        except locale.Error: locale.setlocale(locale.LC_TIME, '')
    
    # Datos de la empresa parametrizados
    empresa_nombre = get_param('EMPRESA_NOMBRE', 'INMOBILIARIA TU HOGAR S.A.')
    empresa_dir = get_param('EMPRESA_DIRECCION', 'Ruta 6ta, Km 45, Bella Vista, Itapúa')
    empresa_tel = get_param('EMPRESA_TELEFONO', '(0985) 123-456')

    class PDF(FPDF):
        def header(self):
            self.set_font('Helvetica', 'B', 14); self.cell(0, 10, clean(empresa_nombre), 0, 1, 'C')
            self.set_font('Helvetica', '', 9); self.cell(0, 5, clean(empresa_dir), 0, 1, 'C')
            self.cell(0, 5, clean(f'Teléfono: {empresa_tel}'), 0, 1, 'C'); self.ln(5)
            self.line(10, self.get_y(), 200, self.get_y()); self.ln(10)
        def footer(self):
            self.set_y(-40); self.set_font('Helvetica', '', 10); self.cell(0, 10, clean('Firma y Aclaración'), 'T', 0, 'C')

    pdf = PDF()
    pdf.add_page()
    pdf.set_font('Helvetica', 'BU', 20); pdf.cell(0, 15, clean('RECIBO DE DINERO'), 0, 1, 'C'); pdf.ln(10)
    pdf.set_font('Helvetica', '', 11)
    
    cliente_nombre = f'{pago.contrato.cliente.nombre} {pago.contrato.cliente.apellido}'
    
    pdf.cell(40, 8, clean('RECIBÍ DE:'), 0, 0); pdf.set_font('', 'B'); pdf.cell(0, 8, clean(cliente_nombre), 0, 1); pdf.set_font('', '')
    pdf.cell(40, 8, clean('CON C.I./RUC N°:'), 0, 0); pdf.set_font('', 'B'); pdf.cell(0, 8, clean(pago.contrato.cliente.documento), 0, 1); pdf.set_font('', '')
    pdf.cell(40, 8, clean('LA SUMA DE:'), 0, 0); pdf.set_font('', 'B'); pdf.multi_cell(0, 8, clean(f'{monto_en_letras.upper()} GUARANÍES.'), 0, 'L'); pdf.set_font('', '')
    pdf.cell(40, 8, clean('EN CONCEPTO DE:'), 0, 0); pdf.multi_cell(0, 8, clean(f'Pago de cuota N° {pago.cuota.numero_cuota} del contrato N° {pago.contrato.numero_contrato}.'), 0, 'L'); pdf.ln(5)
    
    pdf.set_font('Helvetica', 'B', 10); pdf.cell(60, 10, clean('Fecha de Pago'), 1, 0, 'C'); pdf.cell(60, 10, clean('Forma de Pago'), 1, 0, 'C'); pdf.cell(70, 10, clean('Monto Pagado'), 1, 1, 'C')
    pdf.set_font('Helvetica', '', 10); monto_formateado = "Gs. {:,.0f}".format(pago.monto).replace(',', '.')
    # Ajuste: Mostrar nombre de forma de pago desde la relación
    forma_pago_str = pago.forma_pago_rel.nombre if pago.forma_pago_rel else "Efectivo"
    pdf.cell(60, 10, pago.fecha_pago.strftime('%d/%m/%Y'), 1, 0, 'C'); pdf.cell(60, 10, clean(forma_pago_str), 1, 0, 'C')
    pdf.set_font('', 'B'); pdf.cell(70, 10, clean(monto_formateado), 1, 1, 'R'); pdf.ln(15)
    
    try:
        fecha_larga = pago.fecha_pago.strftime('%d de %B de %Y')
    except:
        fecha_larga = pago.fecha_pago.strftime('%d/%m/%Y')

    pdf.set_font('Helvetica', '', 10); pdf.cell(0, 10, clean(f"Bella Vista, {fecha_larga}."), 0, 1, 'L')
    
    try:
        pdf_output = pdf.output(dest='S').encode('latin-1')
    except (AttributeError, TypeError):
        pdf_output = pdf.output()

    return Response(pdf_output, mimetype="application/pdf", headers={"Content-Disposition": f"inline; filename=recibo_{pago.id}.pdf"})

@app.route("/admin/ventas/factura_pdf/<int:venta_id>")
@login_required
@role_required('Admin', 'Vendedor', 'Empleado')
def generar_factura_pdf(venta_id):
    venta = Venta.query.get_or_404(venta_id)
    cliente = venta.cliente
    try:
        monto_en_letras = num2words(int(venta.total), lang='es')
    except:
        monto_en_letras = str(int(venta.total))

    # Datos parametrizados
    empresa_nombre = get_param('EMPRESA_NOMBRE', 'INMOBILIARIA TU HOGAR S.A.')
    empresa_dir = get_param('EMPRESA_DIRECCION', 'Ruta 6ta, Km 45, Bella Vista, Itapúa')
    empresa_tel = get_param('EMPRESA_TELEFONO', '(0985) 123-456')
    tasa_iva = float(get_param('IVA_DEFECTO', '10')) # IVA por defecto

    class PDF(FPDF):
        def header(self):
            self.set_font('Helvetica', 'B', 14); self.cell(0, 10, clean(empresa_nombre), 0, 1, 'L')
            self.set_font('Helvetica', '', 9); self.cell(0, 5, clean(empresa_dir), 0, 1, 'L')
            self.cell(0, 5, clean(f'Teléfono: {empresa_tel}'), 0, 1, 'L')
            
            # Cuadro de Factura
            self.set_xy(110, 10) # Posición
            self.set_font('Helvetica', 'B', 12)
            self.cell(90, 8, clean('FACTURA'), 1, 1, 'C')
            self.set_x(110)
            self.set_font('Helvetica', 'B', 10)
            self.cell(90, 8, clean(f'N° {venta.numero_factura}'), 1, 1, 'C')
            self.set_x(110)
            self.cell(45, 8, clean('Timbrado N°:'), 'T', 0, 'L')
            self.cell(45, 8, '12345678', 'T', 1, 'R')
            self.set_x(110)
            self.cell(45, 8, clean('Inicio Vigencia:'), 0, 0, 'L')
            self.cell(45, 8, '01/01/2025', 0, 1, 'R')

            self.ln(10)
        def footer(self):
            self.set_y(-15); self.set_font('Helvetica', 'I', 8)
            self.cell(0, 10, clean(f'Página {self.page_no()}'), 0, 0, 'C')

    pdf = PDF()
    pdf.add_page()
    
    # Datos del Cliente
    pdf.set_font('Helvetica', 'B', 11); pdf.cell(0, 8, clean('DATOS DEL CLIENTE'), 1, 1, 'C'); pdf.set_font('', '')
    pdf.cell(40, 8, clean('Fecha de Emisión:'), 'L', 0); pdf.cell(55, 8, venta.fecha_venta.strftime('%d/%m/%Y'), 'R', 0)
    pdf.cell(40, 8, clean('Condición:'), 'L', 0); pdf.cell(55, 8, clean('Contado'), 'R', 1)
    pdf.cell(40, 8, clean('Nombre o Razón Social:'), 'L', 0); pdf.cell(150, 8, clean(f"{cliente.nombre} {cliente.apellido}"), 'R', 1)
    pdf.cell(40, 8, clean('C.I./RUC N°:'), 'L', 0); pdf.cell(150, 8, clean(cliente.documento), 'R', 1)
    pdf.cell(40, 8, clean('Dirección:'), 'LB', 0); pdf.cell(150, 8, clean(cliente.direccion or "Sin dirección"), 'RB', 1)
    
    pdf.ln(10)
    
    # Detalles de la Factura
    pdf.set_font('Helvetica', 'B', 10); 
    pdf.cell(20, 10, clean('Cant.'), 1, 0, 'C'); pdf.cell(100, 10, clean('Descripción'), 1, 0, 'C')
    pdf.cell(35, 10, clean('Precio Unit.'), 1, 0, 'C'); pdf.cell(35, 10, clean('Subtotal'), 1, 1, 'C')
    
    pdf.set_font('Helvetica', '', 10);
    for item in venta.detalles:
        precio_unit_f = "Gs. {:,.0f}".format(item.precio_unitario).replace(',', '.')
        subtotal_f = "Gs. {:,.0f}".format(item.subtotal).replace(',', '.')
        pdf.cell(20, 8, str(item.cantidad), 1, 0, 'C')
        pdf.cell(100, 8, clean(item.descripcion), 1, 0, 'L')
        pdf.cell(35, 8, clean(precio_unit_f), 1, 0, 'R')
        pdf.cell(35, 8, clean(subtotal_f), 1, 1, 'R')
    
    # Cálculos de IVA
    total_float = float(venta.total)
    gravada = total_float / (1 + (tasa_iva / 100))
    iva = total_float - gravada

    # Totales y Desglose de IVA
    pdf.ln(5)
    pdf.cell(120, 8, '', 0, 0)
    pdf.set_font('', '')
    pdf.cell(35, 8, clean(f'Gravadas {int(tasa_iva)}%:'), 0, 0, 'R'); pdf.cell(35, 8, clean("Gs. {:,.0f}".format(gravada).replace(',', '.')), 0, 1, 'R')
    
    pdf.cell(120, 8, '', 0, 0)
    pdf.cell(35, 8, clean(f'IVA {int(tasa_iva)}%:'), 0, 0, 'R'); pdf.cell(35, 8, clean("Gs. {:,.0f}".format(iva).replace(',', '.')), 0, 1, 'R')

    total_f = "Gs. {:,.0f}".format(venta.total).replace(',', '.')
    pdf.set_font('', 'B')
    pdf.cell(155, 10, clean('TOTAL A PAGAR:'), 1, 0, 'R'); pdf.cell(35, 10, clean(total_f), 1, 1, 'R')
    
    pdf.ln(5)
    pdf.set_font('Helvetica', '', 10)
    pdf.cell(40, 8, clean('Total en Letras:'), 0, 0); pdf.multi_cell(0, 8, clean(f'{monto_en_letras.upper()} GUARANÍES.'), 0, 'L')
    
    try:
        pdf_output = pdf.output(dest='S').encode('latin-1')
    except (AttributeError, TypeError):
        pdf_output = pdf.output()

    return Response(pdf_output, mimetype="application/pdf", headers={"Content-Disposition": f"inline; filename=factura_{venta.numero_factura}.pdf"})

@app.route("/admin/inventario/contrato_pdf/<int:contrato_id>")
@login_required
@role_required('Admin', 'Vendedor', 'Empleado')
def generar_contrato_pdf(contrato_id):
    contrato = Contrato.query.get_or_404(contrato_id)
    cliente = contrato.cliente
    lote = contrato.lote
    fraccionamiento = lote.fraccionamiento
    
    # Datos de la empresa
    empresa_nombre = get_param('EMPRESA_NOMBRE', 'INMOBILIARIA TU HOGAR S.A.')
    empresa_ruc = get_param('EMPRESA_RUC', '80012345-6')

    try: locale.setlocale(locale.LC_TIME, 'es_ES.UTF-8')
    except locale.Error: 
        try: locale.setlocale(locale.LC_TIME, 'es_ES')
        except locale.Error: locale.setlocale(locale.LC_TIME, '')
        
    fecha_contrato_larga = contrato.fecha_contrato.strftime('%d de %B de %Y')
    
    try:
        valor_total_letras = num2words(int(contrato.valor_total), lang='es').upper()
        valor_cuota_letras = num2words(int(contrato.valor_cuota), lang='es').upper()
        cuota_inicial_letras = num2words(int(contrato.cuota_inicial), lang='es').upper()
    except:
        valor_total_letras = str(int(contrato.valor_total))
        valor_cuota_letras = str(int(contrato.valor_cuota))
        cuota_inicial_letras = str(int(contrato.cuota_inicial))

    class PDF(FPDF):
        def header(self):
            self.set_font('Helvetica', 'B', 14)
            self.cell(0, 10, clean('CONTRATO PRIVADO DE COMPRA-VENTA DE INMUEBLE'), 0, 1, 'C')
            self.ln(5)
        def footer(self):
            self.set_y(-30)
            self.set_font('Helvetica', '', 10)
            self.cell(90, 10, '__________________________', 0, 0, 'C')
            self.cell(90, 10, '__________________________', 0, 1, 'C')
            self.cell(90, 10, clean('Firma del VENDEDOR'), 0, 0, 'C')
            self.cell(90, 10, clean('Firma del COMPRADOR'), 0, 1, 'C')
            self.set_y(-15)
            self.set_font('Helvetica', 'I', 8)
            self.cell(0, 10, clean(f'Página {self.page_no()}'), 0, 0, 'C')

    pdf = PDF()
    pdf.add_page()
    pdf.set_font('Helvetica', '', 10)
    
    txt_intro = f"En la ciudad de Bella Vista, Itapúa, República del Paraguay, a los {fecha_contrato_larga}. Entre la empresa {empresa_nombre}, con RUC N° {empresa_ruc}, representada en este acto por el Sr. Gerente, en adelante denominado EL VENDEDOR, por una parte; y por la otra parte el/la Sr./Sra. {cliente.nombre.upper()} {cliente.apellido.upper()}, con {cliente.tipo_documento.nombre if cliente.tipo_documento else 'CI'} N° {cliente.documento}, domiciliado en {cliente.direccion or 'N/A'}, en adelante denominado EL COMPRADOR, convienen en celebrar el presente Contrato Privado de Compra-Venta de Inmueble, sujeto a las siguientes cláusulas:"
    pdf.multi_cell(0, 5, clean(txt_intro), 0, 'J')
    pdf.ln(5)
    
    pdf.set_font('', 'B')
    pdf.cell(0, 5, clean('PRIMERA: DEL OBJETO DEL CONTRATO'), 0, 1, 'L')
    pdf.set_font('', '')
    
    txt_primera = f"EL VENDEDOR transfiere en venta real y definitiva a favor de EL COMPRADOR, el Lote de Terreno individualizado como Lote N° {lote.numero_lote}, Manzana N° {lote.manzana}, ubicado en el Fraccionamiento '{fraccionamiento.nombre}', con una superficie de {lote.metros_cuadrados} metros cuadrados."
    pdf.multi_cell(0, 5, clean(txt_primera), 0, 'J')
    pdf.ln(5)
    
    pdf.set_font('', 'B')
    pdf.cell(0, 5, clean('SEGUNDA: DEL PRECIO Y FORMA DE PAGO'), 0, 1, 'L')
    pdf.set_font('', '')
    
    txt_segunda = f"El precio total de la venta se fija en la suma de GUARANÍES {valor_total_letras} (Gs. {int(contrato.valor_total):,})."
    pdf.multi_cell(0, 5, clean(txt_segunda), 0, 'J')
    
    if contrato.cuota_inicial > 0:
        txt_inicial = f"Que EL COMPRADOR abona en este acto la suma de GUARANÍES {cuota_inicial_letras} (Gs. {int(contrato.cuota_inicial):,}) como entrega inicial."
        pdf.multi_cell(0, 5, clean(txt_inicial), 0, 'J')
        
    fecha_venc = contrato.cuotas[0].fecha_vencimiento.strftime('%d/%m/%Y') if contrato.cuotas else 'N/A'
    txt_cuotas = f"El saldo restante será abonado en {contrato.cantidad_cuotas} cuotas mensuales, iguales y consecutivas de GUARANÍES {valor_cuota_letras} (Gs. {int(contrato.valor_cuota):,}). El vencimiento de la primera cuota operará el día {fecha_venc}."
    pdf.multi_cell(0, 5, clean(txt_cuotas), 0, 'J')
    pdf.ln(5)

    pdf.set_font('', 'B')
    pdf.cell(0, 5, clean('TERCERA: DE LA POSESIÓN Y ESCRITURACIÓN'), 0, 1, 'L')
    pdf.set_font('', '')
    pdf.multi_cell(0, 5, clean("EL COMPRADOR toma posesión del inmueble en este acto. La escrituración y transferencia definitiva se realizará una vez cancelada la totalidad del precio de venta, corriendo los gastos de escribanía por cuenta exclusiva de EL COMPRADOR."), 0, 'J')
    pdf.ln(10)
    
    pdf.multi_cell(0, 5, clean("En prueba de conformidad, las partes firman dos ejemplares de un mismo tenor y a un solo efecto en el lugar y fecha arriba mencionados."), 0, 'J')
    
    try:
        pdf_output = pdf.output(dest='S').encode('latin-1')
    except (AttributeError, TypeError):
        pdf_output = pdf.output()

    return Response(pdf_output, mimetype="application/pdf", headers={"Content-Disposition": f"inline; filename=contrato_{contrato.numero_contrato}.pdf"})

# --- APIs CLIENTES, CONTRATOS y COBROS ---
@app.route("/api/admin/clientes", methods=["GET", "POST"])
@login_required
@role_required('Admin', 'Vendedor', 'Empleado')
def api_clientes():
    if request.method == "POST":
        data = request.json
        if Cliente.query.filter_by(documento=data["documento"]).first():
            return jsonify({"error": "Ya existe un cliente con este documento"}), 400
        
        ciudad_id = data.get('ciudad_id')
        barrio_id = data.get('barrio_id')

        nuevo_cliente = Cliente(
            tipo_documento_id=data.get('tipo_documento_id'), 
            documento=data['documento'],
            nombre=data['nombre'].strip().title(), 
            apellido=data['apellido'].strip().title(),
            telefono=data.get('telefono'), 
            email=data.get('email'),
            direccion=data.get('direccion'),
            
            # NUEVOS CAMPOS DE DIRECCIÓN
            ciudad_id=int(ciudad_id) if ciudad_id else None,
            barrio_id=int(barrio_id) if barrio_id else None,

            profesion_id=data.get('profesion_id'),
            tipo_cliente_id=data.get('tipo_cliente_id'),
            estado=data.get('estado', 'activo')
        )
        db.session.add(nuevo_cliente)
        db.session.commit()
        return jsonify(nuevo_cliente.to_dict()), 201

    clientes = Cliente.query.order_by(Cliente.nombre).all()
    return jsonify([c.to_dict() for c in clientes])

@app.route("/api/admin/clientes/<int:cid>", methods=["GET", "PUT", "DELETE"])
@login_required
@role_required('Admin', 'Cajero', 'Empleado')
def api_cliente_detalle(cid):
    cliente = Cliente.query.get_or_404(cid)
    if request.method == "PUT":
        data = request.json
        if 'documento' in data and data['documento'] != cliente.documento and Cliente.query.filter_by(documento=data['documento']).first():
            return jsonify({"error": "Ya existe otro cliente con ese documento"}), 400
        
        cliente.tipo_documento_id = data.get('tipo_documento_id', cliente.tipo_documento_id)
        cliente.documento = data.get('documento', cliente.documento)
        cliente.nombre = data.get('nombre', cliente.nombre)
        cliente.apellido = data.get('apellido', cliente.apellido)
        cliente.telefono = data.get('telefono', cliente.telefono)
        cliente.email = data.get('email', cliente.email)
        cliente.direccion = data.get('direccion', cliente.direccion)
        
        # Actualización de dirección
        if 'ciudad_id' in data:
            cliente.ciudad_id = int(data['ciudad_id']) if data['ciudad_id'] else None
        if 'barrio_id' in data:
            cliente.barrio_id = int(data['barrio_id']) if data['barrio_id'] else None

        cliente.profesion_id = data.get('profesion_id', cliente.profesion_id)
        cliente.tipo_cliente_id = data.get('tipo_cliente_id', cliente.tipo_cliente_id)
        cliente.estado = data.get('estado', cliente.estado)
        db.session.commit()
        return jsonify(cliente.to_dict())

    if request.method == "DELETE":
        if cliente.contratos:
            return jsonify({"error": "No se puede eliminar, tiene contratos asociados."}), 400
        db.session.delete(cliente)
        db.session.commit()
        return jsonify({"message": "Cliente eliminado exitosamente."})
    return jsonify(cliente.to_dict())

@app.route("/api/admin/contratos", methods=["GET", "POST"])
@login_required
def api_contratos():
    if request.method == "POST":
        data = request.get_json(force=True)
        if not all(k in data for k in ['numero_contrato', 'cliente_id', 'lote_id', 'fecha_contrato']):
            return jsonify({"error": "Faltan datos requeridos"}), 400

        if Contrato.query.filter_by(numero_contrato=data["numero_contrato"]).first(): 
            return jsonify({"error": "Ya existe un contrato con este número"}), 400
        
        lote = Lote.query.get(data["lote_id"])
        if not lote: return jsonify({"error": "Lote no encontrado"}), 404
        
        if 'precio_id' in data and data['precio_id']:
            plan = ListaPrecioLote.query.get(data['precio_id'])
            if not plan: return jsonify({"error": "Plan de precios no válido"}), 400
            
            valor_total = float(plan.precio_total)
            cantidad_cuotas = plan.cantidad_cuotas
            valor_cuota_calculado = float(plan.precio_cuota)
        else:
            valor_total = float(data.get("valor_total", 0))
            cantidad_cuotas = int(data.get("cantidad_cuotas", 0))
            valor_cuota_calculado = float(data.get("valor_cuota", 0))
            if cantidad_cuotas > 0 and valor_cuota_calculado == 0:
                valor_cuota_calculado = valor_total / cantidad_cuotas

        contrato = Contrato(
            numero_contrato=data["numero_contrato"], 
            cliente_id=data["cliente_id"], 
            lote_id=data["lote_id"], 
            fecha_contrato=datetime.strptime(data["fecha_contrato"], "%Y-%m-%d").date(), 
            valor_total=valor_total, 
            cuota_inicial=float(data.get("cuota_inicial", 0)), 
            cantidad_cuotas=cantidad_cuotas, 
            valor_cuota=valor_cuota_calculado,
            tipo_contrato=data.get("tipo_contrato", "venta"), 
            observaciones=data.get("observaciones")
        )
        db.session.add(contrato)
        db.session.commit()

        for i in range(1, contrato.cantidad_cuotas + 1):
            fecha_vencimiento = contrato.fecha_contrato + timedelta(days=30*i)
            cuota = Cuota(
                contrato_id=contrato.id, 
                numero_cuota=i, 
                fecha_vencimiento=fecha_vencimiento, 
                valor_cuota=contrato.valor_cuota
            )
            db.session.add(cuota)
            
        lote.estado = "vendido" if contrato.tipo_contrato == "venta" else "reservado"
        db.session.commit()
        return jsonify({"ok": True, "id": contrato.id}), 201

    contratos = Contrato.query.order_by(Contrato.fecha_contrato.desc()).all()
    return jsonify([c.to_dict() for c in contratos])

@app.route("/api/admin/contratos/<int:contrato_id>", methods=["GET", "PATCH"])
@login_required
def api_contrato_detalle(contrato_id):
    contrato = Contrato.query.get_or_404(contrato_id)
    if request.method == "PATCH":
        data = request.get_json(force=True)
        if 'numero_contrato' in data: contrato.numero_contrato = data['numero_contrato']
        if 'fecha_contrato' in data and data['fecha_contrato']: contrato.fecha_contrato = datetime.strptime(data['fecha_contrato'], "%Y-%m-%d").date()
        if 'estado' in data: contrato.estado = data['estado']
        contrato.observaciones = data.get('observaciones', contrato.observaciones)
        db.session.commit()
        return jsonify({"ok": True, "message": "Contrato actualizado"})
    return jsonify(contrato.to_dict())

@app.route("/api/admin/lotes-disponibles")
@login_required
def api_lotes_disponibles(): 
    lotes = Lote.query.filter(Lote.estado.in_(["disponible", "reservado"])).all()
    return jsonify([{"id": l.id, "texto": f"{l.fraccionamiento.nombre} - M{l.manzana} L{l.numero_lote} - Gs. {int(l.precio):,}", "precio": float(l.precio)} for l in lotes])

@app.route("/admin/inventario/reportes/contratos")
@login_required
def reporte_contratos_view(): 
    contratos = Contrato.query.order_by(Contrato.fecha_contrato.desc()).all()
    return render_template("reportes/listado_contratos.html", contratos=contratos)

@app.route("/api/reportes/arqueo", methods=["POST"])
@login_required
def api_reporte_arqueo():
    data = request.json
    caja_id = data.get('caja_id')
    fecha_desde = datetime.strptime(data['fecha_desde'], "%Y-%m-%d")
    fecha_hasta = datetime.strptime(data['fecha_hasta'], "%Y-%m-%d") + timedelta(days=1)

    query = MovimientoCaja.query.filter(
        MovimientoCaja.caja_id == caja_id,
        MovimientoCaja.fecha_hora >= fecha_desde,
        MovimientoCaja.fecha_hora < fecha_hasta
    )
    
    movimientos = query.order_by(MovimientoCaja.fecha_hora).all()
    
    ingresos = sum(m.monto for m in movimientos if m.tipo_movimiento == 'ingreso')
    egresos = sum(m.monto for m in movimientos if m.tipo_movimiento == 'egreso')
    saldo = ingresos - egresos
    
    resultados = [{
        "fecha": m.fecha_hora.strftime("%d/%m/%Y %H:%M"),
        "tipo": m.tipo_movimiento,
        "concepto": m.concepto,
        "monto": float(m.monto),
        "usuario": f"{m.usuario.nombre} {m.usuario.apellido}" if m.usuario else "Sistema"
    } for m in movimientos]
    
    return jsonify({
        "movimientos": resultados,
        "total_ingresos": float(ingresos),
        "total_egresos": float(egresos),
        "saldo_periodo": float(saldo)
    })

@app.route("/api/reportes/extracto", methods=["POST"])
@login_required
def api_reporte_extracto():
    data = request.json
    cuenta_id = data.get('cuenta_id')
    fecha_desde = datetime.strptime(data['fecha_desde'], "%Y-%m-%d")
    fecha_hasta = datetime.strptime(data['fecha_hasta'], "%Y-%m-%d") + timedelta(days=1)

    query = DepositoBancario.query.filter(
        DepositoBancario.cuenta_id == cuenta_id,
        DepositoBancario.fecha_deposito >= fecha_desde.date(),
        DepositoBancario.fecha_deposito < fecha_hasta.date(),
        DepositoBancario.estado == 'confirmado'
    )
    
    depositos = query.order_by(DepositoBancario.fecha_deposito).all()
    
    resultados = [{
        "fecha": d.fecha_deposito.strftime("%d/%m/%Y"),
        "referencia": d.referencia,
        "concepto": d.concepto,
        "monto": float(d.monto)
    } for d in depositos]
    
    return jsonify(resultados)

@app.route("/api/admin/caja/estado")
@login_required
def api_caja_estado():
    caja_id = session.get("caja_id")
    if caja_id:
        caja = Caja.query.get(caja_id)
        if caja and caja.abierta:
            return jsonify({
                "caja_abierta": True, 
                "caja_id": caja.id, 
                "caja_descripcion": caja.descripcion,
                "saldo_actual": float(caja.saldo_actual)
            })
    session.pop("caja_id", None)
    return jsonify({"caja_abierta": False})

@app.route("/api/admin/caja/abrir", methods=["POST"])
@login_required
def api_abrir_caja():
    data = request.json

    caja_id_seleccionada = data.get("caja_id", 1)
    monto_apertura = float(data.get("monto_apertura", 0))
    
    caja = Caja.query.get(caja_id_seleccionada)
    if not caja:
        caja = Caja(id=caja_id_seleccionada, descripcion="Caja General", sucursal="Central", saldo_actual=0, abierta=False)
        db.session.add(caja)
        db.session.commit()

    if caja.abierta:
        return jsonify({"error": "Esta caja ya está abierta"}), 400
        
    caja.abierta = True
    caja.saldo_actual = monto_apertura
    
    apertura = MovimientoCaja(
        caja_id=caja.id,
        tipo_movimiento="ingreso",
        monto=monto_apertura,
        concepto="Apertura de Caja",
        fecha_hora=datetime.utcnow(),
        usuario_id=current_user.id
    )
    db.session.add(apertura)
    db.session.commit()
    
    session["caja_id"] = caja.id
    return jsonify({"ok": True, "message": f"Caja '{caja.descripcion}' abierta con Gs. {monto_apertura:,.0f}"})

@app.route("/api/admin/caja/cerrar", methods=["POST"])
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
    
    cierre = MovimientoCaja(
        caja_id=caja.id,
        tipo_movimiento="egreso",
        monto=saldo_cierre,
        concepto="Cierre de Caja",
        fecha_hora=datetime.utcnow(),
        usuario_id=current_user.id
    )
    db.session.add(cierre)
    
    caja.abierta = False
    caja.saldo_actual = 0
    caja.ultimo_arqueo = datetime.utcnow()
    db.session.commit()
    
    session.pop("caja_id", None)
    return jsonify({"ok": True, "message": f"Caja '{caja.descripcion}' cerrada con saldo Gs. {saldo_cierre:,.0f}"})

@app.route("/api/admin/clientes/buscar")
@login_required
def api_buscar_clientes(): 
    query = request.args.get("q", "")
    search_term = f"%{query}%"
    clientes = Cliente.query.filter(or_((Cliente.nombre + " " + Cliente.apellido).ilike(search_term), Cliente.documento.ilike(search_term))).limit(10).all()
    return jsonify([c.to_dict() for c in clientes])

@app.route("/api/admin/clientes/<int:cliente_id>/cuotas")
@login_required
def api_get_cuotas_por_cliente(cliente_id):
    cliente = Cliente.query.get_or_404(cliente_id)
    contratos_activos_ids = [c.id for c in cliente.contratos if c.estado == 'activo']
    if not contratos_activos_ids: return jsonify([])
    cuotas = Cuota.query.filter(Cuota.contrato_id.in_(contratos_activos_ids), Cuota.estado.in_(['pendiente', 'vencida'])).order_by(Cuota.fecha_vencimiento.asc()).all()
    for cuota in cuotas:
        if cuota.fecha_vencimiento < date.today() and cuota.estado == 'pendiente': 
            cuota.estado = 'vencida'
    db.session.commit()
    return jsonify([{"id": c.id, "numero_cuota": c.numero_cuota, "fecha_vencimiento": c.fecha_vencimiento.isoformat(), "valor_cuota": float(c.valor_cuota), "estado": c.estado, "contrato_id": c.contrato_id, "numero_contrato": c.contrato.numero_contrato} for c in cuotas])

@app.route("/api/admin/pagos", methods=["POST"])
@login_required
def api_registrar_pago():
    # Validar Caja solo si es EFECTIVO (asumimos ID 1 = Efectivo)
    data = request.get_json(force=True)
    forma_pago_id = int(data.get("forma_pago_id"))
    monto_pagado = Decimal(str(data["monto"]))
    
    caja = None
    if forma_pago_id == 1: # Efectivo
        caja_id = session.get("caja_id")
        if not caja_id: return jsonify({"error": "Para cobros en Efectivo, debe abrir la Caja."}), 403
        caja = Caja.query.get(caja_id)
        if not caja or not caja.abierta: return jsonify({"error": "Caja cerrada."}), 403

    cuota = Cuota.query.get(int(data["cuota_id"]))
    if not cuota: return jsonify({"error": "La cuota no existe."}), 404
    if cuota.estado == 'pagada': return jsonify({"error": "Esta cuota ya fue pagada."}), 400
    
    # Crear el Pago
    nuevo_pago = Pago(
        contrato_id=cuota.contrato_id, 
        cuota_id=cuota.id, 
        fecha_pago=datetime.strptime(data["fecha_pago"], "%Y-%m-%d"), 
        monto=monto_pagado, 
        forma_pago_id=forma_pago_id,
        referencia=data.get("referencia"), 
        observaciones=data.get("observaciones"), 
        usuario_id=current_user.id,
        cuenta_bancaria_id=data.get("cuenta_bancaria_id") # Guardamos destino
    )
    db.session.add(nuevo_pago)
    
    # Actualizar Cuota
    cuota.estado = 'pagada'
    cuota.fecha_pago = nuevo_pago.fecha_pago
    cuota.valor_pagado = monto_pagado
    
    # --- LÓGICA DE MOVIMIENTO DE DINERO ---
    
    # OPCIÓN A: Si es EFECTIVO -> Mover Caja
    if forma_pago_id == 1 and caja:
        mov_caja = MovimientoCaja(
            caja_id=caja.id,
            tipo_movimiento="ingreso",
            monto=monto_pagado,
            concepto=f"Cobro cuota N°{cuota.numero_cuota} - Contrato {cuota.contrato.numero_contrato}",
            fecha_hora=datetime.now(),
            pago_id=nuevo_pago.id,
            usuario_id=current_user.id
        )
        db.session.add(mov_caja)
        caja.saldo_actual = (caja.saldo_actual or Decimal(0)) + monto_pagado

    # OPCIÓN B: Si seleccionó BANCO -> Crear Depósito Automático
    elif data.get("cuenta_bancaria_id"):
        cuenta_bancaria = CuentaBancaria.query.get(data["cuenta_bancaria_id"])
        if cuenta_bancaria:
            # Creamos un registro en depositos_bancarios para que salga en el extracto
            deposito = DepositoBancario(
                cuenta_id=cuenta_bancaria.id,
                fecha_deposito=nuevo_pago.fecha_pago,
                monto=monto_pagado,
                referencia=data.get("referencia") or "Cobro Automático",
                concepto=f"Cobro Cuota {cuota.numero_cuota} - {cuota.contrato.cliente.nombre} {cuota.contrato.cliente.apellido}",
                estado='confirmado',
                usuario_id=current_user.id
            )
            db.session.add(deposito)
            # Actualizar saldo cuenta
            cuenta_bancaria.saldo = (cuenta_bancaria.saldo or Decimal(0)) + monto_pagado

    db.session.commit()
    return jsonify({"ok": True, "message": "Pago registrado exitosamente.", "pago_id": nuevo_pago.id})

# --- APIs VENTAS ---
@app.route("/api/admin/vendedores")
@login_required
def api_buscar_vendedores():
    vendedores = Funcionario.query.filter_by(es_vendedor=True, estado='activo').all()
    return jsonify([v.to_dict() for v in vendedores])

@app.route("/api/admin/ventas", methods=["GET", "POST"])
@login_required
@role_required('Admin', 'Vendedor', 'Empleado')
def api_ventas():
    if request.method == "POST":
        data = request.json
        
        if not all(k in data for k in ['cliente_id', 'fecha_venta', 'detalles']): 
            return jsonify({"error": "Faltan datos requeridos (cliente, fecha, detalles)"}), 400
        if not data['detalles']: 
            return jsonify({"error": "La factura debe tener al menos un ítem"}), 400
        
        tipo_factura = TipoComprobante.query.filter(db.func.lower(TipoComprobante.nombre) == 'factura').first()
        if not tipo_factura:
            tipo_factura = TipoComprobante(nombre="Factura")
            db.session.add(tipo_factura)
            db.session.commit()
            
        talonario = Talonario.query.filter_by(
            activo=True, 
            tipo_comprobante_id=tipo_factura.id
        ).first()
        
        if not talonario:
            return jsonify({"error": "No se encontró un talonario activo para 'Factura'"}), 400
        
        if talonario.numero_actual > talonario.numero_fin:
            talonario.activo = False
            db.session.commit()
            return jsonify({"error": f"El talonario {talonario.timbrado} ha llegado a su número final"}), 400
            
        nro_factura = f"{talonario.punto_expedicion}-{talonario.caja}-{talonario.numero_actual:07d}"
        
        if Venta.query.filter_by(numero_factura=nro_factura).first(): 
            return jsonify({"error": "El número de factura generado ya existe (Error de concurrencia)"}), 400
        
        try:
            total_factura = sum(float(item['subtotal']) for item in data['detalles'])
            
            nueva_venta = Venta(
                cliente_id=data['cliente_id'], 
                vendedor_id=data.get('vendedor_id'), 
                talonario_id=talonario.id, # CONEXIÓN IMPORTANTE
                fecha_venta=datetime.strptime(data['fecha_venta'], "%Y-%m-%d").date(), 
                numero_factura=nro_factura,
                total=total_factura
            )
            db.session.add(nueva_venta)
            
            talonario.numero_actual += 1
            
            db.session.flush()
            
            for item in data['detalles']:
                detalle = VentaDetalle(
                    venta_id=nueva_venta.id, 
                    lote_id=item.get('lote_id'), 
                    impuesto_id=item.get('impuesto_id'),
                    descripcion=item['descripcion'], 
                    cantidad=int(item['cantidad']), 
                    precio_unitario=float(item['precio_unitario']), 
                    subtotal=float(item['subtotal'])
                )
                db.session.add(detalle)
                
            db.session.commit()
            return jsonify(nueva_venta.to_dict()), 201
            
        except Exception as e:
            db.session.rollback()
            return jsonify({"error": "Error interno del servidor", "details": str(e)}), 500
            
    ventas = Venta.query.order_by(Venta.fecha_venta.desc()).all()
    return jsonify([v.to_dict() for v in ventas])

@app.route("/api/admin/ventas/<int:venta_id>", methods=["GET", "DELETE"])
@login_required
@role_required('Admin', 'Vendedor', 'Empleado')
def api_venta_detalle(venta_id):
    venta = Venta.query.get_or_404(venta_id)
    if request.method == "DELETE":
        if venta.estado == 'anulada': return jsonify({"error": "La venta ya está anulada"}), 400
        venta.estado = 'anulada'
        db.session.commit()
        return jsonify({"message": "Venta anulada correctamente"})
    return jsonify(venta.to_dict())

# --- APIs GASTOS ---
@app.route("/api/admin/categorias-gasto", methods=["GET", "POST"])
@login_required
@role_required('Admin', 'Empleado')
def api_categorias_gasto():
    if request.method == "POST":
        data = request.json
        if not data.get('nombre'): 
            return jsonify({"error": "El nombre es requerido"}), 400
        if CategoriaGasto.query.filter_by(nombre=data['nombre']).first(): 
            return jsonify({"error": "Esa categoría ya existe"}), 400
        
        categoria = CategoriaGasto(
            nombre=data['nombre'], 
            descripcion=data.get('descripcion')
        )
        db.session.add(categoria)
        db.session.commit()
        return jsonify(categoria.to_dict()), 201
    
    categorias = CategoriaGasto.query.order_by(CategoriaGasto.nombre).all()
    return jsonify([c.to_dict() for c in categorias])

@app.route("/api/admin/categorias-gasto/<int:cid>", methods=["GET", "PUT", "DELETE"])
@login_required
@role_required('Admin', 'Empleado')
def api_categoria_gasto_detalle(cid):
    categoria = CategoriaGasto.query.get_or_404(cid)
    
    if request.method == "PUT":
        data = request.json
        if 'nombre' in data and data['nombre'] != categoria.nombre and CategoriaGasto.query.filter_by(nombre=data['nombre']).first():
            return jsonify({"error": "Ya existe otra categoría con ese nombre"}), 400
        
        categoria.nombre = data.get('nombre', categoria.nombre)
        categoria.descripcion = data.get('descripcion', categoria.descripcion)
        db.session.commit()
        return jsonify(categoria.to_dict())

    if request.method == "DELETE":
        if categoria.gastos: 
            return jsonify({"error": "No se puede eliminar, tiene gastos asociados."}), 400
        db.session.delete(categoria)
        db.session.commit()
        return jsonify({"message": "Categoría eliminada"})
    
    return jsonify(categoria.to_dict())

@app.route("/api/admin/proveedores", methods=["GET", "POST"])
@login_required
@role_required('Admin', 'Empleado')
def api_proveedores():
    if request.method == "POST":
        data = request.json
        if not data.get('razon_social') or not data.get('ruc'): return jsonify({"error": "Razón Social y RUC son requeridos"}), 400
        if Proveedor.query.filter_by(ruc=data['ruc']).first(): return jsonify({"error": "Ya existe un proveedor con ese RUC"}), 400
        proveedor = Proveedor(razon_social=data['razon_social'], ruc=data['ruc'], telefono=data.get('telefono'), direccion=data.get('direccion'))
        db.session.add(proveedor)
        db.session.commit()
        return jsonify(proveedor.to_dict()), 201
    proveedores = Proveedor.query.order_by(Proveedor.razon_social).all()
    return jsonify([p.to_dict() for p in proveedores])

@app.route("/api/admin/proveedores/<int:pid>", methods=["GET", "PUT", "DELETE"])
@login_required
@role_required('Admin', 'Empleado')
def api_proveedor_detalle(pid):
    proveedor = Proveedor.query.get_or_404(pid)
    if request.method == "PUT":
        data = request.json
        if 'ruc' in data and data['ruc'] != proveedor.ruc and Proveedor.query.filter_by(ruc=data['ruc']).first():
            return jsonify({"error": "Ya existe otro proveedor con ese RUC"}), 400
        proveedor.razon_social = data.get('razon_social', proveedor.razon_social)
        proveedor.ruc = data.get('ruc', proveedor.ruc)
        proveedor.telefono = data.get('telefono', proveedor.telefono)
        proveedor.direccion = data.get('direccion', proveedor.direccion)
        db.session.commit()
        return jsonify(proveedor.to_dict())
    if request.method == "DELETE":
        if proveedor.gastos: return jsonify({"error": "No se puede eliminar, tiene gastos asociados."}), 400
        db.session.delete(proveedor)
        db.session.commit()
        return jsonify({"message": "Proveedor eliminado"})
    return jsonify(proveedor.to_dict())

@app.route("/api/admin/gastos", methods=["GET", "POST"])
@login_required
@role_required('Admin', 'Cajero', 'Empleado')
def api_gastos():
    if request.method == "POST":
        data = request.json
        if not all(k in data for k in ['proveedor_id', 'categoria_gasto_id', 'fecha_factura', 'monto']):
            return jsonify({"error": "Faltan datos requeridos para el gasto"}), 400
        gasto = Gasto(
            proveedor_id=data['proveedor_id'], 
            categoria_gasto_id=data['categoria_gasto_id'],
            detalle=data.get('detalle'),
            numero_factura=data.get('numero_factura'),
            fecha_factura=datetime.strptime(data['fecha_factura'], "%Y-%m-%d").date(),
            monto=float(data['monto']), estado=data.get('estado', 'pendiente')
        )
        db.session.add(gasto)
        db.session.commit()
        return jsonify(gasto.to_dict()), 201
    gastos = Gasto.query.order_by(Gasto.fecha_factura.desc()).all()
    return jsonify([g.to_dict() for g in gastos])

@app.route("/api/admin/gastos/<int:gid>", methods=["GET", "DELETE"])
@login_required
@role_required('Admin', 'Cajero', 'Empleado')
def api_gasto_detalle(gid):
    gasto = Gasto.query.get_or_404(gid)
    if request.method == "DELETE":
        if gasto.estado == 'anulado': return jsonify({"error": "El gasto ya está anulado"}), 400
        gasto.estado = 'anulado'
        db.session.commit()
        return jsonify({"message": "Gasto anulado correctamente"})
    return jsonify(gasto.to_dict())

# --- APIs TESORERÍA ---
@app.route("/api/admin/entidades-financieras", methods=["GET", "POST"])
@login_required
@role_required('Admin', 'Cajero')
def api_entidades_financieras():
    if request.method == "POST":
        data = request.json
        if not data.get('nombre'): return jsonify({"error": "El nombre es requerido"}), 400
        if EntidadFinanciera.query.filter_by(nombre=data['nombre']).first(): return jsonify({"error": "La entidad ya existe"}), 400
        entidad = EntidadFinanciera(nombre=data['nombre'])
        db.session.add(entidad); db.session.commit()
        return jsonify(entidad.to_dict()), 201
    return jsonify([e.to_dict() for e in EntidadFinanciera.query.order_by(EntidadFinanciera.nombre).all()])

@app.route("/api/admin/entidades-financieras/<int:eid>", methods=["PUT", "DELETE"])
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
        return jsonify(entidad.to_dict())
    if request.method == "DELETE":
        if entidad.cuentas: return jsonify({"error": "No se puede eliminar, tiene cuentas asociadas."}), 400
        db.session.delete(entidad); db.session.commit()
        return jsonify({"message": "Entidad eliminada"})

@app.route("/api/admin/cuentas-bancarias", methods=["GET", "POST"])
@login_required
@role_required('Admin', 'Cajero')
def api_cuentas_bancarias():
    if request.method == "POST":
        data = request.json
        if not all(k in data for k in ['entidad_id', 'numero_cuenta', 'titular', 'tipo_cuenta', 'moneda']):
            return jsonify({"error": "Faltan datos requeridos"}), 400
        if CuentaBancaria.query.filter_by(numero_cuenta=data['numero_cuenta']).first():
            return jsonify({"error": "Ese número de cuenta ya existe"}), 400
        cuenta = CuentaBancaria(entidad_id=data['entidad_id'], numero_cuenta=data['numero_cuenta'], titular=data['titular'], tipo_cuenta=data['tipo_cuenta'], moneda=data['moneda'])
        db.session.add(cuenta); db.session.commit()
        return jsonify(cuenta.to_dict()), 201
    return jsonify([c.to_dict() for c in CuentaBancaria.query.order_by(CuentaBancaria.numero_cuenta).all()])

@app.route("/api/admin/cuentas-bancarias/<int:cid>", methods=["PUT", "DELETE"])
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
        return jsonify(cuenta.to_dict())
    if request.method == "DELETE":
        if cuenta.depositos: return jsonify({"error": "No se puede eliminar, tiene depósitos asociados."}), 400
        db.session.delete(cuenta); db.session.commit()
        return jsonify({"message": "Cuenta eliminada"})

@app.route("/api/admin/depositos", methods=["GET", "POST"])
@login_required
@role_required('Admin', 'Cajero')
def api_depositos():
    if request.method == "POST":
        data = request.json
        if not all(k in data for k in ['cuenta_id', 'fecha_deposito', 'monto']):
            return jsonify({"error": "Faltan datos requeridos"}), 400
        cuenta = CuentaBancaria.query.get(data['cuenta_id'])
        if not cuenta: return jsonify({"error": "La cuenta bancaria no existe"}), 404
        
        monto = float(data['monto'])
        deposito = DepositoBancario(
            cuenta_id=data['cuenta_id'],
            fecha_deposito=datetime.strptime(data['fecha_deposito'], "%Y-%m-%d").date(),
            monto=monto, referencia=data.get('referencia'),
            concepto=data.get('concepto'), usuario_id=current_user.id
        )
        cuenta.saldo = (cuenta.saldo or 0) + monto
        db.session.add(deposito)
        db.session.commit()
        return jsonify(deposito.to_dict()), 201
    depositos = DepositoBancario.query.order_by(DepositoBancario.fecha_deposito.desc()).all()
    return jsonify([d.to_dict() for d in depositos])

@app.route("/api/admin/depositos/<int:did>", methods=["DELETE"])
@login_required
@role_required('Admin', 'Cajero')
def api_deposito_detalle(did):
    deposito = DepositoBancario.query.get_or_404(did)
    if deposito.estado == 'anulado':
        return jsonify({"error": "El depósito ya está anulado"}), 400
    
    cuenta = deposito.cuenta
    cuenta.saldo -= deposito.monto
    deposito.estado = 'anulado'
    db.session.commit()
    return jsonify({"message": "Depósito anulado correctamente"})

@app.route("/api/admin/transferencias", methods=["POST"])
@login_required
@role_required('Admin', 'Cajero')
def api_transferencias_bancarias():
    data = request.json
    if not all(k in data for k in ['cuenta_origen_id', 'cuenta_destino_id', 'monto', 'fecha']):
        return jsonify({"error": "Faltan datos requeridos (origen, destino, monto, fecha)"}), 400

    monto = float(data['monto'])
    if monto <= 0:
        return jsonify({"error": "El monto debe ser positivo"}), 400

    cuenta_origen = CuentaBancaria.query.get(data['cuenta_origen_id'])
    cuenta_destino = CuentaBancaria.query.get(data['cuenta_destino_id'])
    
    if not cuenta_origen or not cuenta_destino:
        return jsonify({"error": "Una o ambas cuentas no existen"}), 404
    
    if (cuenta_origen.saldo or 0) < monto:
        return jsonify({"error": "Saldo insuficiente en la cuenta de origen"}), 400
    
    try:
        fecha_transferencia = datetime.strptime(data['fecha'], "%Y-%m-%d").date()
        concepto = data.get('concepto', 'Transferencia entre cuentas')
        
        # --- LÓGICA MULTIMONEDA INTEGRADA ---
        moneda_origen = cuenta_origen.moneda
        moneda_destino = cuenta_destino.moneda
        monto_debito = monto
        monto_credito = monto # Por defecto si son iguales

        if moneda_origen != moneda_destino:
            cotizacion = Cotizacion.query.filter_by(
                fecha=fecha_transferencia,
                moneda_origen=moneda_origen if moneda_origen == 'USD' else moneda_destino,
                moneda_destino=moneda_destino if moneda_origen == 'USD' else moneda_origen
            ).first()
            
            # Si no hay cotización específica del día, buscar la última disponible
            if not cotizacion:
                cotizacion = Cotizacion.query.order_by(Cotizacion.fecha.desc()).first()
            
            if not cotizacion:
                return jsonify({"error": "No hay cotización registrada para realizar la conversión."}), 400

            # Conversión simple (Ejemplo: Compra si recibimos USD, Venta si entregamos USD, o según política)
            rate = float(cotizacion.compra if moneda_origen == 'USD' else cotizacion.venta)
            
            if moneda_origen == 'USD' and moneda_destino == 'PYG':
                monto_credito = monto * rate
            elif moneda_origen == 'PYG' and moneda_destino == 'USD':
                monto_credito = monto / rate
        
        cuenta_origen.saldo = (cuenta_origen.saldo or 0) - monto_debito
        cuenta_destino.saldo = (cuenta_destino.saldo or 0) + monto_credito
        
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
        
        return jsonify({"message": "Transferencia realizada con éxito"}), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": "Error interno del servidor", "details": str(e)}), 500

# --- APIs REPORTES (VENTAS Y COBROS) ---

@app.route("/api/reportes/ventas/resumen", methods=["POST"])
@login_required
def api_reporte_ventas_resumen():
    data = request.json
    tipo = data.get('tipo') # 'vendedor', 'ranking'
    fecha_desde = datetime.strptime(data['fecha_desde'], "%Y-%m-%d").date()
    fecha_hasta = datetime.strptime(data['fecha_hasta'], "%Y-%m-%d").date()

    query = db.session.query(
        Venta.id, Venta.fecha_venta, Venta.total, Venta.numero_factura,
        Cliente.nombre.label('cliente_nombre'), Cliente.apellido.label('cliente_apellido'),
        Funcionario.nombre.label('vendedor_nombre'), Funcionario.apellido.label('vendedor_apellido')
    ).join(Cliente, Venta.cliente_id == Cliente.id)\
     .outerjoin(Funcionario, Venta.vendedor_id == Funcionario.id)\
     .filter(Venta.fecha_venta >= fecha_desde, Venta.fecha_venta <= fecha_hasta, Venta.estado == 'emitida')

    ventas = query.all()
    
    resultados = []
    
    if tipo == 'vendedores':
        agrupado = {}
        for v in ventas:
            vend = f"{v.vendedor_nombre} {v.vendedor_apellido}" if v.vendedor_nombre else "Sin Vendedor"
            if vend not in agrupado: agrupado[vend] = {'cantidad': 0, 'total': 0}
            agrupado[vend]['cantidad'] += 1
            agrupado[vend]['total'] += float(v.total)
        
        resultados = [{"label": k, "cantidad": v['cantidad'], "total": v['total']} for k, v in agrupado.items()]

    elif tipo == 'ranking':
        agrupado = {}
        for v in ventas:
            cli = f"{v.cliente_nombre} {v.cliente_apellido}"
            if cli not in agrupado: agrupado[cli] = {'cantidad': 0, 'total': 0}
            agrupado[cli]['cantidad'] += 1
            agrupado[cli]['total'] += float(v.total)
        
        resultados = [{"label": k, "cantidad": v['cantidad'], "total": v['total']} for k, v in agrupado.items()]
        resultados.sort(key=lambda x: x['total'], reverse=True)

    return jsonify(resultados)

@app.route("/api/reportes/clientes/estado-cuenta", methods=["POST"])
@login_required
def api_reporte_estado_cuenta():
    data = request.json
    cliente_id = data.get('cliente_id')
    
    cliente = Cliente.query.get_or_404(cliente_id)
    
    contratos = Contrato.query.filter_by(cliente_id=cliente.id).all()
    
    resumen = {
        "cliente": f"{cliente.nombre} {cliente.apellido}",
        "documento": cliente.documento,
        "contratos": []
    }
    
    for contrato in contratos:
        cuotas = Cuota.query.filter_by(contrato_id=contrato.id).all()
        total_pagado = sum(c.valor_pagado for c in cuotas)
        total_deuda = sum(c.valor_cuota for c in cuotas if c.estado != 'pagada')
        
        pagos = Pago.query.filter_by(contrato_id=contrato.id).order_by(Pago.fecha_pago.desc()).all()
        
        info_contrato = {
            "numero": contrato.numero_contrato,
            "lote": f"Mza: {contrato.lote.manzana} Lote: {contrato.lote.numero_lote}",
            "total_contrato": float(contrato.valor_total),
            "total_pagado": float(total_pagado),
            "saldo_pendiente": float(total_deuda),
            "cuotas_vencidas": len([c for c in cuotas if c.estado == 'vencida']),
            "historial_pagos": [p.to_dict() for p in pagos]
        }
        resumen["contratos"].append(info_contrato)
        
    return jsonify(resumen)

# --- APIs DEFINICIONES GENÉRICAS Y COMPLETAS ---
def create_api_for_simple_model(model_class, endpoint):
    @app.route(f"/api/admin/{endpoint}", methods=["GET", "POST"], endpoint=f"api_{endpoint}")
    @login_required
    def api_simple_model():
        if request.method == "POST":
            data = request.json
            if not data.get('nombre'): return jsonify({"error": "El nombre es requerido"}), 400
            if hasattr(model_class, 'nombre') and model_class.query.filter_by(nombre=data['nombre']).first(): 
                return jsonify({"error": "Ese nombre ya existe"}), 400
            
            if endpoint == 'barrios':
                new_obj = model_class(nombre=data['nombre'], ciudad_id=data['ciudad_id'])
            else:
                new_obj = model_class(nombre=data['nombre'])
                
            db.session.add(new_obj); db.session.commit()
            return jsonify(new_obj.to_dict()), 201
        
        query = model_class.query
        if endpoint == 'barrios' and request.args.get('ciudad_id'):
            query = query.filter_by(ciudad_id=request.args.get('ciudad_id'))
            
        return jsonify([obj.to_dict() for obj in query.all()])

    @app.route(f"/api/admin/{endpoint}/<int:obj_id>", methods=["PUT", "DELETE"], endpoint=f"api_{endpoint}_detalle")
    @login_required
    def api_simple_model_detalle(obj_id):
        obj = model_class.query.get_or_404(obj_id)
        if request.method == "PUT":
            data = request.json
            if 'nombre' in data: obj.nombre = data.get('nombre', obj.nombre)
            if endpoint == 'barrios' and 'ciudad_id' in data: obj.ciudad_id = data['ciudad_id']
            db.session.commit()
            return jsonify(obj.to_dict())
        if request.method == "DELETE":
            db.session.delete(obj); db.session.commit()
            return jsonify({"message": "Eliminado correctamente"})

create_api_for_simple_model(FormaPago, 'formas-pago')
create_api_for_simple_model(TipoCliente, 'tipos-cliente')
create_api_for_simple_model(TipoComprobante, 'tipos-comprobante')
create_api_for_simple_model(Profesion, 'profesiones')
create_api_for_simple_model(TipoDocumento, 'tipos-documentos')
create_api_for_simple_model(Ciudad, 'ciudades')
create_api_for_simple_model(Barrio, 'barrios')

@app.route("/api/admin/condiciones-pago", methods=["GET", "POST"])
@login_required
@role_required('Admin', 'Cajero')
def api_condiciones_pago():
    if request.method == "POST":
        data = request.json
        new_obj = CondicionPago(nombre=data['nombre'], dias=data.get('dias', 0))
        db.session.add(new_obj); db.session.commit()
        return jsonify(new_obj.to_dict()), 201
    return jsonify([obj.to_dict() for obj in CondicionPago.query.all()])

@app.route("/api/admin/condiciones-pago/<int:obj_id>", methods=["PUT", "DELETE"])
@login_required
@role_required('Admin', 'Cajero')
def api_condicion_pago_detalle(obj_id):
    obj = CondicionPago.query.get_or_404(obj_id)
    if request.method == "PUT":
        data = request.json
        obj.nombre = data.get('nombre', obj.nombre)
        obj.dias = data.get('dias', obj.dias)
        db.session.commit()
        return jsonify(obj.to_dict())
    if request.method == "DELETE":
        db.session.delete(obj); db.session.commit()
        return jsonify({"message": "Eliminado correctamente"})

@app.route("/api/admin/impuestos", methods=["GET", "POST"])
@login_required
@role_required('Admin')
def api_impuestos():
    if request.method == "POST":
        data = request.json
        obj = Impuesto(nombre=data['nombre'], porcentaje=data['porcentaje'])
        db.session.add(obj); db.session.commit()
        return jsonify(obj.to_dict()), 201
    return jsonify([o.to_dict() for o in Impuesto.query.all()])

@app.route("/api/admin/impuestos/<int:obj_id>", methods=["PUT", "DELETE"])
@login_required
@role_required('Admin')
def api_impuesto_detalle(obj_id):
    obj = Impuesto.query.get_or_404(obj_id)
    if request.method == "GET":
        return jsonify(obj.to_dict())
    if request.method == "PUT":
        data = request.json
        obj.nombre = data.get('nombre', obj.nombre)
        obj.porcentaje = data.get('porcentaje', obj.porcentaje)
        db.session.commit()
        return jsonify(obj.to_dict())
    if request.method == "DELETE":
        db.session.delete(obj); db.session.commit()
        return jsonify({"message": "Eliminado correctamente"})

@app.route("/api/admin/talonarios", methods=["GET", "POST"])
@login_required
@role_required('Admin')
def api_talonarios():
    if request.method == "POST":
        data = request.json
        obj = Talonario(
            tipo_comprobante_id=data['tipo_comprobante_id'],
            timbrado=data['timbrado'],
            fecha_inicio_vigencia=datetime.strptime(data['fecha_inicio_vigencia'], "%Y-%m-%d").date(),
            fecha_fin_vigencia=datetime.strptime(data['fecha_fin_vigencia'], "%Y-%m-%d").date(),
            punto_expedicion=data['punto_expedicion'],
            caja=data['caja'],
            numero_actual=data['numero_actual'],
            numero_fin=data['numero_fin'],
            activo=data.get('activo', True)
        )
        db.session.add(obj); db.session.commit()
        return jsonify(obj.to_dict()), 201
    return jsonify([o.to_dict() for o in Talonario.query.order_by(Talonario.activo.desc(), Talonario.fecha_fin_vigencia.desc()).all()])

@app.route("/api/admin/talonarios/<int:obj_id>", methods=["PUT", "DELETE"])
@login_required
@role_required('Admin')
def api_talonario_detalle(obj_id):
    obj = Talonario.query.get_or_404(obj_id)

    if request.method == "GET":
        return jsonify(obj.to_dict())
    if request.method == "PUT":
        data = request.json
        obj.tipo_comprobante_id = data.get('tipo_comprobante_id', obj.tipo_comprobante_id)
        obj.timbrado = data.get('timbrado', obj.timbrado)
        obj.fecha_inicio_vigencia = datetime.strptime(data['fecha_inicio_vigencia'], "%Y-%m-%d").date() if data.get('fecha_inicio_vigencia') else obj.fecha_inicio_vigencia
        obj.fecha_fin_vigencia = datetime.strptime(data['fecha_fin_vigencia'], "%Y-%m-%d").date() if data.get('fecha_fin_vigencia') else obj.fecha_fin_vigencia
        obj.punto_expedicion = data.get('punto_expedicion', obj.punto_expedicion)
        obj.caja = data.get('caja', obj.caja)
        obj.numero_actual = data.get('numero_actual', obj.numero_actual)
        obj.numero_fin = data.get('numero_fin', obj.numero_fin)
        obj.activo = data.get('activo', obj.activo)
        db.session.commit()
        return jsonify(obj.to_dict())
    if request.method == "DELETE":
        db.session.delete(obj); db.session.commit()
        return jsonify({"message": "Eliminado correctamente"})

@app.route("/api/admin/parametros", methods=["GET", "POST"])
@login_required
def api_parametros_sistema():
    if request.method == "POST":
        data = request.json
        if ParametroSistema.query.filter_by(clave=data['clave']).first():
            return jsonify({"error": "Esa clave ya existe"}), 400
        param = ParametroSistema(clave=data['clave'], valor=data['valor'], descripcion=data.get('descripcion'))
        db.session.add(param); db.session.commit()
        return jsonify(param.to_dict()), 201
    return jsonify([p.to_dict() for p in ParametroSistema.query.all()])

@app.route("/api/admin/parametros/<int:pid>", methods=["PUT", "DELETE"])
@login_required
def api_parametro_sistema_detalle(pid):
    param = ParametroSistema.query.get_or_404(pid)
    if request.method == "PUT":
        data = request.json
        param.valor = data.get('valor', param.valor)
        param.descripcion = data.get('descripcion', param.descripcion)
        db.session.commit()
        return jsonify(param.to_dict())
    if request.method == "DELETE":
        db.session.delete(param); db.session.commit()
        return jsonify({"message": "Eliminado"})

@app.route("/api/admin/cotizaciones", methods=["GET", "POST"])
@login_required
def api_cotizaciones_sistema():
    if request.method == "POST":
        data = request.json
        cot = Cotizacion(
            fecha=datetime.strptime(data['fecha'], "%Y-%m-%d").date(),
            moneda_origen=data['moneda_origen'],
            moneda_destino=data['moneda_destino'],
            compra=data['compra'],
            venta=data['venta']
        )
        db.session.add(cot); db.session.commit()
        return jsonify(cot.to_dict()), 201
    return jsonify([c.to_dict() for c in Cotizacion.query.order_by(Cotizacion.fecha.desc()).limit(50).all()])

@app.route("/api/admin/cotizaciones/<int:cid>", methods=["PUT", "DELETE"])
@login_required
def api_cotizacion_sistema_detalle(cid):
    cot = Cotizacion.query.get_or_404(cid)
    if request.method == "PUT":
        data = request.json
        cot.compra = data['compra']
        cot.venta = data['venta']
        db.session.commit()
        return jsonify(cot.to_dict())
    if request.method == "DELETE":
        db.session.delete(cot); db.session.commit()
        return jsonify({"message": "Eliminado"})

# ============================
# MANEJO DE ERRORES Y COMANDOS CLI
# ============================

@app.errorhandler(404)
def not_found(error):
    return render_template('errors/404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return render_template('errors/500.html'), 500

@app.cli.command("create-admin")
@click.argument("nombre")
@click.argument("apellido")
@click.argument("documento")
@click.argument("usuario")
@click.argument("password")
def create_admin(nombre, apellido, documento, usuario, password):
    """Crea el usuario administrador inicial."""
    with app.app_context():
        admin_role = Role.query.filter_by(name='Admin').first()
        admin_cargo = Cargo.query.filter_by(nombre='Administrador').first()
        if not admin_role: 
            admin_role = Role(name='Admin', description="Acceso total al sistema")
            db.session.add(admin_role)
        if not admin_cargo: 
            admin_cargo = Cargo(nombre='Administrador')
            db.session.add(admin_cargo)
        db.session.commit()
        
        if Funcionario.query.filter_by(usuario=usuario).first(): 
            print(f"El usuario '{usuario}' ya existe.")
            return

        admin_user = Funcionario(nombre=nombre, apellido=apellido, documento=documento, usuario=usuario, cargo_id=admin_cargo.id, fecha_ingreso=date.today(), estado='activo', es_vendedor=True)
        admin_user.set_password(password)
        admin_user.roles.append(admin_role)
        db.session.add(admin_user)
        db.session.commit()
        print(f"Usuario administrador '{usuario}' creado exitosamente.")

@app.cli.command("init-db")
def init_db_command():
    """Crea/actualiza las tablas de la DB y carga datos maestros."""
    db.create_all()
    roles_cargos = {'Admin': 'Administrador', 'Vendedor': 'Vendedor', 'Cajero': 'Cajero', 'Empleado': 'Empleado'}
    for role_name, cargo_name in roles_cargos.items():
        if not Role.query.filter_by(name=role_name).first(): db.session.add(Role(name=role_name))
        if not Cargo.query.filter_by(nombre=cargo_name).first(): db.session.add(Cargo(nombre=cargo_name))
    
    aplicaciones_a_crear = [
        {'modulo': 'Módulo Base', 'nombre': 'Definiciones de Seguridad', 'clave': 'base_definiciones'},
        {'modulo': 'Cobros', 'nombre': 'Movimientos de Cobros', 'clave': 'cobros_movimientos'},
        {'modulo': 'Inventario', 'nombre': 'Movimientos de Inventario', 'clave': 'inventario_movimientos'},
        {'modulo': 'RRHH', 'nombre': 'Definiciones de RRHH', 'clave': 'rrhh_definiciones'},
        {'modulo': 'Tesorería', 'nombre': 'Movimientos de Tesorería', 'clave': 'tesoreria_movimientos'},
        {'modulo': 'Gastos', 'nombre': 'Movimientos de Gastos', 'clave': 'gastos_movimientos'},
        {'modulo': 'Ventas', 'nombre': 'Movimientos de Ventas', 'clave': 'ventas_movimientos'},
        {'modulo': 'Mapa', 'nombre': 'Mapa Interactivo', 'clave': 'mapa_interactivo'},
    ]
    for app_data in aplicaciones_a_crear:
        if not Aplicacion.query.filter_by(clave=app_data['clave']).first():
            db.session.add(Aplicacion(**app_data))

    db.session.commit()
    print('Base de datos inicializada y datos maestros cargados.')

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True, host='0.0.0.0', port=5000)