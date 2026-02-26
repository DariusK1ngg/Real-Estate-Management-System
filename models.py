from extensions import db, bcrypt
from flask_login import UserMixin
from sqlalchemy import Enum
from datetime import datetime, date

# --- DEFINICIONES BASE ---
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

class Servicio(db.Model):
    __tablename__ = 'servicios'
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(150), nullable=False)
    precio_defecto = db.Column(db.Numeric(12, 2), default=0)
    activo = db.Column(db.Boolean, default=True)
    def to_dict(self): return {"id": self.id, "nombre": self.nombre, "precio_defecto": float(self.precio_defecto), "activo": self.activo}

# --- SEGURIDAD ---
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

# --- INMOBILIARIA ---
class Fraccionamiento(db.Model):
    __tablename__ = "fraccionamientos"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    ciudad_id = db.Column(db.Integer, db.ForeignKey('ciudades.id'), nullable=True)
    ciudad = db.relationship('Ciudad')
    nombre = db.Column(db.String(120), nullable=False, unique=True)
    descripcion = db.Column(db.Text, nullable=True)
    comision_inmobiliaria = db.Column(db.Numeric(5, 2), default=0.00)
    comision_propietario = db.Column(db.Numeric(5, 2), default=0.00)
    geojson = db.Column(db.JSON, nullable=False)
    def to_feature(self): 
        return {"type": "Feature", "geometry": self.geojson, "properties": {"id": self.id, "nombre": self.nombre, "descripcion": self.descripcion or "", "ciudad_id": self.ciudad_id, "ciudad_nombre": self.ciudad.nombre if self.ciudad else ""}}
    def to_dict(self):
        return {"id": self.id, "nombre": self.nombre, "descripcion": self.descripcion or "", "ciudad_id": self.ciudad_id, "ciudad_nombre": self.ciudad.nombre if self.ciudad else "", "comision_inmobiliaria": float(self.comision_inmobiliaria or 0.0), "comision_propietario": float(self.comision_propietario or 0.0)}

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
    activo = db.Column(db.Boolean, default=True, nullable=False)
    fraccionamiento = db.relationship("Fraccionamiento", backref=db.backref("lotes", lazy=True, cascade="all, delete-orphan"))
    contratos = db.relationship("Contrato", backref="lote", lazy=True)
    lista_precios = db.relationship("ListaPrecioLote", backref="lote", lazy=True, cascade="all, delete-orphan")
    def to_feature(self): return {"type": "Feature", "geometry": self.geojson, "properties": {"id": self.id, "numero_lote": self.numero_lote, "manzana": self.manzana, "precio": float(self.precio), "precio_financiado_130": float(self.precio_financiado_130) if self.precio_financiado_130 else None, "precio_cuota_130": float(self.precio_cuota_130) if self.precio_cuota_130 else None, "metros_cuadrados": self.metros_cuadrados, "estado": self.estado, "fraccionamiento_id": self.fraccionamiento_id}}
    __table_args__ = (
        db.UniqueConstraint('fraccionamiento_id', 'manzana', 'numero_lote', name='uq_lote_manzana_fracc'),
    )
    def to_dict(self):
        return {
            'id': self.id,
            'numero_lote': self.numero_lote,
            'manzana': self.manzana,
            'precio_contado': float(self.precio) if self.precio else 0, # Ojo: en tu modelo se llama 'precio', no 'precio_contado'
            'metros_cuadrados': self.metros_cuadrados,
            'estado': self.estado
        }

class ListaPrecioLote(db.Model):
    __tablename__ = 'lista_precio_lote'
    id = db.Column(db.Integer, primary_key=True)
    lote_id = db.Column(db.Integer, db.ForeignKey('lotes.id'), nullable=False)
    condicion_pago_id = db.Column(db.Integer, db.ForeignKey('condiciones_pago.id'), nullable=False)
    cantidad_cuotas = db.Column(db.Integer, nullable=False)
    precio_cuota = db.Column(db.Numeric(12, 2), nullable=False)
    precio_total = db.Column(db.Numeric(12, 2), nullable=False)
    condicion_pago = db.relationship("CondicionPago")
    def to_dict(self): return {"id": self.id, "lote_id": self.lote_id, "condicion_pago_id": self.condicion_pago_id, "condicion_pago_nombre": self.condicion_pago.nombre, "cantidad_cuotas": self.cantidad_cuotas, "precio_cuota": float(self.precio_cuota), "precio_total": float(self.precio_total)}

