/* static/js/tesoreria.js */

document.addEventListener('DOMContentLoaded', function() {
    // Detectar si estamos en Definiciones
    if (document.getElementById('tbodyEntidades')) {
        cargarEntidades();
        cargarCuentasBancarias();
    }
    
    // Detectar si estamos en Movimientos
    if (document.getElementById('tbodyDepositos')) {
        cargarDepositos();
        setupModalDeposito();
        setupTransferenciasTab();
    }
});

// --- VARIABLES GLOBALES ---
let modalEntidadInstance = null;
let modalCuentaInstance = null;
let entidadEditandoId = null;
let cuentaEditandoId = null;

// =======================================================
// GESTIÓN DE ENTIDADES FINANCIERAS
// =======================================================

window.abrirModalEntidad = function(entidad = null) {
    const modalEl = document.getElementById('modalEntidad');
    if (!modalEl) return;
    document.body.appendChild(modalEl); // Mover al body para evitar errores de z-index

    if (!modalEntidadInstance) {
        modalEntidadInstance = new bootstrap.Modal(modalEl, { backdrop: 'static', keyboard: false });
    }

    const form = document.getElementById('formEntidad');
    form.reset();
    entidadEditandoId = null;
    
    const title = document.getElementById('modalEntidadTitle');
    if(title) title.textContent = 'Nueva Entidad Financiera';

    if (entidad) {
        entidadEditandoId = entidad.id;
        if(title) title.textContent = 'Editar Entidad';
        document.getElementById('entidad_id').value = entidad.id;
        document.getElementById('entidad_nombre').value = entidad.nombre;
    }
    
    modalEntidadInstance.show();
};

window.cerrarModalEntidad = function() {
    if (modalEntidadInstance) modalEntidadInstance.hide();
    else {
        const el = document.getElementById('modalEntidad');
        const instance = bootstrap.Modal.getInstance(el);
        if(instance) instance.hide();
    }
};

window.guardarEntidad = async function() {
    const form = document.getElementById('formEntidad');
    const data = Object.fromEntries(new FormData(form));
    
    // Validación básica
    if (!data.nombre.trim()) return Toast.fire({ icon: 'warning', title: 'El nombre es obligatorio' });

    const url = entidadEditandoId ? `/api/admin/entidades-financieras/${entidadEditandoId}` : '/api/admin/entidades-financieras';
    const method = entidadEditandoId ? 'PUT' : 'POST';

    try {
        const response = await fetch(url, {
            method: method,
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });
        const result = await response.json();
        
        if (response.ok) {
            Toast.fire({ icon: 'success', title: 'Entidad guardada' });
            window.cerrarModalEntidad();
            cargarEntidades();
            cargarCuentasBancarias(); 
        } else { 
            Toast.fire({ icon: 'error', title: result.error });
        }
    } catch (e) {
        Toast.fire({ icon: 'error', title: 'Error de red' });
    }
};

