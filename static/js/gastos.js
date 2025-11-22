document.addEventListener('DOMContentLoaded', function() {

    // =================================================================
    // LÓGICA COMÚN: PESTAÑAS (TABS)
    // =================================================================
    const tabLinks = document.querySelectorAll('.tab-link');
    const tabContents = document.querySelectorAll('.tab-content');

    if (tabLinks.length > 0) {
        tabLinks.forEach(link => {
            link.addEventListener('click', () => {
                const tabId = link.dataset.tab;
                tabContents.forEach(content => content.classList.remove('active'));
                tabLinks.forEach(l => l.classList.remove('active'));
                const activeTab = document.getElementById(tabId);
                if (activeTab) activeTab.classList.add('active');
                link.classList.add('active');
            });
        });
        if (tabLinks.length > 0 && !document.querySelector('.tab-link.active')) {
             tabLinks[0].click();
        }
    }

    const apiFetch = async (url, method = 'GET', body = null) => {
        try {
            const options = {
                method: method,
                headers: { 'Content-Type': 'application/json' },
            };
            if (body) options.body = JSON.stringify(body);
            
            const response = await fetch(url, options);
            
            if (!response.ok) {
                const errData = await response.json();
                throw new Error(errData.error || `Error ${response.status}`);
            }
            if (response.status === 204 || method === 'DELETE') {
                return { message: "Operación exitosa" };
            }
            return await response.json();

        } catch (error) {
            console.error(`Error en API ${method} ${url}:`, error);
            alert(`Error: ${error.message}`);
            throw error;
        }
    };

    // --- A: DEFINICIONES (CATEGORÍAS Y PROVEEDORES) ---
    const formCategoria = document.getElementById('form-categoria-gasto');
    const tablaCategoriasBody = document.querySelector('#tabla-categorias-gasto tbody');
    const formProveedor = document.getElementById('form-proveedor');
    const tablaProveedoresBody = document.querySelector('#tabla-proveedores tbody');

    if (formCategoria && tablaCategoriasBody) {
        const cargarCategorias = async () => {
            try {
                const categorias = await apiFetch('/api/admin/categorias-gasto');
                tablaCategoriasBody.innerHTML = '';
                categorias.forEach(cat => {
                    tablaCategoriasBody.innerHTML += `
                        <tr><td>${cat.id}</td><td>${cat.nombre}</td><td>${cat.descripcion}</td>
                        <td class="actions"><button class="btn-delete" data-id="${cat.id}">Eliminar</button></td></tr>`;
                });
            } catch (error) {}
        };
        formCategoria.addEventListener('submit', async (e) => {
            e.preventDefault();
            const data = Object.fromEntries(new FormData(formCategoria).entries());
            await apiFetch('/api/admin/categorias-gasto', 'POST', data);
            alert('Categoría guardada'); formCategoria.reset(); cargarCategorias();
        });
        tablaCategoriasBody.addEventListener('click', async (e) => {
            if (e.target.classList.contains('btn-delete')) {
                if (confirm('Eliminar?')) {
                    await apiFetch(`/api/admin/categorias-gasto/${e.target.dataset.id}`, 'DELETE');
                    cargarCategorias();
                }
            }
        });
        cargarCategorias();
    }

    if (formProveedor && tablaProveedoresBody) {
        const cargarProveedores = async () => {
             try {
                const proveedores = await apiFetch('/api/admin/proveedores');
                tablaProveedoresBody.innerHTML = '';
                proveedores.forEach(p => {
                    tablaProveedoresBody.innerHTML += `
                        <tr><td>${p.id}</td><td>${p.razon_social}</td><td>${p.ruc}</td><td>${p.telefono}</td>
                        <td class="actions"><button class="btn-delete" data-id="${p.id}">Eliminar</button></td></tr>`;
                });
             } catch (error) {}
        };
        formProveedor.addEventListener('submit', async (e) => {
            e.preventDefault();
            const data = Object.fromEntries(new FormData(formProveedor).entries());
            await apiFetch('/api/admin/proveedores', 'POST', data);
            alert('Proveedor guardado'); formProveedor.reset(); cargarProveedores();
        });
        tablaProveedoresBody.addEventListener('click', async (e) => {
            if (e.target.classList.contains('btn-delete')) {
                if (confirm('Eliminar?')) {
                    await apiFetch(`/api/admin/proveedores/${e.target.dataset.id}`, 'DELETE');
                    cargarProveedores();
                }
            }
        });
        cargarProveedores();
    }

    // =================================================================
    // LÓGICA PARA: /templates/gastos/movimientos.html (PAGOS Y DATATABLES)
    // =================================================================
    const formGasto = document.getElementById('form-gasto');
    const selectCategoriaGasto = document.getElementById('gasto-categoria');
    const selectProveedorGasto = document.getElementById('gasto-proveedor');
    const tablaGastosBody = document.querySelector('#tabla-gastos tbody');
    const montoInput = document.getElementById('gasto-monto');

    if (formGasto) {
        if (montoInput) {
            montoInput.addEventListener('input', function(e) {
                let value = e.target.value.replace(/[^0-9]/g, '');
                if (value === '') { e.target.value = ''; return; }
                e.target.value = new Intl.NumberFormat('es-ES').format(parseInt(value, 10));
            });
        }

        const cargarSelects = async () => {
            if (!selectCategoriaGasto) return;
            const cats = await apiFetch('/api/admin/categorias-gasto');
            selectCategoriaGasto.innerHTML = '<option value="">Seleccione...</option>';
            cats.forEach(c => selectCategoriaGasto.innerHTML += `<option value="${c.id}">${c.nombre}</option>`);

            const provs = await apiFetch('/api/admin/proveedores');
            selectProveedorGasto.innerHTML = '<option value="">Seleccione...</option>';
            provs.forEach(p => selectProveedorGasto.innerHTML += `<option value="${p.id}">${p.razon_social}</option>`);
        };

        const cargarTablaGastos = async () => {
            if (!tablaGastosBody) return;
            
            // Destruir DataTable si existe para recargar
            if ($.fn.DataTable.isDataTable('#tabla-gastos')) {
                $('#tabla-gastos').DataTable().destroy();
            }

            try {
                const gastos = await apiFetch('/api/admin/gastos');
                tablaGastosBody.innerHTML = '';
                
                gastos.forEach(g => {
                    const tr = document.createElement('tr');
                    const montoFormateado = new Intl.NumberFormat('es-ES').format(g.monto);
                    
                    // Botón Pagar condicional
                    const btnPagar = g.estado === 'pendiente' 
                        ? `<button class="btn btn-sm btn-success me-1" onclick="abrirPagarGasto(${g.id}, ${g.monto}, '${g.proveedor_nombre}')"><i class="fas fa-money-bill-wave"></i> Pagar</button>` 
                        : '';
                    
                    const btnAnular = g.estado !== 'anulado' && g.estado !== 'pagado'
                        ? `<button class="btn-delete" data-id="${g.id}"><i class="fas fa-ban"></i> Anular</button>`
                        : '';

                    tr.innerHTML = `
                        <td>${g.id}</td>
                        <td>${new Date(g.fecha_factura + 'T00:00:00').toLocaleDateString()}</td>
                        <td>${g.proveedor_nombre}</td>
                        <td>${g.categoria_nombre}</td>
                        <td>${g.detalle}</td>
                        <td>${g.numero_factura || '-'}</td>
                        <td>${montoFormateado} Gs.</td> 
                        <td><span class="badge estado-${g.estado}">${g.estado.toUpperCase()}</span></td>
                        <td class="actions">
                            ${btnPagar}
                            ${btnAnular}
                        </td>
                    `;
                    tablaGastosBody.appendChild(tr);
                });

                // Inicializar DataTables con los nuevos datos
                $('#tabla-gastos').DataTable({
                    language: { url: "//cdn.datatables.net/plug-ins/1.13.6/i18n/es-ES.json" },
                    order: [[0, 'desc']]
                });

            } catch (error) {
                tablaGastosBody.innerHTML = `<tr><td colspan="9">Error al cargar gastos</td></tr>`;
            }
        };

        formGasto.addEventListener('submit', async (e) => {
            e.preventDefault();
            const formData = new FormData(formGasto);
            const data = Object.fromEntries(formData.entries());
            data.monto = parseFloat(data.monto.replace(/[^0-9]/g, '')) || 0;
            
            await apiFetch('/api/admin/gastos', 'POST', data);
            alert('Gasto registrado'); formGasto.reset(); cargarTablaGastos();
        });

        tablaGastosBody.addEventListener('click', async (e) => {
            if (e.target.closest('.btn-delete')) {
                const id = e.target.closest('.btn-delete').dataset.id;
                if (!confirm(`¿ANULAR el gasto ID ${id}?`)) return;
                await apiFetch(`/api/admin/gastos/${id}`, 'DELETE');
                cargarTablaGastos();
            }
        });

        // INICIALIZACIÓN
        cargarSelects();
        cargarTablaGastos();
    }
});

