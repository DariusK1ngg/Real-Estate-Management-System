document.addEventListener('DOMContentLoaded', function() {
    cargarClientes();
    cargarParametrosCliente();
});

// --- MANEJO DE SELECTS DINÁMICOS ---
async function cargarParametrosCliente() {
    await cargarSelect('/api/admin/tipos-documentos', 'selectTipoDoc');
    await cargarSelect('/api/admin/profesiones', 'selectProfesion');
    await cargarSelect('/api/admin/tipos-cliente', 'selectTipoCliente');
    await cargarSelect('/api/admin/ciudades', 'selectCiudad');
}

async function cargarSelect(url, elementId) {
    const select = document.getElementById(elementId);
    if (!select) return;
    try {
        const res = await fetch(url);
        const data = await res.json();
        select.innerHTML = '<option value="">-- Seleccione --</option>';
        data.forEach(item => {
            select.innerHTML += `<option value="${item.id}">${item.nombre}</option>`;
        });
    } catch (e) {
        console.error(`Error cargando ${elementId}:`, e);
        select.innerHTML = '<option value="">Error al cargar</option>';
    }
}

// Listener para cambio de ciudad (cascada)
document.getElementById('selectCiudad').addEventListener('change', function(e) {
    const ciudadId = e.target.value;
    const selectBarrio = document.getElementById('selectBarrio');
    
    if (!ciudadId) {
        selectBarrio.innerHTML = '<option value="">-- Primero seleccione Ciudad --</option>';
        selectBarrio.disabled = true;
        return;
    }
    
    selectBarrio.disabled = false;
    cargarSelect(`/api/admin/barrios?ciudad_id=${ciudadId}`, 'selectBarrio');
});

// --- MANEJO DEL MODAL ---
function abrirModal(id) { document.getElementById(id).style.display = 'block'; }
function cerrarModal(id) { document.getElementById(id).style.display = 'none'; }

function abrirModalNuevo() {
    document.getElementById('formCliente').reset();
    document.getElementById('cliente-id').value = '';
    
    // Resetear select de barrios
    const selectBarrio = document.getElementById('selectBarrio');
    selectBarrio.innerHTML = '<option value="">-- Primero seleccione Ciudad --</option>';
    selectBarrio.disabled = true;

    document.getElementById('modal-title').textContent = 'Nuevo Cliente';
    abrirModal('modalCliente');
}

// --- API CALLS (ABM) ---
async function cargarClientes() {
    const tbody = document.getElementById('tablaClientes');
    tbody.innerHTML = '<tr><td colspan="6" class="text-center">Cargando...</td></tr>';
    try {
        const response = await fetch('/api/admin/clientes');
        const clientes = await response.json();
        tbody.innerHTML = '';
        clientes.forEach(c => {
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td>${c.nombre_completo}</td>
                <td>${c.tipo_documento} ${c.documento}</td>
                <td>${c.telefono}</td>
                <td>${c.email}</td>
                <td><span class="badge estado-${c.estado}">${c.estado}</span></td>
                <td>
                    <button class="btn btn-sm btn-info" onclick="editarCliente(${c.id})">Editar</button>
                    <button class="btn btn-sm btn-danger" onclick="eliminarCliente(${c.id})">Eliminar</button>
                </td>
            `;
            tbody.appendChild(tr);
        });
    } catch (error) {
        console.error('Error al cargar clientes:', error);
        tbody.innerHTML = '<tr><td colspan="6" class="text-center text-danger">Error al cargar los clientes.</td></tr>';
    }
}

async function editarCliente(id) {
    try {
        const response = await fetch(`/api/admin/clientes/${id}`);
        if (!response.ok) throw new Error('Cliente no encontrado');
        const cliente = await response.json();
        
        document.getElementById('formCliente').reset();
        document.getElementById('cliente-id').value = cliente.id;
        
        // Asignar valores a selects
        document.getElementById('selectTipoDoc').value = cliente.tipo_documento_id || "";
        document.getElementById('selectProfesion').value = cliente.profesion_id || "";
        document.getElementById('selectTipoCliente').value = cliente.tipo_cliente_id || "";
        
        // Asignar Ciudad y cargar Barrios
        document.getElementById('selectCiudad').value = cliente.ciudad_id || "";
        
        if (cliente.ciudad_id) {
            const selectBarrio = document.getElementById('selectBarrio');
            selectBarrio.disabled = false;
            // Esperar a que carguen los barrios para seleccionar el correcto
            await cargarSelect(`/api/admin/barrios?ciudad_id=${cliente.ciudad_id}`, 'selectBarrio');
            selectBarrio.value = cliente.barrio_id || "";
        } else {
            document.getElementById('selectBarrio').disabled = true;
        }

        document.querySelector('#formCliente [name="documento"]').value = cliente.documento;
        document.querySelector('#formCliente [name="nombre"]').value = cliente.nombre;
        document.querySelector('#formCliente [name="apellido"]').value = cliente.apellido;
        document.querySelector('#formCliente [name="telefono"]').value = cliente.telefono;
        document.querySelector('#formCliente [name="email"]').value = cliente.email;
        document.querySelector('#formCliente [name="direccion"]').value = cliente.direccion;
        document.querySelector('#formCliente [name="estado"]').value = cliente.estado;
        
        document.getElementById('modal-title').textContent = 'Editar Cliente';
        abrirModal('modalCliente');
    } catch (error) {
        console.error(error);
        alert('No se pudo cargar la información del cliente.');
    }
}

async function guardarCliente() {
    const id = document.getElementById('cliente-id').value;
    const form = document.getElementById('formCliente');
    const formData = new FormData(form);
    const data = Object.fromEntries(formData.entries());

    // Convertir IDs a enteros
    if(data.tipo_documento_id) data.tipo_documento_id = parseInt(data.tipo_documento_id);
    if(data.profesion_id) data.profesion_id = parseInt(data.profesion_id);
    if(data.tipo_cliente_id) data.tipo_cliente_id = parseInt(data.tipo_cliente_id);
    if(data.ciudad_id) data.ciudad_id = parseInt(data.ciudad_id);
    if(data.barrio_id) data.barrio_id = parseInt(data.barrio_id);

    const url = id ? `/api/admin/clientes/${id}` : '/api/admin/clientes';
    const method = id ? 'PUT' : 'POST';

    try {
        const response = await fetch(url, {
            method: method,
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });
        const result = await response.json();
        if (response.ok) {
            alert(`Cliente ${id ? 'actualizado' : 'creado'} correctamente.`);
            cerrarModal('modalCliente');
            cargarClientes();
        } else {
            alert(`Error: ${result.error}`);
        }
    } catch (error) {
        console.error('Error al guardar cliente:', error);
    }
}

async function eliminarCliente(id) {
    if (!confirm('¿Estás seguro de que quieres eliminar este cliente? Esta acción no se puede deshacer.')) {
        return;
    }
    try {
        const response = await fetch(`/api/admin/clientes/${id}`, { method: 'DELETE' });
        const result = await response.json();
        if (response.ok) {
            alert(result.message);
            cargarClientes();
        } else {
            alert(`Error: ${result.error}`);
        }
    } catch (error) {
        console.error('Error al eliminar cliente:', error);
    }
}