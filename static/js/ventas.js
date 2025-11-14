// static/js/ventas.js

document.addEventListener('DOMContentLoaded', function() {
    cargarVentas();
    cargarVendedores();
    cargarLotesParaVenta();
    
    // Inicializar Select2 con manejo de errores
    try {
        setupSelect2();
    } catch (e) {
        console.warn("Select2 no se pudo inicializar (puede que ya esté listo o falte la librería):", e);
    }
});

// Configuración de Select2 (Buscador avanzado)
function setupSelect2() {
    // Cliente
    $('#cliente_id').select2({
        dropdownParent: $('#modalFactura'), // Clave para que funcione en el modal
        theme: 'bootstrap-5',
        placeholder: "Buscar cliente...",
        minimumInputLength: 2,
        ajax: {
            url: '/api/admin/clientes/buscar',
            dataType: 'json',
            delay: 250,
            data: params => ({ q: params.term }),
            processResults: data => ({
                results: data.map(c => ({
                    id: c.id,
                    text: `${c.nombre_completo} (${c.documento})`
                }))
            }),
            cache: true
        }
    });

    // Vendedor
    $('#vendedor_id').select2({
        dropdownParent: $('#modalFactura'),
        theme: 'bootstrap-5',
        placeholder: "Seleccionar vendedor"
    });

    // Ítem (Lote/Servicio)
    $('#item-lote').select2({
        dropdownParent: $('#modalFactura'),
        theme: 'bootstrap-5',
        placeholder: "Seleccionar ítem..."
    });
}

// --- VARIABLES GLOBALES DEL MODAL ---
let modalFacturaInstance = null;
let detalleItems = []; 

// --- FUNCIONES GLOBALES (Window) ---

// 1. ABRIR MODAL (Con Fix de Pantalla Oscura)
window.abrirModalFactura = function() {
    const modalEl = document.getElementById('modalFactura');
    if (!modalEl) return;

    // [FIX CRÍTICO] Mover el modal al final del body para evitar conflictos de z-index
    document.body.appendChild(modalEl);

    if (!modalFacturaInstance) {
        modalFacturaInstance = new bootstrap.Modal(modalEl, {
            backdrop: 'static',
            keyboard: false
        });
    }
    
    // Resetear formulario
    document.getElementById('formFactura').reset();
    
    // Resetear Select2
    $('#cliente_id').val(null).trigger('change');
    $('#vendedor_id').val(null).trigger('change');
    $('#item-lote').val(null).trigger('change');
    
    // Limpiar detalles
    detalleItems = [];
    renderizarDetalle();
    
    // Fecha por defecto: Hoy
    document.getElementById('fecha_venta').valueAsDate = new Date();
    
    // Ocultar campo manual
    const descManual = document.getElementById('item-descripcion-manual');
    if(descManual) descManual.style.display = 'none';

    // Mostrar modal
    modalFacturaInstance.show();
};

// 2. CERRAR MODAL
window.cerrarModalFactura = function() {
    if (modalFacturaInstance) {
        modalFacturaInstance.hide();
    } else {
        // Fallback
        const el = document.getElementById('modalFactura');
        const instance = bootstrap.Modal.getInstance(el);
        if (instance) instance.hide();
    }
};

// 3. AGREGAR ÍTEM
window.agregarItemDetalle = function() {
    const select = document.getElementById('item-lote');
    const cantidadInput = document.getElementById('item-cantidad');
    const precioInput = document.getElementById('item-precio');
    const descInput = document.getElementById('item-descripcion-manual');

    // Validar selección (Select2 a veces tiene value "" visualmente pero es válido)
    // Verificamos si es el placeholder real
    if ($(select).val() === null) {
        alert("Seleccione un ítem válido.");
        return;
    }

    // Obtener datos del option seleccionado
    const option = select.options[select.selectedIndex];
    let descripcion = option.dataset.texto || "Ítem";
    const loteId = option.value || null; // Si es "" es servicio (null para la API)

    // Si es servicio manual, usar el input de texto
    if (!loteId && descInput.style.display !== 'none' && descInput.value.trim() !== "") {
        descripcion = descInput.value.trim();
    }

    const cantidad = parseInt(cantidadInput.value);
    const precio = parseFloat(precioInput.value);

    if (isNaN(cantidad) || cantidad <= 0) {
        alert("Cantidad inválida.");
        return;
    }
    if (isNaN(precio) || precio < 0) {
        alert("Precio inválido.");
        return;
    }

    // Agregar al array
    detalleItems.push({
        lote_id: loteId,
        descripcion: descripcion,
        cantidad: cantidad,
        precio_unitario: precio,
        subtotal: cantidad * precio
    });

    renderizarDetalle();
    
    // Limpiar inputs de detalle para el siguiente
    $('#item-lote').val(null).trigger('change');
    cantidadInput.value = 1;
    precioInput.value = "";
    if(descInput) {
        descInput.value = "";
        descInput.style.display = "none";
    }
};

// 4. ELIMINAR ÍTEM
window.eliminarItem = function(index) {
    detalleItems.splice(index, 1);
    renderizarDetalle();
};

// 5. GUARDAR FACTURA
window.guardarFactura = async function() {
    const form = document.getElementById('formFactura');
    const formData = new FormData(form);
    
    const data = {
        cliente_id: formData.get('cliente_id'),
        vendedor_id: formData.get('vendedor_id') || null,
        fecha_venta: formData.get('fecha_venta'),
        detalles: detalleItems
    };

    if (!data.cliente_id) { alert("Falta seleccionar el Cliente."); return; }
    if (!data.fecha_venta) { alert("Falta la Fecha."); return; }
    if (data.detalles.length === 0) { alert("Debe agregar al menos un ítem al detalle."); return; }

    try {
        const response = await fetch('/api/admin/ventas', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });
        const result = await response.json();
        
        if (response.ok) {
            alert(`Factura N° ${result.numero_factura} guardada correctamente.`);
            cerrarModalFactura();
            cargarVentas();
        } else {
            alert('Error al guardar: ' + (result.error || 'Desconocido'));
        }
    } catch (error) {
        console.error(error);
        alert("Error de red al guardar la factura.");
    }
};

