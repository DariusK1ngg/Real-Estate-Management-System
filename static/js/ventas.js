/* static/js/ventas.js */

const formateador = new Intl.NumberFormat('es-PY');
let modalCliente = null;

// ==========================================
// INICIALIZACIÓN (DETECTAR PANTALLA)
// ==========================================
document.addEventListener('DOMContentLoaded', function() {
    // 1. Detectar Pantalla de Nueva Factura (Venta Directa - Contado)
    if (document.getElementById('formNuevaVenta')) {
        initNuevaVenta();
    }
    
    // 2. Detectar Pantalla de Carga de Deuda (Servicios al Contrato)
    if (document.getElementById('formCargaDeuda')) {
        initCargaDeuda();
    }
    
    // 3. Detectar Historial de Ventas/Servicios
    if (document.getElementById('tablaVentas')) {
        cargarHistorialServicios();
    }
    
    // 4. Detectar Pantalla de Definiciones (Pestañas Servicios y Clientes)
    if (document.getElementById('definiciones-tabs')) {
        cargarDefinicionesServicios();
        cargarClientesDefinicion();
        
        // Si existe el modal de clientes, cargamos sus selects
        if (document.getElementById('modalCliente')) {
            cargarParametrosCliente();
            
            // Listener para cascada Ciudad -> Barrio
            const selCiudad = document.getElementById('selectCiudad');
            if (selCiudad) {
                selCiudad.addEventListener('change', function(e) {
                    const id = e.target.value;
                    const selBarrio = document.getElementById('selectBarrio');
                    if(!id) {
                        selBarrio.innerHTML = '<option value="">-- Seleccione Ciudad --</option>';
                        selBarrio.disabled = true;
                        return;
                    }
                    selBarrio.disabled = false;
                    cargarSelect(`/api/admin/barrios?ciudad_id=${id}`, 'selectBarrio');
                });
            }
        }
    }
});

// ==========================================
// A. LÓGICA DE NUEVA FACTURA (CONTADO) 
// ==========================================
function initNuevaVenta() {
    if ($.fn.select2) {
        $('#selectCliente').select2({
            ajax: {
                url: '/api/admin/clientes/buscar',
                dataType: 'json',
                delay: 250,
                data: params => ({ q: params.term }),
                processResults: data => ({ results: data.map(c => ({ id: c.id, text: `${c.nombre} ${c.apellido} - ${c.documento}` })) })
            },
            placeholder: "Buscar cliente...",
            allowClear: true,
            width: '100%'
        });
    }

    const tabla = document.getElementById('tablaDetalles');
    
    if(tabla) {
        tabla.addEventListener('input', function(e) {
            if (e.target.classList.contains('cantidad') || e.target.classList.contains('precio')) {
                calcularFila(e.target.closest('tr'));
                calcularTotalGeneral();
            }
        });

        tabla.addEventListener('click', function(e) {
            if (e.target.closest('.btn-eliminar-fila')) {
                const tr = e.target.closest('tr');
                if (document.querySelectorAll('.fila-detalle').length > 1) {
                    tr.remove();
                    calcularTotalGeneral();
                } else {
                    Swal.fire({ icon: 'warning', title: 'Debe haber al menos un ítem.' });
                }
            }
        });
    }

    const btnAdd = document.getElementById('btnAgregarFila');
    if(btnAdd) {
        btnAdd.addEventListener('click', function() {
            const tbody = tabla.querySelector('tbody');
            const nuevaFila = tbody.querySelector('.fila-detalle').cloneNode(true);
            nuevaFila.querySelector('.descripcion').value = '';
            nuevaFila.querySelector('.cantidad').value = '1';
            nuevaFila.querySelector('.precio').value = ''; 
            nuevaFila.querySelector('.subtotal').value = '0';
            tbody.appendChild(nuevaFila);
            nuevaFila.querySelector('.descripcion').focus();
        });
    }

    const form = document.getElementById('formNuevaVenta');
    if(form) {
        form.addEventListener('submit', async function(e) {
            e.preventDefault();
            const clienteId = $('#selectCliente').val();
            if (!clienteId) return Swal.fire({ icon: 'warning', title: 'Seleccione un cliente' });

            const detalles = [];
            let error = false;

            document.querySelectorAll('.fila-detalle').forEach(tr => {
                const desc = tr.querySelector('.descripcion').value;
                const cant = parseFloat(tr.querySelector('.cantidad').value);
                const prec = parseMoney(tr.querySelector('.precio').value);
                
                if (!desc || cant <= 0) error = true;
                detalles.push({ descripcion: desc, cantidad: cant, precio_unitario: prec, subtotal: cant * prec });
            });

            if (error) return Swal.fire({ icon: 'error', title: 'Revise los detalles' });

            const data = {
                cliente_id: clienteId,
                fecha_venta: document.getElementsByName('fecha_venta')[0].value,
                detalles: detalles
            };

            try {
                const res = await fetch('/api/admin/ventas', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(data)
                });
                const result = await res.json();

                if (res.ok) {
                    Swal.fire({
                        title: '¡Éxito!',
                        text: `Factura N° ${result.numero} generada`,
                        icon: 'success',
                        confirmButtonText: 'Ver PDF'
                    }).then((r) => {
                        if (r.isConfirmed) window.open(`/admin/ventas/factura_pdf/${result.id}`, '_blank');
                        window.location.href = '/admin/ventas/movimientos';
                    });
                } else {
                    Swal.fire('Error', result.error, 'error');
                }
            } catch (error) { Swal.fire('Error', 'Error de conexión', 'error'); }
        });
    }
}

