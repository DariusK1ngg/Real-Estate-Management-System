document.addEventListener('DOMContentLoaded', function() {
    
    // --- Lógica para la página de CARGOS ---
    const tbodyCargos = document.getElementById('tbodyCargos');
    if (tbodyCargos) {
        cargarCargos();
        tbodyCargos.addEventListener('click', function(event) {
            const target = event.target.closest('button');
            if (!target) return;
            const cargoId = target.dataset.id;
            if (!cargoId) return;
            if (target.classList.contains('btn-edit-cargo')) {
                const cargo = allCargos.find(c => c.id == cargoId);
                if (cargo) abrirModalCargo(cargo);
            }
            if (target.classList.contains('btn-delete-cargo')) {
                eliminarCargo(cargoId);
            }
        });
    }

    // --- Lógica para la página de FUNCIONARIOS ---
    const tbodyFuncionarios = document.getElementById('tbodyFuncionarios');
    if (tbodyFuncionarios) {
        cargarFuncionarios();
        tbodyFuncionarios.addEventListener('click', function(event) {
            const target = event.target.closest('button');
            if (!target) return;
            const funcionarioId = target.dataset.id;
            if (!funcionarioId) return;
            if (target.classList.contains('btn-edit-funcionario')) {
                const funcionario = allFuncionarios.find(f => f.id == funcionarioId);
                if (funcionario) abrirModalFuncionario(funcionario);
            }
            if (target.classList.contains('btn-delete-funcionario')) {
                eliminarFuncionario(funcionarioId);
            }
        });
    }
});

// Variables globales
let allCargos = [];
let allFuncionarios = [];

// --- GESTIÓN DE CARGOS ---
let cargoEditandoId = null;

function abrirModalCargo(cargo = null) {
    const form = document.getElementById('formCargo');
    form.reset();
    cargoEditandoId = null;
    const modalTitle = document.getElementById('modalCargoTitle');

    if (cargo) {
        cargoEditandoId = cargo.id;
        modalTitle.textContent = 'Editar Cargo';
        form.querySelector('#cargo_id').value = cargo.id;
        form.querySelector('#cargo_nombre').value = cargo.nombre;
    } else {
        modalTitle.textContent = 'Nuevo Cargo';
    }
    // Llamamos a la función global corregida
    abrirModal('modalCargo');
}

async function guardarCargo() {
    const form = document.getElementById('formCargo');
    const data = Object.fromEntries(new FormData(form));
    const url = cargoEditandoId ? `/api/admin/cargos/${cargoEditandoId}` : '/api/admin/cargos';
    const method = cargoEditandoId ? 'PUT' : 'POST';

    try {
        const response = await fetch(url, {
            method,
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });
        const result = await response.json();
        if (response.ok) {
            alert('Cargo guardado.');
            // Llamamos a la función global corregida
            cerrarModal('modalCargo');
            cargarCargos();
        } else { alert(`Error: ${result.error}`); }
    } catch (e) {
        alert("Error de red al guardar cargo.");
    }
}

async function cargarCargos() {
    const tbody = document.getElementById('tbodyCargos');
    tbody.innerHTML = '<tr><td colspan="2" class="text-center">Cargando...</td></tr>';
    try {
        const response = await fetch('/api/admin/cargos');
        allCargos = await response.json(); 
        tbody.innerHTML = '';
        allCargos.forEach(c => {
            tbody.innerHTML += `
                <tr>
                    <td>${c.nombre}</td>
                    <td>
                        <button class="btn btn-sm btn-warning btn-edit-cargo" data-id="${c.id}">Editar</button>
                        <button class="btn btn-sm btn-danger btn-delete-cargo" data-id="${c.id}">Eliminar</button>
                    </td>
                </tr>`;
        });
    } catch(e) {
        tbody.innerHTML = '<tr><td colspan="2" class="text-danger">Error al cargar los cargos.</td></tr>';
    }
}

async function eliminarCargo(id) {
    if (!confirm('¿Seguro?')) return;
    const response = await fetch(`/api/admin/cargos/${id}`, { method: 'DELETE' });
    const result = await response.json();
    if (response.ok) {
        alert(result.message);
        cargarCargos();
    } else { alert(`Error: ${result.error}`); }
}

// --- GESTIÓN DE FUNCIONARIOS ---
let funcionarioEditandoId = null;

async function abrirModalFuncionario(funcionario = null) {
    const form = document.getElementById('formFuncionario');
    form.reset();
    funcionarioEditandoId = null;
    const modalTitle = document.getElementById('modalFuncionarioTitle');

    await Promise.all([
        poblarSelectCargos(form),
        poblarCheckboxesRoles(form)
    ]);

    if (funcionario) {
        funcionarioEditandoId = funcionario.id;
        modalTitle.textContent = 'Editar Funcionario';
        form.querySelector('[name="nombre"]').value = funcionario.nombre;
        form.querySelector('[name="apellido"]').value = funcionario.apellido;
        form.querySelector('[name="documento"]').value = funcionario.documento;
        form.querySelector('[name="usuario"]').value = funcionario.usuario;
        form.querySelector('[name="cargo_id"]').value = funcionario.cargo_id;
        form.querySelector('[name="estado"]').value = funcionario.estado;
        
        try {
            const response = await fetch(`/api/admin/funcionarios/${funcionario.id}`);
            const data = await response.json();
            const userRoles = data.roles || [];
            form.querySelectorAll('#roles-container input[type="checkbox"]').forEach(checkbox => {
                checkbox.checked = userRoles.includes(checkbox.dataset.rolName);
            });
        } catch (e) { console.error("Error roles", e); }

    } else {
        modalTitle.textContent = 'Nuevo Funcionario';
        form.querySelector('[name="fecha_ingreso"]').valueAsDate = new Date();
    }
    // Llamamos a la función global corregida
    abrirModal('modalFuncionario');
}

