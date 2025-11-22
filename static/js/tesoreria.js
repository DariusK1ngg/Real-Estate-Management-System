document.addEventListener('DOMContentLoaded', function() {
    // Carga inicial de datos si estamos en la página de Definiciones
    if (document.getElementById('tbodyEntidades')) {
        cargarEntidades();
        cargarCuentasBancarias();
    }
    
    // Carga inicial si estamos en Movimientos
    if (document.getElementById('tbodyDepositos')) {
        cargarDepositos();
        setupModalDeposito();
        setupTransferenciasTab();
    }
});

// --- VARIABLES GLOBALES DE MODALES ---
let modalEntidadInstance = null;
let modalCuentaInstance = null;
let entidadEditandoId = null;
let cuentaEditandoId = null;

// =======================================================
// GESTIÓN DE ENTIDADES FINANCIERAS
// =======================================================

// Abrir Modal (Nueva / Editar)
window.abrirModalEntidad = function(entidad = null) {
    const modalEl = document.getElementById('modalEntidad');
    if (!modalEl) return;

    // [CRÍTICO] Mover al body para evitar problemas de z-index (pantalla oscura)
    document.body.appendChild(modalEl);

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

// Cerrar Modal
window.cerrarModalEntidad = function() {
    if (modalEntidadInstance) modalEntidadInstance.hide();
    else {
        const el = document.getElementById('modalEntidad');
        const instance = bootstrap.Modal.getInstance(el);
        if(instance) instance.hide();
    }
};

// Guardar Entidad
window.guardarEntidad = async function() {
    const form = document.getElementById('formEntidad');
    const data = Object.fromEntries(new FormData(form));
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
            alert('Entidad guardada correctamente.');
            window.cerrarModalEntidad();
            cargarEntidades();
            cargarCuentasBancarias(); // Actualizar selects
        } else { 
            alert(`Error: ${result.error}`); 
        }
    } catch (e) {
        alert('Error de red al guardar entidad.');
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
            // Escapar comillas para el HTML
            const entidadStr = JSON.stringify(e).replace(/"/g, '&quot;');
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td>${e.nombre}</td>
                <td class="text-end">
                    <button class="btn btn-sm btn-warning" onclick="abrirModalEntidad(${entidadStr})">
                        <i class="fas fa-edit"></i> Editar
                    </button>
                    <button class="btn btn-sm btn-danger" onclick="eliminarEntidad(${e.id})">
                        <i class="fas fa-trash"></i>
                    </button>
                </td>
            `;
            tbody.appendChild(tr);
        });
        
        // Actualizar dropdowns en otros formularios
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
        // Intentar restaurar valor
        if(valorActual) select.value = valorActual;
    });
}

window.eliminarEntidad = async function(id) {
    if (!confirm('¿Seguro que quieres eliminar esta entidad?')) return;
    try {
        const response = await fetch(`/api/admin/entidades-financieras/${id}`, { method: 'DELETE' });
        const result = await response.json();
        if (response.ok) {
            alert(result.message);
            cargarEntidades();
        } else { 
            alert(`Error: ${result.error}`); 
        }
    } catch (e) { alert('Error de red.'); }
};


// =======================================================
// GESTIÓN DE CUENTAS BANCARIAS
// =======================================================

window.abrirModalCuenta = async function(cuenta = null) {
    const modalEl = document.getElementById('modalCuenta');
    if (!modalEl) return;

    // [CRÍTICO] Mover al body
    document.body.appendChild(modalEl);

    if (!modalCuentaInstance) {
        modalCuentaInstance = new bootstrap.Modal(modalEl, { backdrop: 'static', keyboard: false });
    }

    const form = document.getElementById('formCuenta');
    form.reset();
    cuentaEditandoId = null;
    
    const title = document.getElementById('modalCuentaTitle');
    if(title) title.textContent = 'Nueva Cuenta Bancaria';

    // Verificar si hay entidades cargadas
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

// Cerrar Modal Cuenta
// Como en el HTML usaste onclick="cerrarModal('modalCuenta')", necesitamos soportar esa llamada genérica
// O podemos actualizar el HTML. Para ser compatibles con tu HTML actual, definimos cerrarModal globalmente en main.js
// Pero aquí definimos la específica por si acaso.
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
            alert('Cuenta guardada correctamente.');
            window.cerrarModalCuenta();
            cargarCuentasBancarias();
        } else { 
            alert(`Error: ${result.error}`); 
        }
    } catch (e) { alert('Error de red.'); }
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
            
            // Lógica: Ocultar botón editar si tiene movimientos
            const btnEditar = c.tiene_movimientos 
                ? `<span class="badge bg-secondary" title="No editable por tener movimientos">Bloqueado</span>` 
                : `<button class="btn btn-sm btn-warning" onclick="abrirModalCuenta(${cuentaStr})"><i class="fas fa-edit"></i> Editar</button>`;

            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td>${c.entidad_nombre}</td>
                <td>${c.numero_cuenta}</td>
                <td>${c.titular}</td>
                <td>${c.tipo_cuenta}</td>
                <td>${c.moneda}</td>
                <td class="text-end fw-bold">${c.saldo.toLocaleString('es-PY')}</td>
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
            alert(result.message);
            cargarCuentasBancarias();
        } else { 
            alert(`Error: ${result.error}`); 
        }
    } catch (e) { alert('Error de red.'); }
};


// =======================================================
// UTILIDAD COMPATIBILIDAD
// =======================================================
// Esta función captura las llamadas del HTML `onclick="cerrarModal('modalEntidad')"` 
// y las redirige a la lógica correcta de Bootstrap.
window.cerrarModal = function(modalId) {
    const el = document.getElementById(modalId);
    if (!el) return;
    const instance = bootstrap.Modal.getInstance(el);
    if (instance) {
        instance.hide();
    } else {
        // Fallback por si se abrió manualmente (no debería pasar con este código)
        el.style.display = 'none';
        // Remover backdrop manualmente si quedó pegado
        document.querySelectorAll('.modal-backdrop').forEach(bd => bd.remove());
    }
};


// =======================================================
// DEPÓSITOS Y TRANSFERENCIAS (Página Movimientos)
// =======================================================
let modalDeposito = null;
let formDeposito = null;

function setupModalDeposito() {
    const modalEl = document.getElementById('modalDeposito');
    if (!modalEl) return;
    
    // Mover al body
    document.body.appendChild(modalEl);
    modalDeposito = new bootstrap.Modal(modalEl);
    formDeposito = document.getElementById('formDeposito');

    const btnNuevo = document.getElementById('btnNuevoDeposito');
    if(btnNuevo) {
        btnNuevo.addEventListener('click', async () => {
            formDeposito.reset();
            document.getElementById('deposito-fecha').valueAsDate = new Date();
            await loadCuentasBancariasDropdown('deposito-cuenta');
        });
    }
    
    formDeposito.addEventListener('submit', async (e) => {
        e.preventDefault();
        await guardarDeposito();
    });
}

async function guardarDeposito() {
    const data = Object.fromEntries(new FormData(formDeposito).entries());
    try {
        const response = await fetch('/api/admin/depositos', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });
        const result = await response.json();
        if (response.ok) {
            alert('Depósito guardado.');
            modalDeposito.hide();
            cargarDepositos();
            // Recargar saldos en pestaña transferencias si existe
            if (document.getElementById('transferCuentaOrigen')) {
                 loadCuentasBancariasDropdown('transferCuentaOrigen');
                 loadCuentasBancariasDropdown('transferCuentaDestino');
            }
        } else { alert('Error: ' + result.error); }
    } catch (e) { alert('Error de red'); }
}

async function cargarDepositos() {
    const tbody = document.getElementById('tbodyDepositos');
    if(!tbody) return;
    tbody.innerHTML = '<tr><td colspan="6" class="text-center">Cargando...</td></tr>';
    try {
        const response = await fetch('/api/admin/depositos');
        const depositos = await response.json();
        tbody.innerHTML = '';
        depositos.forEach(d => {
            const montoFormateado = d.monto.toLocaleString('es-PY');
            const fechaFormateada = new Date(d.fecha_deposito + 'T00:00:00').toLocaleDateString('es-ES');
            tbody.innerHTML += `
                <tr>
                    <td>${fechaFormateada}</td>
                    <td>${d.cuenta_info}</td>
                    <td style="color: ${d.monto >= 0 ? 'green' : 'red'}; text-align:right;">${montoFormateado}</td>
                    <td>${d.referencia}</td>
                    <td><span class="badge ${d.estado === 'confirmado' ? 'bg-success' : 'bg-danger'}">${d.estado}</span></td>
                    <td>
                        ${d.estado !== 'anulado' ? `<button class="btn btn-sm btn-danger" onclick="anularDeposito(${d.id})">Anular</button>` : ''}
                    </td>
                </tr>`;
        });
    } catch (e) { console.error(e); }
}

window.anularDeposito = async function(id) {
    if (!confirm('¿Anular depósito?')) return;
    try {
        const response = await fetch(`/api/admin/depositos/${id}`, { method: 'DELETE' });
        const result = await response.json();
        if (response.ok) {
            alert(result.message);
            cargarDepositos();
        } else { alert('Error: ' + result.error); }
    } catch (e) { alert('Error de red'); }
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
            select.innerHTML += `<option value="${c.id}">${c.entidad_nombre} - ${c.numero_cuenta} (Saldo: ${c.saldo.toLocaleString('es-PY')})</option>`;
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
        const data = {
            cuenta_origen_id: document.getElementById('transferCuentaOrigen').value,
            cuenta_destino_id: document.getElementById('transferCuentaDestino').value,
            monto: parseFloat(document.getElementById('transferMonto').value),
            fecha: document.getElementById('transferFecha').value,
            concepto: document.getElementById('transferConcepto').value || 'Transferencia'
        };

        if (data.cuenta_origen_id === data.cuenta_destino_id) {
            alert('Cuentas origen y destino deben ser diferentes.');
            return;
        }

        if (!confirm(`¿Confirmar transferencia de Gs. ${data.monto.toLocaleString('es-PY')}?`)) return;
        
        try {
            const response = await fetch('/api/admin/transferencias', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            });
            const result = await response.json();
            if (!response.ok) throw new Error(result.error);
            
            alert('Transferencia exitosa');
            form.reset();
            document.getElementById('transferFecha').valueAsDate = new Date();
            loadCuentasBancariasDropdown('transferCuentaOrigen');
            loadCuentasBancariasDropdown('transferCuentaDestino');
            cargarDepositos(); 
        } catch (error) { alert(error.message); }
    });
}