// ==========================================
// B. LÓGICA DE CARGA DE DEUDA (SERVICIOS) 
// ==========================================
function initCargaDeuda() {
    // 1. Cargar Catálogo de Servicios
    fetch('/api/admin/servicios')
        .then(r => r.json())
        .then(data => {
            const sel = document.getElementById('selectServicioCatalogo');
            if(sel) {
                data.forEach(s => {
                    const opt = document.createElement('option');
                    opt.value = s.id;
                    opt.text = s.nombre;
                    opt.dataset.precio = s.precio_defecto;
                    sel.appendChild(opt);
                });
            }
        });

    // 2. CONFIGURAR BUSCADOR NATIVO DE CLIENTES
    const inputBuscador = document.getElementById('cliente_buscador');
    const inputHidden = document.getElementById('cliente_id_hidden');
    const listaResultados = document.getElementById('lista_resultados_clientes');
    const selectContrato = document.getElementById('selectContrato');

    if(inputBuscador) {
        inputBuscador.addEventListener('input', function() {
            const query = this.value;

            if (query.length < 2) {
                listaResultados.style.display = 'none';
                listaResultados.innerHTML = '';
                inputHidden.value = '';
                if(selectContrato) {
                    selectContrato.innerHTML = '<option value="">-- Seleccione Cliente --</option>';
                    selectContrato.disabled = true;
                }
                return;
            }

            fetch(`/api/ventas/clientes/buscar_simple?q=${query}`)
                .then(r => r.json())
                .then(data => {
                    listaResultados.innerHTML = '';
                    if (data.length > 0) {
                        listaResultados.style.display = 'block';
                        data.forEach(cliente => {
                            const item = document.createElement('a');
                            item.className = 'list-group-item list-group-item-action';
                            item.style.cursor = 'pointer';
                            item.textContent = cliente.texto;

                            item.addEventListener('click', function() {
                                inputBuscador.value = cliente.texto.split('-')[0].trim();
                                inputHidden.value = cliente.id;
                                listaResultados.style.display = 'none';
                                
                                // Cargar contratos del cliente seleccionado
                                cargarContratosDelCliente(cliente.id);
                            });

                            listaResultados.appendChild(item);
                        });
                    } else {
                        listaResultados.style.display = 'none';
                    }
                });
        });

        // Cerrar al hacer click fuera
        document.addEventListener('click', function(e) {
            if (e.target !== inputBuscador && e.target !== listaResultados) {
                listaResultados.style.display = 'none';
            }
        });
    }

    // 3. Función interna para cargar contratos
    function cargarContratosDelCliente(cid) {
        const selCont = document.getElementById('selectContrato');
        if(!selCont) return;
        
        selCont.innerHTML = '<option>Cargando...</option>';
        selCont.disabled = true;
        
        fetch(`/api/admin/clientes/${cid}/contratos-activos`)
            .then(r => r.json())
            .then(data => {
                selCont.innerHTML = '<option value="">-- Seleccione Contrato --</option>';
                if(data.length === 0) {
                    selCont.innerHTML = '<option value="">Sin contratos activos</option>';
                } else {
                    data.forEach(c => {
                        const opt = document.createElement('option');
                        opt.value = c.id;
                        opt.textContent = `Contrato N° ${c.numero} (Lote: ${c.lote})`;
                        selCont.appendChild(opt);
                    });
                    selCont.disabled = false;
                }
            })
            .catch(e => {
                console.error(e);
                selCont.innerHTML = '<option value="">Error cargando</option>';
            });
    }

    // 4. Enviar Formulario de Deuda (EL BOTÓN CONFIRMAR)
    const formCarga = document.getElementById('formCargaDeuda');
    if(formCarga) {
        formCarga.addEventListener('submit', function(e) {
            e.preventDefault();
            
            const contratoId = document.getElementById('selectContrato').value;
            if(!contratoId) {
                if(typeof Swal !== 'undefined') Swal.fire('Atención', 'Debe seleccionar un contrato activo.', 'warning');
                else alert('Debe seleccionar un contrato activo.');
                return;
            }
            
            const fechaVencElement = document.getElementById('fechaVenc');
            if(!fechaVencElement) {
                alert("Error interno: No se encuentra el campo de fecha.");
                return;
            }

            const items = [];
            const rows = document.querySelectorAll('#tablaDetalles tbody tr');
            
            // *** CORRECCIÓN DEL ERROR DE BUCLE ***
            for (let i = 0; i < rows.length; i++) {
                const tr = rows[i];
                const inputMonto = tr.querySelector('.monto-input');
                
                // Si la fila no tiene el input (ej. fila vacía o de carga), la saltamos
                if (!inputMonto) continue; 

                const val = parseMoney(inputMonto.value);
                items.push({
                    servicio_id: tr.dataset.servicioId,
                    monto: val
                });
            }
            
            if(items.length === 0) {
                if(typeof Swal !== 'undefined') Swal.fire('Atención', 'Agregue al menos un servicio a la lista.', 'warning');
                else alert('Agregue al menos un servicio a la lista.');
                return;
            }

            const data = {
                contrato_id: contratoId,
                fecha_vencimiento: fechaVencElement.value,
                items: items
            };

            fetch('/api/admin/ventas', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            })
            .then(r => r.json())
            .then(res => {
                if(res.ok) {
                    if(typeof Swal !== 'undefined') {
                        Swal.fire('¡Éxito!', 'Servicios cargados correctamente.', 'success').then(() => {
                            window.location.href = '/admin/ventas/movimientos';
                        });
                    } else {
                        alert('Servicios cargados correctamente.');
                        window.location.href = '/admin/ventas/movimientos';
                    }
                } else {
                    if(typeof Swal !== 'undefined') Swal.fire('Error', res.error || "Error al guardar", 'error');
                    else alert("Error: " + res.error);
                }
            })
            .catch(e => {
                if(typeof Swal !== 'undefined') Swal.fire('Error', 'Error de conexión', 'error');
                else alert('Error de conexión');
            });
        });
    }
}