class Cliente(db.Model):
    __tablename__ = "clientes"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    tipo_documento_id = db.Column(db.Integer, db.ForeignKey('tipos_documentos.id'), nullable=True)
    tipo_documento = db.relationship('TipoDocumento')
    profesion_id = db.Column(db.Integer, db.ForeignKey('profesiones.id'), nullable=True)
    profesion = db.relationship('Profesion')
    tipo_cliente_id = db.Column(db.Integer, db.ForeignKey('tipos_cliente.id'), nullable=True)
    tipo_cliente = db.relationship('TipoCliente')
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
    activo = db.Column(db.Boolean, default=True, nullable=False)
    contratos = db.relationship("Contrato", backref="cliente", lazy=True)
    def to_dict(self): 
        return {"id": self.id, "tipo_documento_id": self.tipo_documento_id, "tipo_documento": self.tipo_documento.nombre if self.tipo_documento else "CI", "documento": self.documento, "nombre": self.nombre, "apellido": self.apellido, "nombre_completo": f"{self.nombre} {self.apellido}", "telefono": self.telefono or "", "email": self.email or "", "direccion": self.direccion or "", "ciudad_id": self.ciudad_id, "ciudad_nombre": self.ciudad.nombre if self.ciudad else "", "barrio_id": self.barrio_id, "barrio_nombre": self.barrio.nombre if self.barrio else "", "profesion_id": self.profesion_id, "tipo_cliente_id": self.tipo_cliente_id, "fecha_registro": self.fecha_registro.isoformat() if self.fecha_registro else None, "estado": self.estado}

