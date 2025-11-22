document.addEventListener('DOMContentLoaded', function() {
    // 1. Iniciar lógica de Roles y Permisos (si existe la tabla)
    if (document.getElementById('lista-roles')) {
        configurarRolesYPermisos();
    }

    // 2. Iniciar lógica de Talonarios (si existe la tabla)
    // Se añade un pequeño delay o verificación directa
    if (document.getElementById('tablaTalonarios')) {
        loadTalonarios();
        setupTalonarioModal();
    }
});

// ========== LÓGICA DE ROLES Y PERMISOS ==========
let aplicaciones = [];
let rolSeleccionadoId = null;

async function configurarRolesYPermisos() {
    const lista = document.getElementById('lista-roles');
    if (!lista) return;

    // Cargar datos iniciales
    await cargarAplicaciones();
    await cargarRoles(lista);

    // Evento de selección de rol
    lista.addEventListener('click', function(event) {
        event.preventDefault();
        const target = event.target.closest('.list-group-item');
        if (target) {
            lista.querySelectorAll('.list-group-item.active').forEach(activeItem => activeItem.classList.remove('active'));
            target.classList.add('active');
            seleccionarRol(target.dataset.roleId);
        }
    });

    // Evento Guardar
    const btnGuardar = document.getElementById('btnGuardarPermisos');
    if (btnGuardar) {
        btnGuardar.addEventListener('click', async function() {
            if (!rolSeleccionadoId) {
                alert('Por favor, selecciona un rol primero.');
                return;
            }
            const checkboxes = document.querySelectorAll('#lista-permisos input[type="checkbox"]:checked');
            const aplicaciones_ids = Array.from(checkboxes).map(cb => parseInt(cb.value));
            
            try {
                const response = await fetch(`/api/admin/roles/${rolSeleccionadoId}`, {
                    method: 'PUT',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ aplicaciones_ids })
                });
                if (response.ok) {
                    alert('Permisos actualizados correctamente.');
                } else {
                    alert('Error al guardar los permisos.');
                }
            } catch(e) {
                console.error(e);
                alert('Error de red al guardar permisos.');
            }
        });
    }
}

async function cargarRoles(lista) {
    lista.innerHTML = '<div class="list-group-item">Cargando roles...</div>';
    try {
        const response = await fetch('/api/admin/roles');
        const roles = await response.json();
        lista.innerHTML = '';
        roles.forEach(rol => {
            const item = document.createElement('a');
            item.href = '#';
            item.className = 'list-group-item list-group-item-action';
            item.textContent = rol.name;
            item.dataset.roleId = rol.id;
            lista.appendChild(item);
        });
    } catch (e) {
        lista.innerHTML = '<div class="list-group-item text-danger">Error al cargar roles.</div>';
    }
}

async function cargarAplicaciones() {
    try {
        const response = await fetch('/api/admin/aplicaciones');
        aplicaciones = await response.json();
    } catch(e) { console.error("Error al cargar aplicaciones", e); }
}

async function seleccionarRol(id) {
    if (!id) return;
    rolSeleccionadoId = id;
    try {
        const response = await fetch(`/api/admin/roles/${id}`);
        const rol = await response.json();
        document.getElementById('rol-seleccionado-nombre').textContent = rol.name;
        document.getElementById('panel-vacio').style.display = 'none';
        document.getElementById('panel-permisos').style.display = 'block';
        renderizarPermisos(rol.permisos);
    } catch (e) { console.error("Error al seleccionar el rol:", e); }
}

function renderizarPermisos(permisosRol) {
    const container = document.getElementById('lista-permisos');
    if (!container) return;
    container.innerHTML = '';
    
    // Agrupar por módulo
    const modulos = aplicaciones.reduce((acc, app) => {
        (acc[app.modulo] = acc[app.modulo] || []).push(app);
        return acc;
    }, {});

    Object.keys(modulos).sort().forEach(modulo => {
        const moduloContainer = document.createElement('div');
        moduloContainer.className = 'module-group mb-3';
        moduloContainer.innerHTML = `<h5 class="border-bottom pb-2">${modulo}</h5>`;
        
        modulos[modulo].forEach(app => {
            const isChecked = permisosRol.includes(app.id);
            const checkboxDiv = document.createElement('div');
            checkboxDiv.className = 'form-check';
            checkboxDiv.innerHTML = `
                <input class="form-check-input" type="checkbox" value="${app.id}" id="app-${app.id}" ${isChecked ? 'checked' : ''}>
                <label class="form-check-label" for="app-${app.id}">${app.nombre}</label>
            `;
            moduloContainer.appendChild(checkboxDiv);
        });
        container.appendChild(moduloContainer);
    });
}


// ========== LÓGICA DE TALONARIOS ==========
let modalTalonario = null;