// ==========================================
// FUNCIONES GLOBALES (HELPER) ACCESIBLES DESDE HTML
// ==========================================

// Agregar Item desde Catálogo
window.agregarItemDesdeCatalogo = function() {
    const sel = document.getElementById('selectServicioCatalogo');
    const id = sel.value;
    if(!id) {
        if(typeof Swal !== 'undefined') Swal.fire('Atención', "Seleccione un servicio del catálogo", 'info');
        else alert("Seleccione un servicio");
        return;
    }
    
    const opt = sel.options[sel.selectedIndex];
    const nombre = opt.text;
    const precioRaw = opt.dataset.precio || 0;
    const precioFmt = formatMoney(precioRaw);
    
    const tbody = document.querySelector('#tablaDetalles tbody');
    const tr = document.createElement('tr');
    tr.dataset.servicioId = id;
    
    tr.innerHTML = `
        <td class="align-middle">${nombre}</td>
        <td>
            <div class="input-group input-group-sm">
                <span class="input-group-text">Gs.</span>
                <input type="text" class="form-control input-money monto-input" value="${precioFmt}" oninput="window.calcTotal()">
            </div>
        </td>
        <td class="text-center align-middle">
            <button type="button" class="btn btn-danger btn-sm" onclick="this.closest('tr').remove(); window.calcTotal()">
                <i class="fas fa-trash"></i>
            </button>
        </td>
    `;
    tbody.appendChild(tr);
    window.calcTotal();
};

