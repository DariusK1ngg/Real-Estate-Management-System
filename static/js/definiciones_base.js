document.addEventListener('DOMContentLoaded', function() {
    // Carga inicial de datos
    cargarDatosBase('impuestos');
    cargarDatosBase('tipos-comprobante');
    cargarDatosBase('profesiones');
    cargarDatosBase('tipos-documentos');
    
    cargarParametros();
    cargarCiudades();
    cargarCotizaciones();

    setupModalBase();
    setupModalsCustom();
});

// --- LÓGICA GENÉRICA (MODELOS SIMPLES) ---
let editandoIdBase = null;
let apiEndpointBase = '';
let modalInstanciaBase = null;

function setupModalBase() {
    const modalEl = document.getElementById('modalSimple');
    if (!modalEl) return;
    modalInstanciaBase = new bootstrap.Modal(modalEl);
    
    modalEl.addEventListener('show.bs.modal', (event) => {
        const button = event.relatedTarget; 
        apiEndpointBase = button.dataset.endpoint;
        document.getElementById('formSimple').reset();
        document.getElementById('modalSimpleTitle').textContent = button.dataset.title;
        document.getElementById('simpleEndpoint').value = apiEndpointBase;
        editandoIdBase = null;
        
        const campoExtra = document.getElementById('campoExtraSimple');
        if (apiEndpointBase === 'impuestos') {
            document.getElementById('labelSimpleValor').textContent = 'Porcentaje (%)';
            campoExtra.style.display = 'block';
        } else {
            campoExtra.style.display = 'none';
        }
    });

    document.getElementById('btnGuardarSimple').addEventListener('click', async () => {
        const nombre = document.getElementById('simpleNombre').value;
        const data = { nombre: nombre };
        if (apiEndpointBase === 'impuestos') {
            data.porcentaje = document.getElementById('simpleValor').value;
        }
        
        const url = editandoIdBase ? `/api/admin/${apiEndpointBase}/${editandoIdBase}` : `/api/admin/${apiEndpointBase}`;
        const method = editandoIdBase ? 'PUT' : 'POST';
        
        const res = await fetch(url, { method, headers: {'Content-Type': 'application/json'}, body: JSON.stringify(data) });
        if (res.ok) {
            modalInstanciaBase.hide();
            cargarDatosBase(apiEndpointBase);
        } else { alert('Error al guardar'); }
    });
}