async function cargarEntidades() {
    const tbody = document.getElementById('tbodyEntidades');
    if(!tbody) return;
    
    tbody.innerHTML = '<tr><td colspan="2" class="text-center">Cargando...</td></tr>';
    try {
        const response = await fetch('/api/admin/entidades-financieras');
        const entidades = await response.json();
        tbody.innerHTML = '';
        
        if (entidades.length === 0) {
            tbody.innerHTML = '<tr><td colspan="2" class="text-center text-muted">No hay entidades registradas.</td></tr>';
        }

        entidades.forEach(e => {
            const entidadStr = JSON.stringify(e).replace(/"/g, '&quot;');
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td>${e.nombre}</td>
                <td class="text-end">
                    <button class="btn btn-sm btn-warning" onclick="abrirModalEntidad(${entidadStr})"><i class="fas fa-edit"></i></button>
                    <button class="btn btn-sm btn-danger" onclick="eliminarEntidad(${e.id})"><i class="fas fa-trash"></i></button>
                </td>
            `;
            tbody.appendChild(tr);
        });
        
        actualizarSelectEntidades(entidades);

    } catch (e) {
        console.error(e);
        tbody.innerHTML = '<tr><td colspan="2" class="text-danger text-center">Error al cargar datos.</td></tr>';
    }
}

function actualizarSelectEntidades(entidades) {
    const selects = document.querySelectorAll('#cuenta_entidad, #deposito-cuenta, #transferCuentaOrigen, #transferCuentaDestino');
    selects.forEach(select => {
        if(!select) return;
        const valorActual = select.value;
        select.innerHTML = '<option value="">-- Seleccione --</option>';
        entidades.forEach(e => {
            select.innerHTML += `<option value="${e.id}">${e.nombre}</option>`;
        });
        if(valorActual) select.value = valorActual;
    });
}

window.eliminarEntidad = async function(id) {
    if (!confirm('¿Seguro que quieres eliminar esta entidad?')) return;
    try {
        const response = await fetch(`/api/admin/entidades-financieras/${id}`, { method: 'DELETE' });
        const result = await response.json();
        if (response.ok) {
            Toast.fire({ icon: 'success', title: 'Entidad eliminada' });
            cargarEntidades();
        } else { 
            Toast.fire({ icon: 'error', title: result.error });
        }
    } catch (e) { Toast.fire({ icon: 'error', title: 'Error de red' }); }
};


// =======================================================
// GESTIÓN DE CUENTAS BANCARIAS
// =======================================================

window.abrirModalCuenta = async function(cuenta = null) {
    const modalEl = document.getElementById('modalCuenta');
    if (!modalEl) return;
    document.body.appendChild(modalEl);

    if (!modalCuentaInstance) {
        modalCuentaInstance = new bootstrap.Modal(modalEl, { backdrop: 'static', keyboard: false });
    }

    const form = document.getElementById('formCuenta');
    form.reset();
    cuentaEditandoId = null;
    
    const title = document.getElementById('modalCuentaTitle');
    if(title) title.textContent = 'Nueva Cuenta Bancaria';

    const selectEntidad = document.getElementById('cuenta_entidad');
    if (selectEntidad && selectEntidad.options.length <= 1) {
        await cargarEntidades();
    }

    if (cuenta) {
        cuentaEditandoId = cuenta.id;
        if(title) title.textContent = 'Editar Cuenta Bancaria';
        document.getElementById('cuenta_id').value = cuenta.id;
        document.getElementById('cuenta_entidad').value = cuenta.entidad_id;
        document.getElementById('cuenta_numero').value = cuenta.numero_cuenta;
        document.getElementById('cuenta_titular').value = cuenta.titular;
        document.getElementById('cuenta_tipo').value = cuenta.tipo_cuenta;
        document.getElementById('cuenta_moneda').value = cuenta.moneda;
    }
    
    modalCuentaInstance.show();
};

window.cerrarModalCuenta = function() {
    if(modalCuentaInstance) modalCuentaInstance.hide();
    else {
        const el = document.getElementById('modalCuenta');
        const inst = bootstrap.Modal.getInstance(el);
        if(inst) inst.hide();
    }
};

window.guardarCuenta = async function() {
    const form = document.getElementById('formCuenta');
    const data = Object.fromEntries(new FormData(form));
    const url = cuentaEditandoId ? `/api/admin/cuentas-bancarias/${cuentaEditandoId}` : '/api/admin/cuentas-bancarias';
    const method = cuentaEditandoId ? 'PUT' : 'POST';

    try {
        const response = await fetch(url, {
            method: method,
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });
        const result = await response.json();
        if (response.ok) {
            Toast.fire({ icon: 'success', title: 'Cuenta guardada' });
            window.cerrarModalCuenta();
            cargarCuentasBancarias();
        } else { 
            Toast.fire({ icon: 'error', title: result.error });
        }
    } catch (e) { Toast.fire({ icon: 'error', title: 'Error de red' }); }
};

async function cargarCuentasBancarias() {
    const tbody = document.getElementById('tbodyCuentas');
    if(!tbody) return;
    
    tbody.innerHTML = '<tr><td colspan="7" class="text-center">Cargando...</td></tr>';
    try {
        const response = await fetch('/api/admin/cuentas-bancarias');
        const cuentas = await response.json();
        tbody.innerHTML = '';
        
        if(cuentas.length === 0) {
            tbody.innerHTML = '<tr><td colspan="7" class="text-center text-muted">No hay cuentas registradas.</td></tr>';
        }

        cuentas.forEach(c => {
            const cuentaStr = JSON.stringify(c).replace(/"/g, '&quot;');
            const btnEditar = c.tiene_movimientos 
                ? `<span class="badge bg-secondary" title="Bloqueado por movimientos">Bloqueado</span>` 
                : `<button class="btn btn-sm btn-warning" onclick="abrirModalCuenta(${cuentaStr})"><i class="fas fa-edit"></i></button>`;

            // FORMATO VISUAL UNIFICADO (formatMoney)
            const saldoVisual = formatMoney(c.saldo);

            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td>${c.entidad_nombre}</td>
                <td>${c.numero_cuenta}</td>
                <td>${c.titular}</td>
                <td>${c.tipo_cuenta}</td>
                <td>${c.moneda}</td>
                <td class="text-end fw-bold">Gs. ${saldoVisual}</td>
                <td class="text-end">
                    ${btnEditar}
                    <button class="btn btn-sm btn-danger" onclick="eliminarCuenta(${c.id})"><i class="fas fa-trash"></i></button>
                </td>
            `;
            tbody.appendChild(tr);
        });
    } catch (e) {
        tbody.innerHTML = '<tr><td colspan="7" class="text-center text-danger">Error al cargar cuentas.</td></tr>';
    }
}

window.eliminarCuenta = async function(id) {
    if (!confirm('¿Seguro que quieres eliminar esta cuenta?')) return;
    try {
        const response = await fetch(`/api/admin/cuentas-bancarias/${id}`, { method: 'DELETE' });
        const result = await response.json();
        if (response.ok) {
            Toast.fire({ icon: 'success', title: 'Cuenta eliminada' });
            cargarCuentasBancarias();
        } else { 
            Toast.fire({ icon: 'error', title: result.error });
        }
    } catch (e) { Toast.fire({ icon: 'error', title: 'Error de red' }); }
};

// Utilidad de compatibilidad para llamadas HTML directas
window.cerrarModal = function(modalId) {
    const el = document.getElementById(modalId);
    if (!el) return;
    const instance = bootstrap.Modal.getInstance(el);
    if (instance) instance.hide();
};


// =======================================================
// DEPÓSITOS Y TRANSFERENCIAS (MOVIMIENTOS)
// =======================================================
let modalDeposito = null;
let formDeposito = null;

function setupModalDeposito() {
    const modalEl = document.getElementById('modalDeposito');
    if (!modalEl) return;
    
    document.body.appendChild(modalEl);
    modalDeposito = new bootstrap.Modal(modalEl);
    formDeposito = document.getElementById('formDeposito');

    const btnNuevo = document.getElementById('btnNuevoDeposito');
    if(btnNuevo) {
        btnNuevo.addEventListener('click', async () => {
            formDeposito.reset();
            document.getElementById('deposito-fecha').valueAsDate = new Date();
            // Resetear input de dinero visual
            const inputMonto = document.getElementById('deposito-monto');
            if(inputMonto) inputMonto.value = '';
            
            await loadCuentasBancariasDropdown('deposito-cuenta');
        });
    }
    
    formDeposito.addEventListener('submit', async (e) => {
        e.preventDefault();
        await guardarDeposito();
    });
}

async function guardarDeposito() {
    // Obtener datos y PARSEAR MONTO
    const cuentaId = document.getElementById('deposito-cuenta').value;
    const fecha = document.getElementById('deposito-fecha').value;
    const montoRaw = document.getElementById('deposito-monto').value;
    const monto = parseMoney(montoRaw); // Usar parser global
    const ref = document.getElementById('deposito-referencia').value;
    const concepto = document.getElementById('deposito-concepto').value;

    if(!cuentaId || !fecha || monto <= 0) return Toast.fire({ icon: 'warning', title: 'Complete todos los campos' });

    const data = {
        cuenta_id: cuentaId,
        fecha_deposito: fecha,
        monto: monto,
        referencia: ref,
        concepto: concepto
    };

    try {
        const response = await fetch('/api/admin/depositos', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });
        const result = await response.json();
        if (response.ok) {
            Toast.fire({ icon: 'success', title: 'Depósito guardado' });
            modalDeposito.hide();
            cargarDepositos();
            if (document.getElementById('transferCuentaOrigen')) {
                 loadCuentasBancariasDropdown('transferCuentaOrigen');
                 loadCuentasBancariasDropdown('transferCuentaDestino');
            }
        } else { Toast.fire({ icon: 'error', title: result.error }); }
    } catch (e) { Toast.fire({ icon: 'error', title: 'Error de red' }); }
}