window.calcTotal = function() {
    let total = 0;
    document.querySelectorAll('.monto-input').forEach(i => total += parseMoney(i.value));
    const totalEl = document.getElementById('totalVenta');
    if(totalEl) totalEl.innerText = formatMoney(total);
};

// ==========================================
// C. HISTORIAL Y ELIMINACIÓN
// ==========================================
async function cargarHistorialServicios() {
    const tableId = '#tablaVentas';
    const tbody = document.querySelector(tableId + ' tbody');
    if (!tbody) return;

    if ($.fn.DataTable.isDataTable(tableId)) {
        $(tableId).DataTable().destroy();
    }

    tbody.innerHTML = '<tr><td colspan="7" class="text-center">Cargando datos...</td></tr>';

    try {
        const res = await fetch('/api/admin/ventas');
        const datos = await res.json();
        
        tbody.innerHTML = '';

        if (datos.length > 0) {
            datos.forEach(item => {
                const tr = document.createElement('tr');
                let badge = item.estado === 'pagada' ? 
                    '<span class="badge bg-success">COBRADO</span>' : 
                    '<span class="badge bg-warning text-dark">PENDIENTE</span>';
                
                let btnEliminar = item.estado === 'pendiente' ? 
                    `<button class="btn btn-sm btn-outline-danger" onclick="eliminarCarga(${item.id})"><i class="fas fa-trash"></i></button>` : 
                    '';

                let monto = typeof formatMoney === 'function' ? formatMoney(item.total) : item.total;

                tr.innerHTML = `
                    <td>${item.fecha}</td>
                    <td>${item.numero}</td>
                    <td><strong>${item.cliente_nombre}</strong><br><small class="text-muted">${item.concepto}</small></td>
                    <td>${item.cliente_documento || '-'}</td>
                    <td class="text-end">Gs. ${monto}</td>
                    <td>${badge}</td>
                    <td class="text-center">${btnEliminar}</td>
                `;
                tbody.appendChild(tr);
            });
        }

        $(tableId).DataTable({
            language: { 
                url: '//cdn.datatables.net/plug-ins/1.13.6/i18n/es-ES.json',
                emptyTable: "No hay registros de ventas/servicios cargados."
            },
            order: [[0, 'desc']],
            responsive: true,
            columnDefs: [ { targets: 6, orderable: false } ]
        });

    } catch (e) { 
        console.error(e); 
        tbody.innerHTML = '<tr><td colspan="7" class="text-center text-danger">Error de conexión al cargar historial.</td></tr>';
    }
}

