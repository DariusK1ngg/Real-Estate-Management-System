-- ============================================================
-- ARCHIVO DE CARGA DE DATOS INICIALES - SISTEMA INMOBILIARIO
-- ============================================================
-- Ejecutar este script después de 'flask db upgrade'
-- ============================================================

-- 1. TIPOS DE DOCUMENTO
INSERT INTO tipos_documentos (id, nombre) VALUES 
(1, 'Cédula de Identidad (CI)'),
(2, 'RUC'),
(3, 'Pasaporte'),
(4, 'Carnet de Extranjería');

-- 2. TIPOS DE CLIENTE
INSERT INTO tipos_cliente (id, nombre) VALUES 
(1, 'Persona Física'),
(2, 'Persona Jurídica'),
(3, 'Inversionista');

-- 3. PROFESIONES
INSERT INTO profesiones (id, nombre) VALUES 
(1, 'Comerciante'),
(2, 'Empleado Privado'),
(3, 'Funcionario Público'),
(4, 'Abogado/a'),
(5, 'Médico/a'),
(6, 'Ingeniero/a'),
(7, 'Docente'),
(8, 'Arquitecto/a'),
(9, 'Contador/a'),
(10, 'Jubilado/a'),
(11, 'Estudiante'),
(12, 'Empresario/a');

-- 4. FORMAS DE PAGO
INSERT INTO formas_pago (id, nombre) VALUES 
(1, 'Efectivo'),
(2, 'Transferencia Bancaria'),
(3, 'Cheque'),
(4, 'Tarjeta de Débito'),
(5, 'Tarjeta de Crédito');

-- 5. IMPUESTOS (Paraguay)
INSERT INTO impuestos (id, nombre, porcentaje) VALUES 
(1, 'IVA 10%', 10.00),
(2, 'IVA 5%', 5.00),
(3, 'Exenta', 0.00);

-- 6. CONDICIONES DE PAGO
INSERT INTO condiciones_pago (id, nombre, dias) VALUES 
(1, 'Contado', 0),
(2, 'Crédito 30 días', 30),
(3, 'Crédito 60 días', 60),
(4, 'Financiación Propia (Cuotas)', 0);

-- 7. TIPOS DE COMPROBANTE
INSERT INTO tipos_comprobantes (id, nombre) VALUES 
(1, 'Factura'),
(2, 'Recibo de Dinero'),
(3, 'Nota de Crédito'),
(4, 'Nota de Presupuesto');

-- 8. CIUDADES (Principales de Paraguay)
INSERT INTO ciudades (id, nombre) VALUES 
(1, 'Encarnación'),
(2, 'Asunción'),
(3, 'Ciudad del Este'),
(4, 'Cambyretá'),
(5, 'Hohenau'),
(6, 'Bella Vista'),
(7, 'San Lorenzo'),
(8, 'Luque'),
(9, 'Villarrica'),
(10, 'Coronel Bogado');

-- 9. BARRIOS (Ejemplos para Encarnación/Asunción)
INSERT INTO barrios (id, nombre, ciudad_id) VALUES 
(1, 'Centro', 1),
(2, 'Barrio San Pedro', 1),
(3, 'Barrio San Isidro', 1),
(4, 'Barrio Pacú Cua', 1),
(5, 'Villa Morra', 2),
(6, 'Recoleta', 2),
(7, 'Centro', 4), -- Cambyretá
(8, 'Centro', 5); -- Hohenau

-- 10. CARGOS (RRHH)
INSERT INTO cargos (id, nombre) VALUES 
(1, 'Administrador General'),
(2, 'Gerente de Ventas'),
(3, 'Vendedor'),
(4, 'Cajero'),
(5, 'Secretario/a'),
(6, 'Cobrador');

-- 11. ROLES DEL SISTEMA (Seguridad)
-- Estos deben coincidir con los que usas en los decoradores @role_required
INSERT INTO roles (id, name, description) VALUES 
(1, 'Admin', 'Acceso total al sistema'),
(2, 'Vendedor', 'Acceso a módulo de ventas, inventario y clientes'),
(3, 'Cajero', 'Acceso a módulo de cobros, tesorería y arqueos'),
(4, 'Empleado', 'Acceso de consulta y tareas administrativas básicas');

-- 12. APLICACIONES (Módulos para permisos granulares)
INSERT INTO aplicaciones (id, nombre, clave, modulo) VALUES 
(1, 'Gestión de Usuarios', 'user_manage', 'Seguridad'),
(2, 'Gestión de Roles', 'role_manage', 'Seguridad'),
(3, 'Mapa Interactivo', 'map_view', 'Inventario'),
(4, 'ABM Lotes', 'lote_manage', 'Inventario'),
(5, 'Cargar Venta', 'sale_create', 'Ventas'),
(6, 'Registrar Cobro', 'payment_create', 'Cobros'),
(7, 'Arqueo de Caja', 'cash_audit', 'Tesoreria'),
(8, 'Reportes Financieros', 'fin_reports', 'Reportes');

-- 13. PARAMETROS DEL SISTEMA
INSERT INTO parametros_sistema (id, clave, valor, descripcion) VALUES 
(1, 'EMPRESA_NOMBRE', 'Inmobiliaria Von Knobloch', 'Nombre comercial de la empresa'),
(2, 'EMPRESA_RUC', '80012345-6', 'RUC de la empresa'),
(3, 'EMPRESA_DIRECCION', 'Calle Mcal. Estigarribia c/ Tomás R. Pereira', 'Dirección fiscal'),
(4, 'MONEDA_DEFECTO', 'PYG', 'Moneda predeterminada'),
(5, 'IVA_DEFECTO', '10', 'Porcentaje de IVA por defecto'),
(6, 'INTERES_MORA_DIARIO', '0.5', 'Porcentaje de interés por día de atraso');

-- 14. ENTIDADES FINANCIERAS
INSERT INTO entidades_financieras (id, nombre) VALUES 
(1, 'Banco Itaú Paraguay'),
(2, 'Banco Atlas'),
(3, 'Banco Nacional de Fomento (BNF)'),
(4, 'Banco Continental'),
(5, 'Visión Banco'),
(6, 'Cooperativa Universitaria');

-- 15. CATEGORÍAS DE GASTO
INSERT INTO categorias_gasto (id, nombre, descripcion) VALUES 
(1, 'Servicios Básicos', 'ANDE, ESSAP, Internet'),
(2, 'Sueldos y Jornales', 'Pago de nómina'),
(3, 'Mantenimiento', 'Reparaciones de oficina o lotes'),
(4, 'Publicidad', 'Redes sociales, radio, tv'),
(5, 'Insumos de Oficina', 'Papelería, tinta, etc.');

-- 16. PROVEEDORES (Ejemplos)
INSERT INTO proveedores (id, razon_social, ruc, telefono, direccion) VALUES 
(1, 'Administración Nacional de Electricidad (ANDE)', '80000000-1', '160', 'Avda. España'),
(2, 'Librería Central', '5556667-8', '0981-111222', 'Centro'),
(3, 'Facebook Ads', 'Extranjero', '-', 'Online');