class Contrato(db.Model):
    __tablename__ = "contratos"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    numero_contrato = db.Column(db.String(50), nullable=False, unique=True)
    cliente_id = db.Column(db.Integer, db.ForeignKey("clientes.id"), nullable=False)
    lote_id = db.Column(db.Integer, db.ForeignKey("lotes.id"), nullable=False)
    vendedor_id = db.Column(db.Integer, db.ForeignKey("funcionarios.id"), nullable=True)
    fecha_contrato = db.Column(db.Date, nullable=False)
    uso = db.Column(db.String(50), nullable=True)
    moneda = db.Column(db.String(10), default='GS')
    medida_tiempo = db.Column(db.String(20), default='Mensual')
    valor_total = db.Column(db.Numeric(12, 2), nullable=False)
    cuota_inicial = db.Column(db.Numeric(12, 2), nullable=False)
    fecha_vencimiento_entrega = db.Column(db.Date, nullable=True)
    cantidad_cuotas = db.Column(db.Integer, nullable=False)
    valor_cuota = db.Column(db.Numeric(12, 2), nullable=False)
    doc_modelo_contrato = db.Column(db.String(20), default='No entregado')
    doc_comp_interno = db.Column(db.String(20), default='No entregado')
    doc_identidad = db.Column(db.String(20), default='No entregado')
    doc_factura_servicios = db.Column(db.String(20), default='No entregado')
    doc_ingresos = db.Column(db.String(20), default='No entregado')
    # Eliminadas las comisiones aquí
    tipo_contrato = db.Column(Enum("venta", "reserva", "alquiler", name="tipo_contrato_enum"), nullable=False, default="venta")
    estado = db.Column(Enum("activo", "cancelado", "finalizado", "rescindido", "inactivo", name="estado_contrato_enum"), nullable=False, default="activo")
    observaciones = db.Column(db.Text, nullable=True)
    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow)
    cuotas = db.relationship("Cuota", backref="contrato", lazy=True, cascade="all, delete-orphan")
    pagos = db.relationship("Pago", backref="contrato", lazy=True, cascade="all, delete-orphan")
    vendedor = db.relationship("Funcionario")

    def to_dict(self): 
        return {
            "id": self.id, 
            "numero_contrato": self.numero_contrato, 
            "cliente_id": self.cliente_id, 
            "lote_id": self.lote_id, 
            "fecha_contrato": self.fecha_contrato.isoformat() if self.fecha_contrato else None, 
            "valor_total": float(self.valor_total), 
            "cuota_inicial": float(self.cuota_inicial), 
            "cantidad_cuotas": self.cantidad_cuotas, 
            "valor_cuota": float(self.valor_cuota), 
            "tipo_contrato": self.tipo_contrato, 
            "estado": self.estado, 
            "observaciones": self.observaciones,
            "uso": self.uso,
            "moneda": self.moneda,
            "doc_identidad": self.doc_identidad,
            "cliente_nombre": f"{self.cliente.nombre} {self.cliente.apellido}", 
            "lote_info": f"{self.lote.manzana} - {self.lote.numero_lote}", 
            "fraccionamiento": self.lote.fraccionamiento.nombre
        }

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
    tipo = db.Column(db.String(20), default='cuota')
    observaciones = db.Column(db.Text, nullable=True)
    pagos = db.relationship("Pago", backref="cuota", lazy=True, cascade="all, delete-orphan")
    def to_dict(self): 
        return {
            "id": self.id, 
            "contrato_id": self.contrato_id, 
            "numero_contrato": self.contrato.numero_contrato if self.contrato else "N/A",
            "numero_cuota": self.numero_cuota, 
            "fecha_vencimiento": self.fecha_vencimiento.isoformat() if self.fecha_vencimiento else None, 
            "valor_cuota": float(self.valor_cuota), 
            "fecha_pago": self.fecha_pago.isoformat() if self.fecha_pago else None, 
            "valor_pagado": float(self.valor_pagado), 
            "estado": self.estado, 
            "tipo": self.tipo,
            "observaciones": self.observaciones, 
            "dias_vencimiento": (self.fecha_vencimiento - date.today()).days if self.fecha_vencimiento else None
        }

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
    def to_dict(self): return {"id": self.id, "contrato_id": self.contrato_id, "cuota_id": self.cuota_id, "fecha_pago": self.fecha_pago.isoformat() if self.fecha_pago else None, "monto": float(self.monto), "forma_pago_id": self.forma_pago_id, "forma_pago": self.forma_pago_rel.nombre if self.forma_pago_rel else "N/A", "referencia": self.referencia, "observaciones": self.observaciones, "cuenta_bancaria_id": self.cuenta_bancaria_id, "usuario_id": self.usuario_id}

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
    def to_dict(self): return { "id": self.id, "nombre": self.nombre, "descripcion": self.descripcion or "" }

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
    talonario_id = db.Column(db.Integer, db.ForeignKey("talonarios.id"), nullable=True)
    talonario = db.relationship("Talonario")
    fecha_venta = db.Column(db.Date, nullable=False, default=date.today)
    numero_factura = db.Column(db.String(50), nullable=False, unique=True)
    total = db.Column(db.Numeric(12, 2), nullable=False)
    estado = db.Column(Enum("emitida", "anulada", name="estado_venta_enum"), nullable=False, default="emitida")
    cliente = db.relationship("Cliente", backref=db.backref("ventas", lazy=True))
    vendedor = db.relationship("Funcionario", backref=db.backref("ventas", lazy=True))
    detalles = db.relationship("VentaDetalle", backref="venta", lazy=True, cascade="all, delete-orphan")
    def to_dict(self): return { "id": self.id, "cliente_id": self.cliente_id, "cliente_nombre": f"{self.cliente.nombre} {self.cliente.apellido}", "vendedor_id": self.vendedor_id, "vendedor_nombre": f"{self.vendedor.nombre} {self.vendedor.apellido}" if self.vendedor else "N/A", "numero_factura": self.numero_factura, "talonario_id": self.talonario_id, "total": float(self.total), "estado": self.estado, "detalles": [d.to_dict() for d in self.detalles] }