window.eliminarCarga = async function(id) {
    const result = await Swal.fire({
        title: '¿Eliminar?',
        text: "Se borrará esta deuda de la cuenta del cliente.",
        icon: 'warning',
        showCancelButton: true,
        confirmButtonColor: '#d33',
        confirmButtonText: 'Sí, eliminar'
    });

    if (result.isConfirmed) {
        try {
            const res = await fetch(`/api/admin/ventas/${id}`, { method: 'DELETE' });
            if(res.ok) {
                Swal.fire('Eliminado', 'El servicio ha sido eliminado.', 'success');
                cargarHistorialServicios();
            } else {
                Swal.fire('Error', 'No se pudo eliminar', 'error');
            }
        } catch(e) { Swal.fire('Error', 'Fallo de red', 'error'); }
    }
};

// ==========================================
// D. GESTIÓN DE CLIENTES
// ==========================================
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
    } catch (e) { console.error(e); }
}

window.abrirModalCliente = function(cliente = null) {
    const el = document.getElementById('modalCliente');
    if (!modalCliente) modalCliente = new bootstrap.Modal(el);
    
    const form = document.getElementById('formCliente');
    form.reset();
    document.getElementById('cliente_id').value = '';
    document.getElementById('selectBarrio').disabled = true;
    document.getElementById('modalClienteTitle').textContent = 'Nuevo Cliente';

    if (cliente) {
        document.getElementById('modalClienteTitle').textContent = 'Editar Cliente';
        document.getElementById('cliente_id').value = cliente.id;
        
        form.querySelector('[name="documento"]').value = cliente.documento;
        form.querySelector('[name="nombre"]').value = cliente.nombre;
        form.querySelector('[name="apellido"]').value = cliente.apellido;
        form.querySelector('[name="telefono"]').value = cliente.telefono || '';
        form.querySelector('[name="email"]').value = cliente.email || '';
        form.querySelector('[name="direccion"]').value = cliente.direccion || '';
        form.querySelector('[name="estado"]').value = cliente.estado;

        if(cliente.tipo_documento_id) document.getElementById('selectTipoDoc').value = cliente.tipo_documento_id;
        if(cliente.profesion_id) document.getElementById('selectProfesion').value = cliente.profesion_id;
        if(cliente.tipo_cliente_id) document.getElementById('selectTipoCliente').value = cliente.tipo_cliente_id;
        
        if(cliente.ciudad_id) {
            document.getElementById('selectCiudad').value = cliente.ciudad_id;
            document.getElementById('selectBarrio').disabled = false;
            cargarSelect(`/api/admin/barrios?ciudad_id=${cliente.ciudad_id}`, 'selectBarrio').then(() => {
                if(cliente.barrio_id) document.getElementById('selectBarrio').value = cliente.barrio_id;
            });
        }
    }
    
    modalCliente.show();
};

window.guardarCliente = async function() {
    const form = document.getElementById('formCliente');
    const data = Object.fromEntries(new FormData(form));
    const id = document.getElementById('cliente_id').value;
    
    if(!data.documento || !data.nombre || !data.apellido) return Swal.fire({icon:'warning', title:'Campos obligatorios faltantes'});

    const url = id ? `/api/admin/clientes/${id}` : '/api/admin/clientes';
    const method = id ? 'PUT' : 'POST';

    try {
        const res = await fetch(url, {
            method: method,
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(data)
        });
        const result = await res.json();
        
        if(res.ok) {
            Swal.fire({icon:'success', title:'Cliente guardado'});
            modalCliente.hide();
            cargarClientesDefinicion();
        } else {
            Swal.fire({icon:'error', title: result.error || 'Error al guardar'});
        }
    } catch(e) { Swal.fire({icon:'error', title:'Error de red'}); }
};