// --- EVENTOS SELECT2 (Lógica interna) ---
$(document).on('select2:select', '#item-lote', function(e) {
    const data = e.params.data;
    const element = $(data.element);
    const precio = element.data('precio');
    
    // Auto-rellenar precio
    if (precio) {
        document.getElementById('item-precio').value = precio;
    }
    
    // Mostrar input manual si es servicio
    const descInput = document.getElementById('item-descripcion-manual');
    if (element.val() === "") { // Es el servicio genérico
        if(descInput) {
            descInput.style.display = 'block';
            descInput.value = element.data('texto') || "";
            descInput.focus();
        }
    } else {
        if(descInput) descInput.style.display = 'none';
    }
});

// --- FUNCIONES AUXILIARES ---

function renderizarDetalle() {
    const tbody = document.getElementById('tbodyDetalleFactura');
    tbody.innerHTML = '';
    let total = 0;

    detalleItems.forEach((item, index) => {
        total += item.subtotal;
        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td>${item.descripcion}</td>
            <td class="text-center">${item.cantidad}</td>
            <td class="text-end">${item.precio_unitario.toLocaleString('es-PY')}</td>
            <td class="text-end">${item.subtotal.toLocaleString('es-PY')}</td>
            <td class="col-accion">
                <button type="button" class="btn btn-sm btn-outline-danger border-0" onclick="eliminarItem(${index})">
                    <i class="fas fa-times"></i>
                </button>
            </td>
        `;
        tbody.appendChild(tr);
    });

    document.getElementById('factura-total').textContent = total.toLocaleString('es-PY') + " Gs.";
}

window.cargarVentas = async function() {
    const tbody = document.getElementById('tbodyVentas');
    if(!tbody) return;
    tbody.innerHTML = '<tr><td colspan="7" class="text-center">Cargando...</td></tr>';
    
    try {
        const res = await fetch('/api/admin/ventas');
        const data = await res.json();
        
        tbody.innerHTML = '';
        if (data.length === 0) {
            tbody.innerHTML = '<tr><td colspan="7" class="text-center text-muted py-4">No hay ventas registradas.</td></tr>';
            return;
        }

        data.forEach(v => {
            // Formato fecha seguro
            let fecha = v.fecha_venta;
            try { fecha = new Date(v.fecha_venta + 'T00:00:00').toLocaleDateString('es-ES'); } catch(e){}

            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td><span class="fw-bold text-primary">${v.numero_factura}</span></td>
                <td>${fecha}</td>
                <td>${v.cliente_nombre}</td>
                <td>${v.vendedor_nombre}</td>
                <td class="fw-bold">Gs. ${v.total.toLocaleString('es-PY')}</td>
                <td>
                    <span class="badge ${v.estado === 'emitida' ? 'bg-success' : 'bg-danger'}">
                        ${v.estado.toUpperCase()}
                    </span>
                </td>
                <td>
                    <button class="btn btn-sm btn-info text-white" onclick="window.open('/admin/ventas/factura_pdf/${v.id}', '_blank')" title="Imprimir">
                        <i class="fas fa-print"></i>
                    </button>
                    ${v.estado === 'emitida' ? 
                        `<button class="btn btn-sm btn-danger" onclick="anularVenta(${v.id})" title="Anular">
                            <i class="fas fa-ban"></i>
                        </button>` : ''}
                </td>
            `;
            tbody.appendChild(tr);
        });
    } catch (error) {
        console.error(error);
        tbody.innerHTML = '<tr><td colspan="7" class="text-center text-danger">Error al cargar ventas.</td></tr>';
    }
};

async function cargarLotesParaVenta() {
    const select = document.getElementById('item-lote');
    if(!select) return;
    
    try {
        const res = await fetch('/api/admin/lotes-disponibles');
        const lotes = await res.json();
        
        select.innerHTML = '<option value="">Seleccione un ítem...</option>';
        // Opción especial
        select.innerHTML += `<option value="" data-precio="0" data-texto="Servicio Administrativo">Servicio Administrativo (Manual)</option>`;
        
        lotes.forEach(l => {
            // Guardamos precio y texto en data attributes para leerlos luego con jQuery/JS
            select.innerHTML += `<option value="${l.id}" data-precio="${l.precio}" data-texto="${l.texto}">${l.texto}</option>`;
        });
    } catch (e) { console.error(e); }
}

async function cargarVendedores() {
    const select = document.getElementById('vendedor_id');
    if(!select) return;
    try {
        const res = await fetch('/api/admin/vendedores');
        const data = await res.json();
        select.innerHTML = '<option value="">-- Sin Vendedor --</option>';
        data.forEach(v => {
            select.innerHTML += `<option value="${v.id}">${v.nombre_completo}</option>`;
        });
    } catch(e) { console.error(e); }
}

window.anularVenta = async function(id) {
    if(!confirm("¿Anular esta venta? Se revertirá el estado del lote.")) return;
    try {
        const res = await fetch(`/api/admin/ventas/${id}`, { method: 'DELETE' });
        const data = await res.json();
        if(res.ok) {
            alert(data.message);
            cargarVentas();
        } else {
            alert("Error: " + data.error);
        }
    } catch(e) { alert("Error de red"); }
};