async function cargarDepositos() {
    const tbody = document.getElementById('tbodyDepositos');
    if(!tbody) return;
    tbody.innerHTML = '<tr><td colspan="6" class="text-center">Cargando...</td></tr>';
    try {
        const response = await fetch('/api/admin/depositos');
        const depositos = await response.json();
        tbody.innerHTML = '';
        
        if(depositos.length === 0) {
            tbody.innerHTML = '<tr><td colspan="6" class="text-center text-muted">Sin movimientos.</td></tr>';
            return;
        }

        depositos.forEach(d => {
            const montoFormateado = formatMoney(d.monto); // Formato visual
            const fechaFormateada = new Date(d.fecha_deposito + 'T00:00:00').toLocaleDateString('es-ES');
            const colorMonto = d.monto >= 0 ? 'text-success' : 'text-danger';
            
            tbody.innerHTML += `
                <tr>
                    <td>${fechaFormateada}</td>
                    <td>${d.cuenta_info}</td>
                    <td class="${colorMonto} fw-bold text-end">Gs. ${montoFormateado}</td>
                    <td>${d.referencia || '-'}</td>
                    <td><span class="badge ${d.estado === 'confirmado' ? 'bg-success' : 'bg-danger'}">${d.estado}</span></td>
                    <td class="text-end">
                        ${d.estado !== 'anulado' ? `<button class="btn btn-sm btn-outline-danger" onclick="anularDeposito(${d.id})"><i class="fas fa-ban"></i></button>` : ''}
                    </td>
                </tr>`;
        });
    } catch (e) { console.error(e); }
}

