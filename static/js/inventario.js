document.addEventListener('DOMContentLoaded', () => {
    const searchInput = document.getElementById('search-fraccionamiento');
    if (searchInput) {
        searchInput.addEventListener('input', () => buscarFraccionamientos(searchInput.value));
        buscarFraccionamientos('');
    }

    // Si estamos en la página de detalle
    if (document.getElementById('form-fraccionamiento-detalle')) {
        cargarDatosFraccionamiento();
    }
});

// --- FUNCIONES DE FORMATO ---
function formatNumber(value) {
    // Elimina todo lo que no sea un dígito
    const numberString = value.replace(/\D/g, '');
    // Formatea con separadores de miles para Paraguay
    return new Intl.NumberFormat('es-PY').format(numberString) || '';
}

function unformatNumber(value) {
    // Elimina los separadores de miles para obtener el número puro
    return value.replace(/\./g, '');
}
// --- FIN DE FUNCIONES DE FORMATO ---


async function buscarFraccionamientos(query) {
    const response = await fetch(`/api/admin/fraccionamientos?q=${query}`);
    const fraccionamientos = await response.json();
    const tbody = document.getElementById('tbody-fraccionamientos');
    tbody.innerHTML = '';
    fraccionamientos.forEach(f => {
        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td>${f.nombre}</td>
            <td>${f.descripcion}</td>
            <td>
                <a href="/admin/inventario/fraccionamientos/${f.id}" class="btn btn-sm btn-info">Editar / Ver Lotes</a>
            </td>
        `;
        tbody.appendChild(tr);
    });
}

// --- Lógica para la página de detalle ---

let loteSeleccionadoId = null;
let condicionesPago = [];

// ===== FUNCIÓN MODIFICADA =====
async function cargarDatosFraccionamiento() {
    const fraccionamientoId = document.getElementById('fraccionamiento_id').value;
    const response = await fetch(`/api/admin/fraccionamientos/${fraccionamientoId}/detalle`);
    const data = await response.json();

    document.getElementById('nombre').value = data.nombre;
    document.getElementById('descripcion').value = data.descripcion || '';
    document.getElementById('comision_propietario').value = data.comision_propietario;
    document.getElementById('comision_inmobiliaria').value = data.comision_inmobiliaria;

    const lotesList = document.getElementById('lotes-list');
    lotesList.innerHTML = '';
    data.lotes.forEach(lote => {
        const div = document.createElement('div');
        div.className = 'lote-item';
        div.dataset.loteId = lote.id;
        div.innerHTML = `
            <div class="lote-item-info">
                <span><b>Lote:</b> ${lote.numero_lote} - <b>Manzana:</b> ${lote.manzana}</span>
                <span class="lote-item-estado estado-${lote.estado}">${lote.estado.toUpperCase()}</span>
            </div>
        `;
        div.addEventListener('click', () => seleccionarLote(lote.id));
        lotesList.appendChild(div);
    });

    const condResponse = await fetch('/api/admin/condiciones-pago');
    condicionesPago = await condResponse.json();
    const selectCondicion = document.getElementById('condicion_pago_id');
    selectCondicion.innerHTML = '<option value="">Seleccione...</option>';
    condicionesPago.forEach(c => {
        selectCondicion.innerHTML += `<option value="${c.id}">${c.nombre}</option>`;
    });

    const precioUnitarioInput = document.getElementById('precio_unitario');
    precioUnitarioInput.addEventListener('input', (e) => {
        const cursorPosition = e.target.selectionStart;
        const originalLength = e.target.value.length;
        e.target.value = formatNumber(e.target.value);
        const newLength = e.target.value.length;
        e.target.setSelectionRange(cursorPosition + (newLength - originalLength), cursorPosition + (newLength - originalLength));
        calcularPrecioTotal();
    });

    document.getElementById('cantidad_cuotas').addEventListener('input', calcularPrecioTotal);
}

function seleccionarLote(loteId) {
    loteSeleccionadoId = loteId;
    document.querySelectorAll('.lote-item').forEach(item => item.classList.remove('selected'));
    document.querySelector(`.lote-item[data-lote-id="${loteId}"]`).classList.add('selected');
    
    document.getElementById('precios-lote-section').style.display = 'block';
    cargarListaPrecios(loteId);
}

async function cargarListaPrecios(loteId) {
    const response = await fetch(`/api/admin/lotes/${loteId}/precios`);
    const precios = await response.json();
    const tbody = document.getElementById('tbody-precios');
    tbody.innerHTML = '';
    precios.forEach(p => {
        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td>${p.condicion_pago_nombre}</td>
            <td>${p.cantidad_cuotas}</td>
            <td>${p.precio_cuota.toLocaleString('es-PY')}</td>
            <td>${p.precio_total.toLocaleString('es-PY')}</td>
            <td><button class="btn btn-sm btn-danger" onclick="eliminarPrecio(${p.id})">X</button></td>
        `;
        tbody.appendChild(tr);
    });
}

function calcularPrecioTotal() {
    const cantidad = parseFloat(document.getElementById('cantidad_cuotas').value) || 0;
    const precioUnitario = parseFloat(unformatNumber(document.getElementById('precio_unitario').value)) || 0;
    const total = cantidad * precioUnitario;
    
    const totalInput = document.getElementById('precio_total');
    if (total > 0) {
        totalInput.value = total.toLocaleString('es-PY');
    } else {
        totalInput.value = '';
    }
}

async function guardarDetalleFraccionamiento() {
    const fraccionamientoId = document.getElementById('fraccionamiento_id').value;
    const data = {
        nombre: document.getElementById('nombre').value,
        descripcion: document.getElementById('descripcion').value,
        comision_propietario: document.getElementById('comision_propietario').value,
        comision_inmobiliaria: document.getElementById('comision_inmobiliaria').value,
    };

    const response = await fetch(`/api/admin/fraccionamientos/${fraccionamientoId}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data)
    });

    if (response.ok) {
        alert('Datos guardados correctamente.');
    } else {
        alert('Error al guardar los datos.');
    }
}
// ===== FIN DE LA MODIFICACIÓN =====

async function agregarPrecio() {
    if (!loteSeleccionadoId) {
        alert('Por favor, seleccione un lote primero.');
        return;
    }

    const data = {
        lote_id: loteSeleccionadoId,
        condicion_pago_id: document.getElementById('condicion_pago_id').value,
        cantidad_cuotas: document.getElementById('cantidad_cuotas').value,
        precio_cuota: unformatNumber(document.getElementById('precio_unitario').value),
        precio_total: unformatNumber(document.getElementById('precio_total').value),
    };

    if (!data.precio_cuota || !data.precio_total || !data.cantidad_cuotas || !data.condicion_pago_id) {
        alert('Por favor, complete todos los campos del plan de pago.');
        return;
    }

    const response = await fetch(`/api/admin/lotes/${loteSeleccionadoId}/precios`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data)
    });

    if (response.ok) {
        cargarListaPrecios(loteSeleccionadoId);
        document.getElementById('form-precios').reset();
    } else {
        alert('Error al agregar el precio.');
    }
}

async function eliminarPrecio(precioId) {
    if (!confirm('¿Está seguro de que desea eliminar este plan de pago?')) return;

    const response = await fetch(`/api/admin/lista-precios/${precioId}`, {
        method: 'DELETE'
    });

    if (response.ok) {
        cargarListaPrecios(loteSeleccionadoId);
    } else {
        alert('Error al eliminar el precio.');
    }
}