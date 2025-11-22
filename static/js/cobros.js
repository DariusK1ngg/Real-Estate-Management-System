// static/js/cobros.js

let clienteSeleccionadoId = null;
let modalPago = null;
let modalAbrirCaja = null;

document.addEventListener('DOMContentLoaded', function() {
    // --- Modales ---
    modalPago = new bootstrap.Modal(document.getElementById('modalPago'));
    modalAbrirCaja = new bootstrap.Modal(document.getElementById('modalAbrirCaja'));

    // --- Estado de Caja ---
    checkCajaEstado();
    document.getElementById('btn-cerrar-caja').addEventListener('click', cerrarCaja);
    
    const formAbrirCaja = document.getElementById('formAbrirCaja');
    formAbrirCaja.addEventListener('submit', (e) => {
        e.preventDefault();
        abrirCaja();
    });

    // --- Búsqueda de Cliente ---
    let timeout = null;
    document.getElementById('buscador-cliente').addEventListener('keyup', function(e) {
        clearTimeout(timeout);
        timeout = setTimeout(() => buscarClientes(e.target.value), 500);
    });
    
    // --- Formulario de Pago ---
    const formPago = document.getElementById('formPago');
    formPago.addEventListener('submit', (e) => {
        e.preventDefault();
        registrarPago();
    });

    // --- CARGAR FORMAS DE PAGO ---
    cargarFormasPago();
    cargarCuentasDestino();
});

async function cargarCuentasDestino() {
    const select = document.getElementById('selectCuentaDestino');
    try {
        const res = await fetch('/api/admin/cuentas-bancarias');
        const data = await res.json();
        select.innerHTML = '<option value="">-- Seleccione Cuenta --</option>';
        data.forEach(c => {
            select.innerHTML += `<option value="${c.id}">${c.entidad_nombre} - ${c.numero_cuenta} (${c.moneda})</option>`;
        });
    } catch(e) { console.error(e); }
}

async function cargarFormasPago() {
    const select = document.getElementById('selectFormaPago');
    if(!select) return;

    try {
        const res = await fetch('/api/admin/formas-pago');
        const formas = await res.json();
        select.innerHTML = '';
        formas.forEach(fp => {
            select.innerHTML += `<option value="${fp.id}">${fp.nombre}</option>`;
        });
    } catch (e) {
        console.error("Error cargando formas pago", e);
        select.innerHTML = '<option value="">Error</option>';
    }
}

document.getElementById('selectFormaPago').addEventListener('change', function(e) {
    const text = e.target.options[e.target.selectedIndex].text.toLowerCase();
    const divCuenta = document.getElementById('div-cuenta-destino');
    const selectCuenta = document.getElementById('selectCuentaDestino');
    
    // Lógica simple: Si NO dice "efectivo", pedimos banco
    if (text.includes('efectivo') || e.target.value === "") {
        divCuenta.style.display = 'none';
        selectCuenta.required = false;
        selectCuenta.value = "";
    } else {
        divCuenta.style.display = 'block';
        selectCuenta.required = true; // Obligatorio seleccionar cuenta
    }
});

// --- MANEJO DE CAJA ---
async function checkCajaEstado() {
    const estadoCajaSpan = document.getElementById('estado-caja');
    const btnAbrirCaja = document.getElementById('btn-abrir-caja');
    const btnCerrarCaja = document.getElementById('btn-cerrar-caja');

    if (!estadoCajaSpan || !btnAbrirCaja || !btnCerrarCaja) return;

    try {
        const response = await fetch('/api/admin/caja/estado');
        const data = await response.json();
        
        if (data.caja_abierta) {
            const saldoFormateado = (data.saldo_actual || 0).toLocaleString('es-PY');
            estadoCajaSpan.innerHTML = `ABIERTA: ${data.caja_descripcion} (Saldo: Gs. ${saldoFormateado})`;
            estadoCajaSpan.className = 'badge abierta';
            btnAbrirCaja.style.display = 'none';
            btnCerrarCaja.style.display = 'inline-block';
        } else {
            estadoCajaSpan.innerHTML = 'CERRADA';
            estadoCajaSpan.className = 'badge cerrada';
            btnAbrirCaja.style.display = 'inline-block';
            btnCerrarCaja.style.display = 'none';
        }
    } catch (error) {
        console.error('Error al chequear estado de caja:', error);
        estadoCajaSpan.innerHTML = 'Error de conexión';
        estadoCajaSpan.className = 'badge error';
    }
}

async function abrirCaja() {
    const caja_id = document.getElementById('selectCaja').value;
    const monto_apertura = parseFloat(document.getElementById('montoApertura').value);

    try {
        const response = await fetch('/api/admin/caja/abrir', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                caja_id: parseInt(caja_id),
                monto_apertura: monto_apertura
            })
        });
        const data = await response.json();
        
        if (!response.ok) throw new Error(data.error || 'Error al abrir la caja');
        
        alert(data.message);
        modalAbrirCaja.hide();
        checkCajaEstado();
    } catch (error) {
        alert(error.message);
    }
}

