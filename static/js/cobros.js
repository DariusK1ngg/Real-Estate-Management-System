// static/js/cobros.js

let clienteSeleccionadoId = null;
let modalPago = null;
let modalAbrirCaja = null;
let cajaAbiertaGlobal = false; // NUEVA VARIABLE PARA CONTROLAR EL ESTADO

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
    
    if (text.includes('efectivo') || e.target.value === "") {
        divCuenta.style.display = 'none';
        selectCuenta.required = false;
        selectCuenta.value = "";
    } else {
        divCuenta.style.display = 'block';
        selectCuenta.required = true;
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
        
        // Actualizamos variable global
        cajaAbiertaGlobal = data.caja_abierta;

        if (data.caja_abierta) {
            const saldoFormateado = (data.saldo_actual || 0).toLocaleString('es-PY');
            estadoCajaSpan.innerHTML = `ABIERTA: ${data.caja_descripcion} (Saldo: Gs. ${saldoFormateado})`;
            estadoCajaSpan.className = 'badge bg-success'; // Bootstrap 5 usa bg-success
            btnAbrirCaja.style.display = 'none';
            btnCerrarCaja.style.display = 'inline-block';
        } else {
            estadoCajaSpan.innerHTML = 'CERRADA';
            estadoCajaSpan.className = 'badge bg-danger';
            btnAbrirCaja.style.display = 'inline-block';
            btnCerrarCaja.style.display = 'none';
        }

        // --- NUEVO: Aplicar bloqueo visual y funcional a la sección de cuotas ---
        actualizarBloqueoInterfaz();

    } catch (error) {
        console.error('Error al chequear estado de caja:', error);
        estadoCajaSpan.innerHTML = 'Error de conexión';
        estadoCajaSpan.className = 'badge bg-warning text-dark';
    }
}

// Función auxiliar para bloquear/desbloquear la UI
function actualizarBloqueoInterfaz() {
    const seccionCuotas = document.getElementById('seccion-cuotas'); // ID que añadiremos al HTML
    const alerta = document.getElementById('alertaCajaCerrada');
    
    if (!cajaAbiertaGlobal) {
        // Bloquear
        if(seccionCuotas) {
            seccionCuotas.style.opacity = '0.5';
            seccionCuotas.style.pointerEvents = 'none'; // Evita clicks en botones dentro
        }
        if(alerta) alerta.style.display = 'block';
        
        // Asegurar que los botones existentes se deshabiliten visualmente
        document.querySelectorAll('.btn-pagar-cuota').forEach(btn => btn.disabled = true);
    } else {
        // Desbloquear
        if(seccionCuotas) {
            seccionCuotas.style.opacity = '1';
            seccionCuotas.style.pointerEvents = 'auto';
        }
        if(alerta) alerta.style.display = 'none';
        
        document.querySelectorAll('.btn-pagar-cuota').forEach(btn => btn.disabled = false);
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
        
        // alert(data.message); // Opcional, a veces es mejor solo actualizar
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

// --- MODIFICADO: MUESTRA INTERÉS POR MORA Y GESTIONA BLOQUEO ---
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
            
            // --- Lógica Visual de Mora ---
            let infoInteres = '';
            let claseMonto = '';
            let btnClass = 'btn-success';
            
            if (cuota.interes_mora > 0) {
                const interesFmt = cuota.interes_mora.toLocaleString('es-PY', {maximumFractionDigits: 0});
                infoInteres = `<div class="text-danger fw-bold" style="font-size: 0.85em;">+ Mora: Gs. ${interesFmt}</div>`;
                claseMonto = 'text-danger';
                btnClass = 'btn-warning';
            }

            const diasAtrasoTexto = cuota.dias_atraso > 0 
                ? `<span class="badge bg-danger">${cuota.dias_atraso} días atraso</span>` 
                : '<span class="badge bg-success">Al día</span>';

            // --- LÓGICA DE BLOQUEO DE BOTÓN ---
            // Si la caja está cerrada, el botón nace deshabilitado
            const disabledAttr = !cajaAbiertaGlobal ? 'disabled' : '';

            tr.innerHTML = `
                <td>${cuota.numero_contrato}</td>
                <td>${cuota.numero_cuota}</td>
                <td>${fechaFormateada} <br> ${diasAtrasoTexto}</td>
                <td>
                    <strong class="${claseMonto}">Gs. ${montoFormateado}</strong>
                    ${infoInteres}
                </td>
                <td><span class="badge ${cuota.estado === 'pendiente' ? 'bg-secondary' : 'bg-danger'}">${cuota.estado}</span></td>
                <td>
                    <button class="btn btn-sm ${btnClass} btn-pagar-cuota" ${disabledAttr} onclick="abrirModalPago(${cuota.id}, ${cuota.total_pagar})">
                        Pagar Gs. ${cuota.total_pagar.toLocaleString('es-PY')}
                    </button>
                </td>
            `;
            tbody.appendChild(tr);
        });
        
        // Re-validar estado visual por seguridad
        actualizarBloqueoInterfaz();

    } catch (error) {
        console.error('Error cargando cuotas:', error);
        tbody.innerHTML = '<tr><td colspan="6" class="text-center text-danger">Error al cargar la información.</td></tr>';
    }
}
// --------------------------------------------

// --- MANEJO DE MODAL Y REGISTRO DE PAGO ---
function abrirModalPago(cuotaId, montoTotal) {
    // Doble chequeo de seguridad
    if (!cajaAbiertaGlobal) {
        alert("Debe abrir la caja para realizar cobros.");
        return;
    }

    const form = document.getElementById('formPago');
    form.reset();
    document.getElementById('pago-cuota-id').value = cuotaId;
    document.getElementById('pago-monto').value = montoTotal; 
    document.getElementById('pago-fecha').valueAsDate = new Date();
    
    // Resetear visibilidad de cuenta bancaria
    document.getElementById('div-cuenta-destino').style.display = 'none';
    document.getElementById('selectCuentaDestino').required = false;

    modalPago.show();
}

async function registrarPago() {
    // Triple chequeo de seguridad
    if (!cajaAbiertaGlobal) {
        alert("La caja está cerrada.");
        modalPago.hide();
        return;
    }

    const form = document.getElementById('formPago');
    const formData = new FormData(form);
    const data = Object.fromEntries(formData.entries());

    if(data.forma_pago_id) data.forma_pago_id = parseInt(data.forma_pago_id);

    try {
        const response = await fetch('/api/admin/pagos', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });
        const result = await response.json();
        
        if (response.ok) {
            modalPago.hide();
            if (result.pago_id) {
                window.open(`/admin/cobros/recibo/${result.pago_id}`, '_blank');
            }
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