window.anularDeposito = async function(id) {
    if (!confirm('¿Anular este movimiento?')) return;
    try {
        const response = await fetch(`/api/admin/depositos/${id}`, { method: 'DELETE' });
        const result = await response.json();
        if (response.ok) {
            Toast.fire({ icon: 'success', title: 'Anulado correctamente' });
            cargarDepositos();
        } else { Toast.fire({ icon: 'error', title: result.error }); }
    } catch (e) { Toast.fire({ icon: 'error', title: 'Error de red' }); }
};

async function loadCuentasBancariasDropdown(selectId) {
    const select = document.getElementById(selectId);
    if (!select) return;
    try {
        const response = await fetch('/api/admin/cuentas-bancarias');
        const cuentas = await response.json();
        const val = select.value;
        select.innerHTML = '<option value="">Seleccione...</option>';
        cuentas.forEach(c => {
            // Mostrar saldo formateado en el dropdown
            select.innerHTML += `<option value="${c.id}">${c.entidad_nombre} - ${c.numero_cuenta} (Saldo: Gs. ${formatMoney(c.saldo)})</option>`;
        });
        if(val) select.value = val;
    } catch (e) { console.error(e); }
}

function setupTransferenciasTab() {
    const form = document.getElementById('formTransferencia');
    if (!form) return;
    
    loadCuentasBancariasDropdown('transferCuentaOrigen');
    loadCuentasBancariasDropdown('transferCuentaDestino');
    document.getElementById('transferFecha').valueAsDate = new Date(); 

    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        
        // PARSEAR MONTO DE INPUT VISUAL
        const montoRaw = document.getElementById('transferMonto').value;
        const monto = parseMoney(montoRaw);

        const data = {
            cuenta_origen_id: document.getElementById('transferCuentaOrigen').value,
            cuenta_destino_id: document.getElementById('transferCuentaDestino').value,
            monto: monto,
            fecha: document.getElementById('transferFecha').value,
            concepto: document.getElementById('transferConcepto').value || 'Transferencia'
        };

        if (data.cuenta_origen_id === data.cuenta_destino_id) {
            return Toast.fire({ icon: 'warning', title: 'Las cuentas deben ser diferentes' });
        }
        if (data.monto <= 0) {
            return Toast.fire({ icon: 'warning', title: 'Monto inválido' });
        }

        if (!confirm(`¿Confirmar transferencia de Gs. ${formatMoney(data.monto)}?`)) return;
        
        try {
            const response = await fetch('/api/admin/transferencias', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            });
            const result = await response.json();
            if (!response.ok) throw new Error(result.error);
            
            Toast.fire({ icon: 'success', title: 'Transferencia exitosa' });
            form.reset();
            document.getElementById('transferFecha').valueAsDate = new Date();
            // Limpiar input money
            document.getElementById('transferMonto').value = '';
            
            loadCuentasBancariasDropdown('transferCuentaOrigen');
            loadCuentasBancariasDropdown('transferCuentaDestino');
            cargarDepositos(); 
        } catch (error) { Toast.fire({ icon: 'error', title: error.message }); }
    });
}