// --- FUNCIONES GLOBALES PARA EL MODAL DE PAGO ---
let modalPagarInstance = null;

window.abrirPagarGasto = async function(id, monto, proveedor) {
    const el = document.getElementById('modalPagarGasto');
    if (!el) return;
    
    modalPagarInstance = new bootstrap.Modal(el);
    
    document.getElementById('pago_gasto_id').value = id;
    document.getElementById('spanMontoPagar').textContent = new Intl.NumberFormat('es-PY').format(monto);
    document.getElementById('spanProveedorPagar').textContent = proveedor;
    document.getElementById('pago_fecha').valueAsDate = new Date();
    
    // Cargar cuentas si es necesario
    const selectCuenta = document.getElementById('selectCuentaPago');
    if (selectCuenta.options.length === 0) {
        try {
            const res = await fetch('/api/admin/cuentas-bancarias');
            const cuentas = await res.json();
            selectCuenta.innerHTML = '<option value="">Seleccione Cuenta...</option>';
            cuentas.forEach(c => {
                selectCuenta.innerHTML += `<option value="${c.id}">${c.entidad_nombre} - ${c.numero_cuenta} (${c.moneda})</option>`;
            });
        } catch(e) {}
    }
    
    modalPagarInstance.show();
};

window.toggleInfoPago = function() {
    const metodo = document.getElementById('selectMetodoPago').value;
    document.getElementById('divBanco').style.display = (metodo === 'banco') ? 'block' : 'none';
};

// Listener para el formulario de pago (fuera del DOMContentLoaded para ser accesible)
document.addEventListener('submit', async function(e) {
    if (e.target && e.target.id === 'formPagarGasto') {
        e.preventDefault();
        const gastoId = document.getElementById('pago_gasto_id').value;
        const data = Object.fromEntries(new FormData(e.target));
        
        try {
            const response = await fetch(`/api/admin/gastos/${gastoId}/pagar`, {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(data)
            });
            const result = await response.json();
            
            if (response.ok) {
                alert(result.message);
                if(modalPagarInstance) modalPagarInstance.hide();
                // Recargar página para actualizar tabla y estado
                location.reload(); 
            } else {
                alert("Error: " + result.error);
            }
        } catch (err) {
            alert("Error de red");
        }
    }
});