async function cerrarCaja() {
    if (confirm('¿Estás seguro de que quieres cerrar la caja? Se calculará el saldo final.')) {
        try {
            const response = await fetch('/api/admin/caja/cerrar', { method: 'POST' });
            const data = await response.json();
            if (!response.ok) throw new Error(data.error || 'Error al cerrar caja');
            
            alert(data.message);
            checkCajaEstado();
        } catch (error) {
            alert(error.message);
        }
    }
}

// --- BÚSQUEDA Y SELECCIÓN DE CLIENTE ---
async function buscarClientes(query) {
    const resultadosDiv = document.getElementById('resultados-busqueda');
    if (query.length < 2) {
        resultadosDiv.innerHTML = '';
        return;
    }
    const response = await fetch(`/api/admin/clientes/buscar?q=${query}`);
    const clientes = await response.json();
    resultadosDiv.innerHTML = '';
    if (clientes.length === 0) {
        resultadosDiv.innerHTML = '<div class="list-group-item">No se encontraron clientes.</div>';
    } else {
        clientes.forEach(cliente => {
            const item = document.createElement('a');
            item.href = "#";
            item.className = 'list-group-item list-group-item-action';
            item.textContent = `${cliente.nombre_completo} - ${cliente.documento}`;
            item.onclick = (e) => {
                e.preventDefault();
                seleccionarCliente(cliente);
            };
            resultadosDiv.appendChild(item);
        });
    }
}

function seleccionarCliente(cliente) {
    clienteSeleccionadoId = cliente.id;
    document.getElementById('nombre-cliente-seleccionado').textContent = cliente.nombre_completo;
    document.getElementById('buscador-cliente').value = cliente.nombre_completo;
    document.getElementById('resultados-busqueda').innerHTML = '';
    cargarCuotasCliente(cliente.id);
}

async function cargarCuotasCliente(clienteId) {
    const tbody = document.getElementById('tbodyCuotas');
    tbody.innerHTML = '<tr><td colspan="6" class="text-center">Cargando cuotas...</td></tr>';
    try {
        const response = await fetch(`/api/admin/clientes/${clienteId}/cuotas`);
        const cuotas = await response.json();
        if (cuotas.length === 0) {
            tbody.innerHTML = '<tr><td colspan="6" class="text-center text-muted">Este cliente no tiene cuotas pendientes.</td></tr>';
            return;
        }
        tbody.innerHTML = '';
        cuotas.forEach(cuota => {
            const tr = document.createElement('tr');
            const fechaVenc = new Date(cuota.fecha_vencimiento + 'T00:00:00-00:00');
            const fechaFormateada = fechaVenc.toLocaleDateString('es-ES', { timeZone: 'UTC' });
            const montoFormateado = cuota.valor_cuota.toLocaleString('es-PY');
            
            tr.innerHTML = `
                <td>${cuota.numero_contrato}</td>
                <td>${cuota.numero_cuota}</td>
                <td>${fechaFormateada}</td>
                <td><strong>Gs. ${montoFormateado}</strong></td>
                <td><span class="badge ${cuota.estado === 'pendiente' ? 'bg-warning' : 'bg-danger'}">${cuota.estado}</span></td>
                <td><button class="btn btn-sm btn-success" onclick="abrirModalPago(${cuota.id}, ${cuota.valor_cuota})">Registrar Pago</button></td>
            `;
            tbody.appendChild(tr);
        });
    } catch (error) {
        console.error('Error cargando cuotas:', error);
        tbody.innerHTML = '<tr><td colspan="6" class="text-center text-danger">Error al cargar la información.</td></tr>';
    }
}

// --- MANEJO DE MODAL Y REGISTRO DE PAGO ---
function abrirModalPago(cuotaId, monto) {
    const form = document.getElementById('formPago');
    form.reset();
    document.getElementById('pago-cuota-id').value = cuotaId;
    document.getElementById('pago-monto').value = monto;
    document.getElementById('pago-fecha').valueAsDate = new Date();
    
    modalPago.show();
}

async function registrarPago() {
    const form = document.getElementById('formPago');
    const formData = new FormData(form);
    const data = Object.fromEntries(formData.entries());

    // Convertir ID a entero
    if(data.forma_pago_id) data.forma_pago_id = parseInt(data.forma_pago_id);

    try {
        const response = await fetch('/api/admin/pagos', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });
        const result = await response.json();
        if (response.ok) {
            alert(result.message);
            modalPago.hide();
            if (clienteSeleccionadoId) cargarCuotasCliente(clienteSeleccionadoId);
            checkCajaEstado();
        } else {
            alert(`Error: ${result.error}`);
        }
    } catch (error) {
        console.error('Error al registrar el pago:', error);
        alert('Ocurrió un error de red al intentar registrar el pago.');
    }
}