class VentaDetalle(db.Model):
    __tablename__ = "ventas_detalle"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    venta_id = db.Column(db.Integer, db.ForeignKey("ventas.id"), nullable=False)
    lote_id = db.Column(db.Integer, db.ForeignKey("lotes.id"), nullable=True)
    impuesto_id = db.Column(db.Integer, db.ForeignKey("impuestos.id"), nullable=True)
    impuesto = db.relationship("Impuesto")
    descripcion = db.Column(db.String(255), nullable=False)
    cantidad = db.Column(db.Integer, nullable=False, default=1)
    precio_unitario = db.Column(db.Numeric(12, 2), nullable=False)
    subtotal = db.Column(db.Numeric(12, 2), nullable=False)
    lote = db.relationship("Lote")
    def to_dict(self): return { "id": self.id, "venta_id": self.venta_id, "lote_id": self.lote_id, "impuesto_id": self.impuesto_id, "impuesto_nombre": self.impuesto.nombre if self.impuesto else "", "descripcion": self.descripcion, "cantidad": self.cantidad, "precio_unitario": float(self.precio_unitario), "subtotal": float(self.subtotal) }

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
    def to_dict(self): return {"id": self.id, "entidad_id": self.entidad_id, "entidad_nombre": self.entidad.nombre, "numero_cuenta": self.numero_cuenta, "titular": self.titular, "tipo_cuenta": self.tipo_cuenta, "moneda": self.moneda, "saldo": float(self.saldo), "tiene_movimientos": bool(self.depositos)}

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
    def to_dict(self): return {"id": self.id, "nombre": self.nombre}

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
    def to_dict(self): return {"id": self.id, "tipo_comprobante_id": self.tipo_comprobante_id, "tipo_comprobante_nombre": self.tipo_comprobante.nombre if self.tipo_comprobante else "N/A", "timbrado": self.timbrado, "fecha_inicio_vigencia": self.fecha_inicio_vigencia.isoformat(), "fecha_fin_vigencia": self.fecha_fin_vigencia.isoformat(), "punto_expedicion": self.punto_expedicion, "caja": self.caja, "numero_actual": self.numero_actual, "numero_fin": self.numero_fin, "activo": self.activo}

class ParametroSistema(db.Model):
    __tablename__ = 'parametros_sistema'
    id = db.Column(db.Integer, primary_key=True)
    clave = db.Column(db.String(50), unique=True, nullable=False)
    valor = db.Column(db.String(255), nullable=False)
    descripcion = db.Column(db.Text, nullable=True)
    def to_dict(self): return {"id": self.id, "clave": self.clave, "valor": self.valor, "descripcion": self.descripcion}

class Cotizacion(db.Model):
    __tablename__ = 'cotizaciones'
    id = db.Column(db.Integer, primary_key=True)
    fecha = db.Column(db.Date, nullable=False, default=date.today)
    moneda_origen = db.Column(Enum("USD", "PYG", name="moneda_cot_orig_enum"), nullable=False)
    moneda_destino = db.Column(Enum("USD", "PYG", name="moneda_cot_dest_enum"), nullable=False)
    compra = db.Column(db.Numeric(10, 2), nullable=False)
    venta = db.Column(db.Numeric(10, 2), nullable=False)
    def to_dict(self): return {"id": self.id, "fecha": self.fecha.isoformat(), "moneda_origen": self.moneda_origen, "moneda_destino": self.moneda_destino, "compra": float(self.compra), "venta": float(self.venta)}

class AuditLog(db.Model):
    __tablename__ = 'audit_logs'
    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('funcionarios.id'), nullable=True)
    usuario = db.relationship("Funcionario")
    accion = db.Column(db.String(50), nullable=False) 
    tabla = db.Column(db.String(50), nullable=False) 
    detalle = db.Column(db.Text, nullable=True)
    fecha = db.Column(db.DateTime, default=datetime.utcnow)
    ip_address = db.Column(db.String(50), nullable=True)

    def to_dict(self):
        return {
            "id": self.id,
            "fecha": self.fecha.strftime("%d/%m/%Y %H:%M:%S"),
            "usuario": self.usuario.usuario if self.usuario else "Sistema",
            "accion": self.accion,
            "tabla": self.tabla,
            "detalle": self.detalle,
            "ip_address": self.ip_address
        }