async function cargarDatosBase(endpoint) {
    let tableId = `tbody-${endpoint}`;
    if (endpoint === 'tipos-documentos') tableId = 'tbody-tipos-documentos'; // Ajuste por nombre plural
    const tbody = document.getElementById(tableId);
    if (!tbody) return;
    
    const res = await fetch(`/api/admin/${endpoint}`);
    const list = await res.json();
    tbody.innerHTML = '';
    
    list.forEach(item => {
        let extra = endpoint === 'impuestos' ? `<td>${item.porcentaje}%</td>` : '';
        const itemStr = JSON.stringify(item).replace(/"/g, '&quot;');
        tbody.innerHTML += `<tr><td>${item.id}</td><td>${item.nombre}</td>${extra}<td>
            <button class="btn btn-sm btn-warning" onclick="editarSimple('${endpoint}', ${itemStr})">Editar</button>
            <button class="btn btn-sm btn-danger" onclick="eliminarSimple('${endpoint}', ${item.id})">Eliminar</button>
        </td></tr>`;
    });
}

window.editarSimple = function(endpoint, item) {
    apiEndpointBase = endpoint;
    editandoIdBase = item.id;
    document.getElementById('simpleId').value = item.id;
    document.getElementById('simpleNombre').value = item.nombre;
    document.getElementById('simpleEndpoint').value = endpoint;
    document.getElementById('modalSimpleTitle').textContent = 'Editar';
    
    if (endpoint === 'impuestos') {
        document.getElementById('simpleValor').value = item.porcentaje;
        document.getElementById('campoExtraSimple').style.display = 'block';
    } else {
        document.getElementById('campoExtraSimple').style.display = 'none';
    }
    modalInstanciaBase.show();
};

window.eliminarSimple = async function(endpoint, id) {
    if(!confirm('¿Eliminar?')) return;
    await fetch(`/api/admin/${endpoint}/${id}`, { method: 'DELETE' });
    cargarDatosBase(endpoint);
};

// --- LÓGICA ESPECÍFICA (PARAMETROS, UBICACIONES, COTIZACIONES) ---

function setupModalsCustom() {
    // Parámetros
    document.getElementById('formParametro').addEventListener('submit', async (e) => {
        e.preventDefault();
        const id = document.getElementById('paramId').value;
        const data = {
            clave: document.getElementById('paramClave').value,
            valor: document.getElementById('paramValor').value,
            descripcion: document.getElementById('paramDesc').value
        };
        const url = id ? `/api/admin/parametros/${id}` : '/api/admin/parametros';
        const method = id ? 'PUT' : 'POST';
        await fetch(url, { method, headers: {'Content-Type': 'application/json'}, body: JSON.stringify(data) });
        cerrarModal('modalParametro');
        cargarParametros();
    });

    // Ciudades
    document.getElementById('formCiudad').addEventListener('submit', async (e) => {
        e.preventDefault();
        const id = document.getElementById('ciudadId').value;
        const data = { nombre: document.getElementById('ciudadNombre').value };
        const url = id ? `/api/admin/ciudades/${id}` : '/api/admin/ciudades';
        const method = id ? 'PUT' : 'POST';
        await fetch(url, { method, headers: {'Content-Type': 'application/json'}, body: JSON.stringify(data) });
        cerrarModal('modalCiudad');
        cargarCiudades();
    });

    // Barrios
    document.getElementById('formBarrio').addEventListener('submit', async (e) => {
        e.preventDefault();
        const id = document.getElementById('barrioId').value;
        const data = { 
            nombre: document.getElementById('barrioNombre').value,
            ciudad_id: document.getElementById('barrioCiudad').value
        };
        const url = id ? `/api/admin/barrios/${id}` : '/api/admin/barrios';
        const method = id ? 'PUT' : 'POST';
        await fetch(url, { method, headers: {'Content-Type': 'application/json'}, body: JSON.stringify(data) });
        cerrarModal('modalBarrio');
        const ciudadFilter = document.getElementById('filtro-ciudad-barrio').value;
        cargarBarrios(ciudadFilter);
    });

    // Cotizaciones
    document.getElementById('formCotizacion').addEventListener('submit', async (e) => {
        e.preventDefault();
        const id = document.getElementById('cotId').value;
        const data = {
            fecha: document.getElementById('cotFecha').value,
            moneda_origen: document.getElementById('cotOrigen').value,
            moneda_destino: document.getElementById('cotDestino').value,
            compra: document.getElementById('cotCompra').value,
            venta: document.getElementById('cotVenta').value
        };
        const url = id ? `/api/admin/cotizaciones/${id}` : '/api/admin/cotizaciones';
        const method = id ? 'PUT' : 'POST';
        await fetch(url, { method, headers: {'Content-Type': 'application/json'}, body: JSON.stringify(data) });
        cerrarModal('modalCotizacion');
        cargarCotizaciones();
    });
}

// --- FUNCIONES DE CARGA ---

async function cargarParametros() {
    const res = await fetch('/api/admin/parametros');
    const list = await res.json();
    const tbody = document.getElementById('tbody-parametros');
    tbody.innerHTML = '';
    list.forEach(p => {
        const pStr = JSON.stringify(p).replace(/"/g, '&quot;');
        tbody.innerHTML += `<tr><td>${p.clave}</td><td>${p.valor}</td><td>${p.descripcion || ''}</td><td>
            <button class="btn btn-sm btn-warning" onclick='editarParametro(${pStr})'>Editar</button>
            <button class="btn btn-sm btn-danger" onclick="eliminarParametro(${p.id})">X</button>
        </td></tr>`;
    });
}

async function cargarCiudades() {
    const res = await fetch('/api/admin/ciudades');
    const list = await res.json();
    const tbody = document.getElementById('tbody-ciudades');
    const selectFiltro = document.getElementById('filtro-ciudad-barrio');
    
    tbody.innerHTML = '';
    selectFiltro.innerHTML = '<option value="">-- Filtrar por Ciudad --</option>';
    
    list.forEach(c => {
        const cStr = JSON.stringify(c).replace(/"/g, '&quot;');
        tbody.innerHTML += `<tr><td>${c.nombre}</td><td>
            <button class="btn btn-sm btn-warning" onclick='editarCiudad(${cStr})'>Editar</button>
            <button class="btn btn-sm btn-danger" onclick="eliminarCiudad(${c.id})">X</button>
        </td></tr>`;
        selectFiltro.innerHTML += `<option value="${c.id}">${c.nombre}</option>`;
    });
    
    // Cargar barrios si hay ciudad seleccionada
    cargarBarrios(selectFiltro.value);
}

window.cargarBarrios = async function(ciudadId = null) {
    if (!ciudadId) ciudadId = document.getElementById('filtro-ciudad-barrio').value;
    const url = ciudadId ? `/api/admin/barrios?ciudad_id=${ciudadId}` : '/api/admin/barrios';
    const res = await fetch(url);
    const list = await res.json();
    const tbody = document.getElementById('tbody-barrios');
    tbody.innerHTML = '';
    list.forEach(b => {
        const bStr = JSON.stringify(b).replace(/"/g, '&quot;');
        tbody.innerHTML += `<tr><td>${b.nombre}</td><td>
            <button class="btn btn-sm btn-warning" onclick='editarBarrio(${bStr})'>Editar</button>
            <button class="btn btn-sm btn-danger" onclick="eliminarBarrio(${b.id})">X</button>
        </td></tr>`;
    });
};

async function cargarCotizaciones() {
    const res = await fetch('/api/admin/cotizaciones');
    const list = await res.json();
    const tbody = document.getElementById('tbody-cotizaciones');
    tbody.innerHTML = '';
    list.forEach(c => {
        const cStr = JSON.stringify(c).replace(/"/g, '&quot;');
        tbody.innerHTML += `<tr><td>${c.fecha}</td><td>${c.moneda_origen}</td><td>${c.moneda_destino}</td><td>${c.compra}</td><td>${c.venta}</td><td>
            <button class="btn btn-sm btn-warning" onclick='editarCotizacion(${cStr})'>Editar</button>
            <button class="btn btn-sm btn-danger" onclick="eliminarCotizacion(${c.id})">X</button>
        </td></tr>`;
    });
}

// --- FUNCIONES DE APERTURA DE MODALES Y EDICIÓN ---

window.abrirModalParametro = () => {
    document.getElementById('formParametro').reset();
    document.getElementById('paramId').value = '';
    abrirModal('modalParametro');
};
window.editarParametro = (p) => {
    document.getElementById('paramId').value = p.id;
    document.getElementById('paramClave').value = p.clave;
    document.getElementById('paramValor').value = p.valor;
    document.getElementById('paramDesc').value = p.descripcion;
    abrirModal('modalParametro');
};
window.eliminarParametro = async (id) => {
    if(!confirm('Eliminar?')) return;
    await fetch(`/api/admin/parametros/${id}`, {method: 'DELETE'});
    cargarParametros();
};

window.abrirModalCiudad = () => {
    document.getElementById('formCiudad').reset();
    document.getElementById('ciudadId').value = '';
    abrirModal('modalCiudad');
};
window.editarCiudad = (c) => {
    document.getElementById('ciudadId').value = c.id;
    document.getElementById('ciudadNombre').value = c.nombre;
    abrirModal('modalCiudad');
};
window.eliminarCiudad = async (id) => {
    if(!confirm('Eliminar?')) return;
    await fetch(`/api/admin/ciudades/${id}`, {method: 'DELETE'});
    cargarCiudades();
};

window.abrirModalBarrio = async () => {
    document.getElementById('formBarrio').reset();
    document.getElementById('barrioId').value = '';
    // Cargar ciudades en el select del modal
    const res = await fetch('/api/admin/ciudades');
    const ciudades = await res.json();
    const select = document.getElementById('barrioCiudad');
    select.innerHTML = '';
    ciudades.forEach(c => select.innerHTML += `<option value="${c.id}">${c.nombre}</option>`);
    abrirModal('modalBarrio');
};
window.editarBarrio = async (b) => {
    await window.abrirModalBarrio(); // Para cargar el select
    document.getElementById('barrioId').value = b.id;
    document.getElementById('barrioNombre').value = b.nombre;
    document.getElementById('barrioCiudad').value = b.ciudad_id;
    abrirModal('modalBarrio');
};
window.eliminarBarrio = async (id) => {
    if(!confirm('Eliminar?')) return;
    await fetch(`/api/admin/barrios/${id}`, {method: 'DELETE'});
    cargarBarrios();
};

window.abrirModalCotizacion = () => {
    document.getElementById('formCotizacion').reset();
    document.getElementById('cotId').value = '';
    document.getElementById('cotFecha').valueAsDate = new Date();
    abrirModal('modalCotizacion');
};
window.editarCotizacion = (c) => {
    document.getElementById('cotId').value = c.id;
    document.getElementById('cotFecha').value = c.fecha;
    document.getElementById('cotOrigen').value = c.moneda_origen;
    document.getElementById('cotDestino').value = c.moneda_destino;
    document.getElementById('cotCompra').value = c.compra;
    document.getElementById('cotVenta').value = c.venta;
    abrirModal('modalCotizacion');
};
window.eliminarCotizacion = async (id) => {
    if(!confirm('Eliminar?')) return;
    await fetch(`/api/admin/cotizaciones/${id}`, {method: 'DELETE'});
    cargarCotizaciones();
};

// Función auxiliar local para abrir modales (si no está en main.js)
function abrirModal(id) {
    const el = document.getElementById(id);
    const modal = new bootstrap.Modal(el);
    modal.show();
}
window.cerrarModal = (id) => {
    const el = document.getElementById(id);
    const modal = bootstrap.Modal.getInstance(el);
    if (modal) modal.hide();
};