async function loadTalonarios() {
    const tabla = document.getElementById('tablaTalonarios');
    if (!tabla) return;
    const tbody = tabla.querySelector('tbody');
    tbody.innerHTML = '<tr><td colspan="8" class="text-center">Cargando...</td></tr>';

    try {
        const response = await fetch('/api/admin/talonarios');
        if (!response.ok) throw new Error('Error en respuesta de servidor');
        const talonarios = await response.json();
        
        tbody.innerHTML = ''; // Limpiar tabla
        if (talonarios.length === 0) {
            tbody.innerHTML = '<tr><td colspan="8" class="text-center">No hay talonarios registrados.</td></tr>';
            return;
        }
        
        talonarios.forEach(t => {
            // Manejo seguro de fechas
            let vigencia = 'Sin fecha';
            try {
                const inicio = t.fecha_inicio_vigencia ? new Date(t.fecha_inicio_vigencia + 'T00:00:00').toLocaleDateString('es-ES') : '';
                const fin = t.fecha_fin_vigencia ? new Date(t.fecha_fin_vigencia + 'T00:00:00').toLocaleDateString('es-ES') : '';
                vigencia = `${inicio} al ${fin}`;
            } catch(e) { console.error("Error fecha", e); }

            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td>${t.timbrado}</td>
                <td>${t.tipo_comprobante_nombre}</td>
                <td>${t.punto_expedicion}-${t.caja}</td>
                <td>${t.numero_actual}</td>
                <td>${t.numero_fin}</td>
                <td>${vigencia}</td>
                <td>${t.activo ? '<span class="badge bg-success">Sí</span>' : '<span class="badge bg-secondary">No</span>'}</td>
                <td>
                    <button class="btn btn-sm btn-warning btn-editar-talonario" data-id="${t.id}">Editar</button>
                    <button class="btn btn-sm btn-danger btn-eliminar-talonario" data-id="${t.id}">Borrar</button>
                </td>
            `;
            tbody.appendChild(tr);
        });

        // Listeners dinámicos
        tbody.querySelectorAll('.btn-editar-talonario').forEach(btn => {
            btn.addEventListener('click', () => editTalonario(btn.dataset.id));
        });
        tbody.querySelectorAll('.btn-eliminar-talonario').forEach(btn => {
            btn.addEventListener('click', () => deleteTalonario(btn.dataset.id));
        });

    } catch (error) {
        console.error("Error Talonarios:", error);
        tbody.innerHTML = '<tr><td colspan="8" class="text-center text-danger">Error al cargar talonarios.</td></tr>';
    }
}

async function loadTiposComprobanteDropdown() {
    try {
        const response = await fetch('/api/admin/tipos-comprobante');
        const tipos = await response.json();
        const select = document.getElementById('talonarioTipo');
        select.innerHTML = '<option value="">Seleccione...</option>';
        tipos.forEach(tipo => {
            select.innerHTML += `<option value="${tipo.id}">${tipo.nombre}</option>`;
        });
    } catch (error) {
        console.error('Error cargando tipos de comprobante:', error);
    }
}

function setupTalonarioModal() {
    const modalEl = document.getElementById('modalTalonario');
    if (!modalEl) return;
    
    modalTalonario = new bootstrap.Modal(modalEl);
    const form = document.getElementById('formTalonario');
    
    document.getElementById('btnNuevoTalonario').addEventListener('click', () => {
        document.getElementById('tituloModalTalonario').textContent = 'Nuevo Talonario';
        form.reset();
        document.getElementById('talonarioId').value = '';
        document.getElementById('talonarioActivo').checked = true;
        loadTiposComprobanteDropdown();
    });

    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        await guardarTalonario();
    });
}

async function guardarTalonario() {
    const id = document.getElementById('talonarioId').value;
    const data = {
        tipo_comprobante_id: document.getElementById('talonarioTipo').value,
        timbrado: document.getElementById('talonarioTimbrado').value,
        fecha_inicio_vigencia: document.getElementById('talonarioInicioVigencia').value,
        fecha_fin_vigencia: document.getElementById('talonarioFinVigencia').value,
        punto_expedicion: document.getElementById('talonarioPuntoExp').value,
        caja: document.getElementById('talonarioCaja').value,
        numero_actual: parseInt(document.getElementById('talonarioNumeroActual').value),
        numero_fin: parseInt(document.getElementById('talonarioNumeroFin').value),
        activo: document.getElementById('talonarioActivo').checked
    };
    
    const url = id ? `/api/admin/talonarios/${id}` : '/api/admin/talonarios';
    const method = id ? 'PUT' : 'POST';
    
    try {
        const response = await fetch(url, {
            method: method,
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });
        const result = await response.json();
        if (!response.ok) throw new Error(result.error || 'Error al guardar');
        
        modalTalonario.hide();
        loadTalonarios();
        alert('Talonario guardado con éxito');
    } catch (error) {
        alert(error.message);
    }
}

async function editTalonario(id) {
    await loadTiposComprobanteDropdown();
    try {
        const response = await fetch(`/api/admin/talonarios/${id}`);
        if (!response.ok) throw new Error('Error al obtener datos');
        const t = await response.json(); 

        document.getElementById('tituloModalTalonario').textContent = 'Editar Talonario';
        document.getElementById('talonarioId').value = t.id;
        document.getElementById('talonarioTipo').value = t.tipo_comprobante_id;
        document.getElementById('talonarioTimbrado').value = t.timbrado;
        
        // Formatear fecha para input date (YYYY-MM-DD)
        if(t.fecha_inicio_vigencia) document.getElementById('talonarioInicioVigencia').value = t.fecha_inicio_vigencia.split('T')[0];
        if(t.fecha_fin_vigencia) document.getElementById('talonarioFinVigencia').value = t.fecha_fin_vigencia.split('T')[0];
        
        document.getElementById('talonarioPuntoExp').value = t.punto_expedicion;
        document.getElementById('talonarioCaja').value = t.caja;
        document.getElementById('talonarioNumeroActual').value = t.numero_actual;
        document.getElementById('talonarioNumeroFin').value = t.numero_fin;
        document.getElementById('talonarioActivo').checked = t.activo;

        modalTalonario.show();
    } catch (error) {
        alert(error.message);
    }
}

async function deleteTalonario(id) {
    if (!confirm('¿Estás seguro de eliminar este talonario?')) return;
    try {
        const response = await fetch(`/api/admin/talonarios/${id}`, { method: 'DELETE' });
        if (!response.ok) throw new Error('Error al eliminar');
        loadTalonarios();
    } catch (error) {
        alert(error.message);
    }
}