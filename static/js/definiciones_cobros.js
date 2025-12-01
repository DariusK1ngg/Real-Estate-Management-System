document.addEventListener('DOMContentLoaded', function() {
    // Carga inicial de datos
    cargarDatosCobros('formas-pago');
    cargarDatosCobros('tipos-cliente');
    cargarDatosCobros('condiciones-pago');

    // Configuración del modal
    setupModalCobros();
});

// Variables globales específicas para Cobros
let editandoIdCobros = null;
let apiEndpointCobros = '';
let modalInstanciaCobros = null;
let formInstanciaCobros = null;

function setupModalCobros() {
    const modalEl = document.getElementById('modalSimpleCobros');
    if (!modalEl) return;
    
    // Usamos Bootstrap Modal
    modalInstanciaCobros = new bootstrap.Modal(modalEl);
    formInstanciaCobros = document.getElementById('formSimpleCobros');
    
    // Evento al abrir el modal
    modalEl.addEventListener('show.bs.modal', (event) => {
        const button = event.relatedTarget; 
        apiEndpointCobros = button.dataset.endpoint;
        const title = button.dataset.title;
        
        formInstanciaCobros.reset();
        document.getElementById('modalSimpleTitleCobros').textContent = title;
        document.getElementById('simpleEndpointCobros').value = apiEndpointCobros;
        editandoIdCobros = null;

        // Lógica campos extra
        const campoExtra = document.getElementById('campoExtraSimpleCobros');
        const labelExtra = document.getElementById('labelSimpleValorCobros');
        const inputExtra = document.getElementById('simpleValorCobros');
        
        if (apiEndpointCobros === 'condiciones-pago') {
            labelExtra.textContent = 'Días';
            inputExtra.type = 'number';
            inputExtra.step = '1';
            inputExtra.placeholder = '30';
            inputExtra.name = 'dias';
            campoExtra.style.display = 'block';
        } else {
            campoExtra.style.display = 'none';
            inputExtra.name = '';
        }
    });

    // Guardar
    document.getElementById('btnGuardarSimpleCobros').addEventListener('click', async () => {
        await guardarSimpleCobros();
    });
}

async function guardarSimpleCobros() {
    const form = document.getElementById('formSimpleCobros');
    const formData = new FormData(form);
    const data = Object.fromEntries(formData.entries());
    
    if (data.dias === '') delete data.dias;

    const url = editandoIdCobros ? `/api/admin/${apiEndpointCobros}/${editandoIdCobros}` : `/api/admin/${apiEndpointCobros}`;
    const method = editandoIdCobros ? 'PUT' : 'POST';

    try {
        const response = await fetch(url, { 
            method: method, 
            headers: { 'Content-Type': 'application/json' }, 
            body: JSON.stringify(data) 
        });
        
        if (response.ok) {
            modalInstanciaCobros.hide();
            cargarDatosCobros(apiEndpointCobros);
        } else {
            const result = await response.json();
            alert(`Error: ${result.error}`);
        }
    } catch (error) {
        console.error(error);
        alert('Error de red al guardar.');
    }
}

async function cargarDatosCobros(endpoint) {
    let tableId = '';
    let columnas = 3; // Valor base (ID, Nombre, Acciones)

    // Definir ID de tabla y número EXACTO de columnas según el HTML
    if(endpoint === 'formas-pago') { tableId = 'tbody-formas-pago'; columnas = 3; }
    if(endpoint === 'tipos-cliente') { tableId = 'tbody-tipos-cliente'; columnas = 3; }
    if(endpoint === 'condiciones-pago') { tableId = 'tbody-condiciones-pago'; columnas = 4; } // ID, Nombre, Días, Acciones

    const tbody = document.getElementById(tableId);
    if (!tbody) return;
    
    // Aquí estaba el error: el colspan debe ser dinámico
    tbody.innerHTML = `<tr><td colspan="${columnas}" class="text-center">Cargando...</td></tr>`;
    
    try {
        const response = await fetch(`/api/admin/${endpoint}`);
        const dataList = await response.json();
        tbody.innerHTML = '';
        
        if (dataList.length === 0) {
            tbody.innerHTML = `<tr><td colspan="${columnas}" class="text-center text-muted">No hay registros.</td></tr>`;
            return;
        }

        dataList.forEach(item => {
            let extraColumn = '';
            if (endpoint === 'condiciones-pago') {
                extraColumn = `<td>${item.dias || 0}</td>`;
            }

            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td>${item.id}</td>
                <td>${item.nombre}</td>
                ${extraColumn} 
                <td>
                    <button class="btn btn-sm btn-warning btn-editar-cobro" 
                            data-id="${item.id}" data-endpoint="${endpoint}">
                        Editar
                    </button>
                    <button class="btn btn-sm btn-danger btn-eliminar-cobro" 
                            data-id="${item.id}" data-endpoint="${endpoint}">
                        Eliminar
                    </button>
                </td>`;
            tbody.appendChild(tr);
        });

        // Asignar eventos
        tbody.querySelectorAll('.btn-editar-cobro').forEach(btn => {
            btn.addEventListener('click', () => abrirModalEditarCobros(btn.dataset.id, btn.dataset.endpoint));
        });
        tbody.querySelectorAll('.btn-eliminar-cobro').forEach(btn => {
            btn.addEventListener('click', () => eliminarSimpleCobros(btn.dataset.id, btn.dataset.endpoint));
        });

    } catch (error) {
        console.error(error);
        tbody.innerHTML = `<tr><td colspan="${columnas}" class="text-danger">Error al cargar datos.</td></tr>`;
    }
}

async function abrirModalEditarCobros(id, endpoint) {
    try {
        const response = await fetch(`/api/admin/${endpoint}/${id}`);
        if (!response.ok) return alert('Error al cargar datos.');
        const item = await response.json();

        apiEndpointCobros = endpoint;
        editandoIdCobros = id;
        
        const form = document.getElementById('formSimpleCobros');
        form.reset();
        
        document.getElementById('modalSimpleTitleCobros').textContent = `Editar ${endpoint.replace('-', ' ')}`;
        document.getElementById('simpleEndpointCobros').value = endpoint;
        document.getElementById('simpleIdCobros').value = item.id;
        document.getElementById('simpleNombreCobros').value = item.nombre;
        
        const campoExtra = document.getElementById('campoExtraSimpleCobros');
        const inputExtra = document.getElementById('simpleValorCobros');
        const labelExtra = document.getElementById('labelSimpleValorCobros');

        if (endpoint === 'condiciones-pago') {
            labelExtra.textContent = 'Días';
            inputExtra.type = 'number';
            inputExtra.name = 'dias';
            inputExtra.value = item.dias;
            campoExtra.style.display = 'block';
        } else {
            campoExtra.style.display = 'none';
            inputExtra.name = '';
        }
        
        modalInstanciaCobros.show();
    } catch (e) {
        console.error(e);
        alert("Error al abrir edición");
    }
}

async function eliminarSimpleCobros(id, endpoint) {
    if (!confirm('¿Estás seguro de eliminar este registro?')) return;
    try {
        const response = await fetch(`/api/admin/${endpoint}/${id}`, { method: 'DELETE' });
        if (response.ok) {
            cargarDatosCobros(endpoint);
        } else {
            alert('Error al eliminar');
        }
    } catch (error) {
        console.error(error);
        alert('Error de red.');
    }
}