async function guardarFuncionario() {
    const form = document.getElementById('formFuncionario');
    const data = Object.fromEntries(new FormData(form));

    data.roles_ids = Array.from(form.querySelectorAll('#roles-container input:checked')).map(cb => cb.value);
    data.es_vendedor = form.querySelector('#es_vendedor').checked;
    if (!data.password) delete data.password;

    const url = funcionarioEditandoId ? `/api/admin/funcionarios/${funcionarioEditandoId}` : '/api/admin/funcionarios';
    const method = funcionarioEditandoId ? 'PUT' : 'POST';
    if(funcionarioEditandoId) data.nombre_completo = `${data.nombre} ${data.apellido}`;

    try {
        const response = await fetch(url, {
            method,
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });
        const result = await response.json();
        if (response.ok) {
            alert('Funcionario guardado.');
            // Llamamos a la función global corregida
            cerrarModal('modalFuncionario');
            cargarFuncionarios();
        } else { alert(`Error: ${result.error}`); }
    } catch (e) {
        alert("Ocurrió un error al guardar funcionario.");
    }
}

async function cargarFuncionarios() {
    const tbody = document.getElementById('tbodyFuncionarios');
    tbody.innerHTML = '<tr><td colspan="6" class="text-center">Cargando...</td></tr>';
    try {
        const response = await fetch('/api/admin/funcionarios');
        allFuncionarios = await response.json(); 
        tbody.innerHTML = '';
        allFuncionarios.forEach(f => {
            tbody.innerHTML += `
                <tr>
                    <td>${f.nombre_completo}</td>
                    <td>${f.usuario}</td>
                    <td>${f.documento}</td>
                    <td>${f.cargo_nombre}</td>
                    <td><span class="estado-${f.estado}">${f.estado}</span></td>
                    <td>
                        <button class="btn btn-sm btn-warning btn-edit-funcionario" data-id="${f.id}">Editar</button>
                        <button class="btn btn-sm btn-danger btn-delete-funcionario" data-id="${f.id}">Eliminar</button>
                    </td>
                </tr>`;
        });
    } catch(e) {
        tbody.innerHTML = '<tr><td colspan="6" class="text-danger">Error al cargar funcionarios.</td></tr>';
    }
}

async function eliminarFuncionario(id) {
    if (!confirm('¿Seguro?')) return;
    const response = await fetch(`/api/admin/funcionarios/${id}`, { method: 'DELETE' });
    const result = await response.json();
    if (response.ok) {
        alert(result.message);
        cargarFuncionarios();
    } else { alert(`Error: ${result.error}`); }
}

async function poblarSelectCargos(form) {
    const select = form.querySelector('[name="cargo_id"]');
    select.innerHTML = '<option>Cargando...</option>';
    try {
        const response = await fetch('/api/admin/cargos');
        const cargos = await response.json();
        select.innerHTML = '';
        cargos.forEach(c => select.innerHTML += `<option value="${c.id}">${c.nombre}</option>`);
    } catch (e) { select.innerHTML = '<option class="text-danger">Error</option>'; }
}

async function poblarCheckboxesRoles(form) {
    const container = form.querySelector('#roles-container');
    container.innerHTML = 'Cargando...';
    try {
        const response = await fetch('/api/admin/roles');
        const roles = await response.json();
        container.innerHTML = '';
        roles.forEach(r => {
            container.innerHTML += `
                <div class="form-check">
                    <input class="form-check-input" type="checkbox" value="${r.id}" id="rol-${r.id}" data-rol-name="${r.name}">
                    <label class="form-check-label" for="rol-${r.id}">${r.name}</label>
                </div>`;
        });
    } catch (e) { container.innerHTML = '<span class="text-danger">Error</span>'; }
}

// =========================================================
// CORRECCIÓN: FUNCIONES DE MODAL MANUALES (SIN BOOTSTRAP JS)
// =========================================================
// Esto asegura que funcione con tu CSS personalizado y arregla
// el problema de que no se cierra o se oscurece la pantalla.

window.abrirModal = function(id) {
    const el = document.getElementById(id);
    if (el) {
        el.style.display = 'block'; // Fuerza la visualización manual
    }
};

window.cerrarModal = function(id) {
    const el = document.getElementById(id);
    if (el) {
        el.style.display = 'none'; // Fuerza el ocultamiento manual
    }
    
    document.querySelectorAll('.modal-backdrop').forEach(el => el.remove());
    document.body.classList.remove('modal-open');
    document.body.style.overflow = 'auto';
};