window.cargarClientesDefinicion = async function() {
    const tbody = document.getElementById('tabla-clientes');
    if(!tbody) return;
    
    tbody.innerHTML = '<tr><td colspan="6" class="text-center">Cargando...</td></tr>';
    const res = await fetch('/api/admin/clientes/buscar?q=');
    const data = await res.json();
    tbody.innerHTML = '';
    
    data.forEach(c => {
        const clienteStr = JSON.stringify(c).replace(/"/g, '&quot;');
        tbody.innerHTML += `
            <tr>
                <td>${c.nombre} ${c.apellido}</td>
                <td>${c.tipo_documento} ${c.documento}</td>
                <td>${c.telefono || '-'}</td>
                <td>${c.ciudad_nombre || '-'}</td>
                <td><span class="badge bg-${c.estado === 'activo' ? 'success' : 'secondary'}">${c.estado}</span></td>
                <td class="text-end">
                    <button class="btn btn-sm btn-warning" onclick="abrirModalCliente(${clienteStr})"><i class="fas fa-edit"></i></button>
                    <button class="btn btn-sm btn-danger" onclick="eliminarCliente(${c.id})"><i class="fas fa-trash"></i></button>
                </td>
            </tr>`;
    });
};

window.eliminarCliente = async function(id) {
    const result = await Swal.fire({title:"¿Eliminar cliente?", icon:'warning', showCancelButton:true});
    if(!result.isConfirmed) return;
    
    try {
        const res = await fetch(`/api/admin/clientes/${id}`, { method: 'DELETE' });
        if(res.ok) {
            Swal.fire({icon:'success', title:'Eliminado'});
            cargarClientesDefinicion();
        } else { Swal.fire({icon:'error', title:'Error'}); }
    } catch(e) { Swal.fire({icon:'error', title:'Error'}); }
};

// ==========================================
// E. DEFINICIONES DE SERVICIOS
// ==========================================
async function cargarDefinicionesServicios() {
    const tbody = document.getElementById('tabla-servicios-definicion');
    if(!tbody) return;
    const res = await fetch('/api/admin/servicios');
    const data = await res.json();
    tbody.innerHTML = '';
    data.forEach(s => {
        tbody.innerHTML += `
            <tr>
                <td>${s.nombre}</td>
                <td>Gs. ${formatMoney(s.precio_defecto)}</td>
                <td><button class="btn btn-sm btn-danger" onclick="borrarServicio(${s.id})"><i class="fas fa-trash"></i></button></td>
            </tr>`;
    });
}

window.guardarServicio = async function() {
    const nombre = document.getElementById('nuevo-servicio-nombre').value;
    const precio = parseMoney(document.getElementById('nuevo-servicio-precio').value);
    if(!nombre) return Swal.fire({icon:'warning', title:'Nombre requerido'});
    await fetch('/api/admin/servicios', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({nombre, precio_defecto: precio})
    });
    document.getElementById('nuevo-servicio-nombre').value = '';
    document.getElementById('nuevo-servicio-precio').value = '';
    cargarDefinicionesServicios();
    Swal.fire({icon:'success', title:'Servicio guardado'});
};

window.borrarServicio = async function(id) {
    if(!confirm("¿Borrar?")) return;
    await fetch(`/api/admin/servicios/${id}`, {method: 'DELETE'});
    cargarDefinicionesServicios();
};

// ==========================================
// UTILIDADES (HELPER)
// ==========================================
function parseMoney(str) {
    if(!str) return 0;
    return parseFloat(str.toString().replace(/\./g, '').replace(',', '.'));
}

function formatMoney(amount) {
    return new Intl.NumberFormat('es-PY').format(amount);
}

function calcularFila(tr) {
    const cant = parseFloat(tr.querySelector('.cantidad').value) || 0;
    const prec = parseMoney(tr.querySelector('.precio').value);
    const sub = cant * prec;
    tr.querySelector('.subtotal').value = formatMoney(sub);
    tr.dataset.subtotal = sub;
}

function calcularTotalGeneral() {
    let total = 0;
    document.querySelectorAll('.fila-detalle').forEach(tr => { total += parseFloat(tr.dataset.subtotal) || 0; });
    const el = document.getElementById('totalVenta');
    if(el) el.textContent = formatMoney(total);
}