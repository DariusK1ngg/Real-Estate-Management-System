document.addEventListener('DOMContentLoaded', function() {

    // =================================================================
    // LÓGICA COMÚN: PESTAÑAS (TABS)
    // =================================================================
    const tabLinks = document.querySelectorAll('.tab-link');
    const tabContents = document.querySelectorAll('.tab-content');

    // Esta parte solo se ejecuta si hay pestañas en la página
    if (tabLinks.length > 0) {
        tabLinks.forEach(link => {
            link.addEventListener('click', () => {
                const tabId = link.dataset.tab;

                // Ocultar todos los contenidos
                tabContents.forEach(content => {
                    content.classList.remove('active');
                });
                // Quitar clase activa de todos los links
                tabLinks.forEach(l => {
                    l.classList.remove('active');
                });

                // Mostrar el contenido seleccionado
                const activeTab = document.getElementById(tabId);
                if (activeTab) {
                    activeTab.classList.add('active');
                }
                // Añadir clase activa al link
                link.classList.add('active');
            });
        });
        
        // Activar la primera pestaña por defecto (si existe)
        if (tabLinks.length > 0 && !document.querySelector('.tab-link.active')) {
             tabLinks[0].click();
        }
    }

    // Función global de API (para simplificar)
    const apiFetch = async (url, method = 'GET', body = null) => {
        try {
            const options = {
                method: method,
                headers: { 'Content-Type': 'application/json' },
            };
            if (body) {
                options.body = JSON.stringify(body);
            }
            
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


    // =================================================================
    // LÓGICA PARA: /templates/gastos/definiciones.html
    // =================================================================
    
    // --- A: GESTIÓN DE CATEGORÍAS ---
    const formCategoria = document.getElementById('form-categoria-gasto');
    const tablaCategoriasBody = document.querySelector('#tabla-categorias-gasto tbody');
    const btnCancelarCategoria = document.getElementById('btn-cancelar-categoria');
    const categoriaIdField = document.getElementById('categoria-id');

    // *** INICIO DE PROTECCIÓN ***
    if (formCategoria && tablaCategoriasBody) {
        
        // --- Cargar tabla de categorías ---
        const cargarCategorias = async () => {
            try {
                const categorias = await apiFetch('/api/admin/categorias-gasto');
                tablaCategoriasBody.innerHTML = ''; // Limpiar tabla
                
                categorias.forEach(cat => {
                    const tr = document.createElement('tr');
                    tr.innerHTML = `
                        <td>${cat.id}</td>
                        <td>${cat.nombre}</td>
                        <td>${cat.descripcion}</td>
                        <td class="actions">
                            <button class="btn-edit" data-id="${cat.id}">Editar</button>
                            <button class="btn-delete" data-id="${cat.id}">Eliminar</button>
                        </td>
                    `;
                    tablaCategoriasBody.appendChild(tr);
                });
            } catch (error) {
                tablaCategoriasBody.innerHTML = `<tr><td colspan="4">Error al cargar categorías</td></tr>`;
            }
        };

        // --- Limpiar formulario de categoría ---
        const resetFormCategoria = () => {
            formCategoria.reset();
            categoriaIdField.value = '';
            formCategoria.querySelector('button[type="submit"]').textContent = 'Guardar Categoría';
        };

        // --- Guardar (Crear/Actualizar) Categoría ---
        formCategoria.addEventListener('submit', async (e) => {
            e.preventDefault();
            
            const formData = new FormData(formCategoria);
            const data = Object.fromEntries(formData.entries());
            const categoriaId = categoriaIdField.value;
            
            const url = categoriaId ? `/api/admin/categorias-gasto/${categoriaId}` : '/api/admin/categorias-gasto';
            const method = categoriaId ? 'PUT' : 'POST';

            try {
                await apiFetch(url, method, data);
                alert('Categoría guardada exitosamente');
                resetFormCategoria();
                cargarCategorias(); // Recargar la tabla
            } catch (error) {
                // El error ya se muestra en apiFetch
            }
        });

        // --- Botón Cancelar ---
        if (btnCancelarCategoria) {
            btnCancelarCategoria.addEventListener('click', resetFormCategoria);
        }

        // --- Delegación de eventos para Editar y Eliminar ---
        tablaCategoriasBody.addEventListener('click', async (e) => {
            const target = e.target;

            // --- Editar Categoría ---
            if (target.classList.contains('btn-edit')) {
                const id = target.dataset.id;
                try {
                    const cat = await apiFetch(`/api/admin/categorias-gasto/${id}`);
                    
                    categoriaIdField.value = cat.id;
                    document.getElementById('categoria-nombre').value = cat.nombre;
                    document.getElementById('categoria-descripcion').value = cat.descripcion;
                    formCategoria.querySelector('button[type="submit"]').textContent = 'Actualizar Categoría';
                    
                    window.scrollTo(0, 0); // Subir al formulario

                } catch (error) {
                    alert('Error: No se pudo cargar la categoría para editar');
                }
            }
            
            // --- Eliminar Categoría ---
            if (target.classList.contains('btn-delete')) {
                const id = target.dataset.id;
                if (!confirm(`¿Estás seguro de eliminar la categoría ID ${id}?`)) return;

                try {
                    await apiFetch(`/api/admin/categorias-gasto/${id}`, 'DELETE');
                    alert('Categoría eliminada');
                    cargarCategorias(); // Recargar la tabla
                } catch (error) {
                     // El error ya se muestra en apiFetch
                }
            }
        });

        // Carga inicial de categorías
        cargarCategorias();
    } // <-- FIN DEL BLOQUE PROTEGIDO PARA CATEGORÍAS

    // --- B: GESTIÓN DE PROVEEDORES ---
    const formProveedor = document.getElementById('form-proveedor');
    const tablaProveedoresBody = document.querySelector('#tabla-proveedores tbody');
    const btnCancelarProveedor = document.getElementById('btn-cancelar-proveedor');
    const proveedorIdField = document.getElementById('proveedor-id');

    // *** INICIO DE PROTECCIÓN ***
    if (formProveedor && tablaProveedoresBody) {
        
        const cargarProveedores = async () => {
             try {
                const proveedores = await apiFetch('/api/admin/proveedores');
                tablaProveedoresBody.innerHTML = '';
                
                proveedores.forEach(p => {
                    const tr = document.createElement('tr');
                    tr.innerHTML = `
                        <td>${p.id}</td>
                        <td>${p.razon_social}</td>
                        <td>${p.ruc}</td>
                        <td>${p.telefono}</td>
                        <td class="actions">
                            <button class="btn-edit" data-id="${p.id}">Editar</button>
                            <button class="btn-delete" data-id="${p.id}">Eliminar</button>
                        </td>
                    `;
                    tablaProveedoresBody.appendChild(tr);
                });
             } catch (error) {
                 tablaProveedoresBody.innerHTML = `<tr><td colspan="5">Error al cargar proveedores</td></tr>`;
             }
        };

        const resetFormProveedor = () => {
            formProveedor.reset();
            proveedorIdField.value = '';
            formProveedor.querySelector('button[type="submit"]').textContent = 'Guardar Proveedor';
        };

        formProveedor.addEventListener('submit', async (e) => {
            e.preventDefault();
            const formData = new FormData(formProveedor);
            const data = Object.fromEntries(formData.entries());
            const id = proveedorIdField.value;
            
            const url = id ? `/api/admin/proveedores/${id}` : '/api/admin/proveedores';
            const method = id ? 'PUT' : 'POST';

            try {
                await apiFetch(url, method, data);
                alert('Proveedor guardado exitosamente');
                resetFormProveedor();
                cargarProveedores();
            } catch (error) {
                // error manejado por apiFetch
            }
        });

        if (btnCancelarProveedor) {
            btnCancelarProveedor.addEventListener('click', resetFormProveedor);
        }

        tablaProveedoresBody.addEventListener('click', async (e) => {
            const target = e.target;
            
            if (target.classList.contains('btn-edit')) {
                const id = target.dataset.id;
                try {
                    const p = await apiFetch(`/api/admin/proveedores/${id}`);
                    proveedorIdField.value = p.id;
                    document.getElementById('proveedor-razon-social').value = p.razon_social;
                    document.getElementById('proveedor-ruc').value = p.ruc;
                    document.getElementById('proveedor-telefono').value = p.telefono;
                    document.getElementById('proveedor-direccion').value = p.direccion;
                    formProveedor.querySelector('button[type="submit"]').textContent = 'Actualizar Proveedor';
                    window.scrollTo(0, 0);
                } catch (error) {
                    alert('Error: No se pudo cargar el proveedor');
                }
            }
            
            if (target.classList.contains('btn-delete')) {
                const id = target.dataset.id;
                if (!confirm(`¿Seguro de eliminar al proveedor ID ${id}?`)) return;
                try {
                    await apiFetch(`/api/admin/proveedores/${id}`, 'DELETE');
                    alert('Proveedor eliminado');
                    cargarProveedores();
                } catch (error) {
                    // error manejado por apiFetch
                }
            }
        });

        // Carga inicial
        cargarProveedores();
    } // <-- FIN DEL BLOQUE PROTEGIDO PARA PROVEEDORES


    // =================================================================
    // LÓGICA PARA: /templates/gastos/movimientos.html
    // =================================================================
    const formGasto = document.getElementById('form-gasto');
    const selectCategoriaGasto = document.getElementById('gasto-categoria');
    const selectProveedorGasto = document.getElementById('gasto-proveedor');
    const tablaGastosBody = document.querySelector('#tabla-gastos tbody');
    const btnCancelarGasto = document.getElementById('btn-cancelar-gasto');
    const montoInput = document.getElementById('gasto-monto'); // Seleccionamos el input de monto

    // *** INICIO DE PROTECCIÓN ***
    if (formGasto) {
        if (montoInput) {
            montoInput.addEventListener('input', function(e) {
                // 1. Obtener el valor limpio (solo números)
                let value = e.target.value.replace(/[^0-9]/g, '');

                // 2. Si está vacío, no hacer nada (permite borrar)
                if (value === '') {
                    e.target.value = '';
                    return;
                }

                // 3. Convertir a número
                let number = parseInt(value, 10);
                
                // 4. Formatear con puntos (usamos 'es-ES' para el formato 1.000.000)
                let formattedValue = new Intl.NumberFormat('es-ES').format(number);

                // 5. Asignar el valor formateado de nuevo al input
                e.target.value = formattedValue;
            });
        }
        // --- Cargar Select de Categorías ---
        const cargarSelectCategorias = async () => {
            if (!selectCategoriaGasto) return;
            try {
                const categorias = await apiFetch('/api/admin/categorias-gasto');
                selectCategoriaGasto.innerHTML = '<option value="">Seleccione una categoría</option>';
                categorias.forEach(cat => {
                    const option = document.createElement('option');
                    option.value = cat.id;
                    option.textContent = cat.nombre;
                    selectCategoriaGasto.appendChild(option);
                });
            } catch (error) {
                selectCategoriaGasto.innerHTML = '<option value="">Error al cargar</option>';
            }
        };

        // --- Cargar Select de Proveedores ---
        const cargarSelectProveedores = async () => {
            if (!selectProveedorGasto) return;
            try {
                const proveedores = await apiFetch('/api/admin/proveedores');
                selectProveedorGasto.innerHTML = '<option value="">Seleccione un proveedor</option>';
                proveedores.forEach(p => {
                    const option = document.createElement('option');
                    option.value = p.id;
                    option.textContent = p.razon_social;
                    selectProveedorGasto.appendChild(option);
                });
            } catch (error) {
                selectProveedorGasto.innerHTML = '<option value="">Error al cargar</ar>';
            }
        };
        
        // --- Cargar Tabla de Gastos ---
        const cargarTablaGastos = async () => {
            if (!tablaGastosBody) return;
            try {
                const gastos = await apiFetch('/api/admin/gastos');
                tablaGastosBody.innerHTML = '';
                
                gastos.forEach(g => {
                    const tr = document.createElement('tr');
                    // Formateamos el monto que viene de la API
                    const montoFormateado = new Intl.NumberFormat('es-ES').format(g.monto);
                    tr.innerHTML = `
                        <td>${g.id}</td>
                        <td>${new Date(g.fecha_factura + 'T00:00:00').toLocaleDateString()}</td>
                        <td>${g.proveedor_nombre}</td>
                        <td>${g.categoria_nombre}</td>
                        <td>${g.detalle}</td>
                        <td>${g.numero_factura}</td>
                        <td>${montoFormateado} Gs.</td> <td><span class="badge estado-${g.estado}">${g.estado}</span></td>
                        <td class="actions">
                            ${g.estado !== 'anulado' ? `<button class="btn-delete" data-id="${g.id}">Anular</button>` : ''}
                        </td>
                    `;
                    tablaGastosBody.appendChild(tr);
                });
            } catch (error) {
                tablaGastosBody.innerHTML = `<tr><td colspan="9">Error al cargar gastos</td></tr>`;
            }
        };

        // --- Registrar Gasto (MODIFICADO) ---
        formGasto.addEventListener('submit', async (e) => {
            e.preventDefault();
            
            const formData = new FormData(formGasto);
            const data = Object.fromEntries(formData.entries());
            const montoLimpio = data.monto.replace(/[^0-9]/g, '');
            const payload = {
                proveedor_id: data.proveedor_id,
                categoria_gasto_id: data.categoria_gasto_id,
                detalle: data.detalle,
                numero_factura: data.numero_factura,
                fecha_factura: data.fecha_factura,
                monto: parseFloat(montoLimpio) || 0,
                estado: 'pendiente'
            };

            try {
                await apiFetch('/api/admin/gastos', 'POST', payload);
                alert('Gasto registrado exitosamente');
                formGasto.reset();
                cargarTablaGastos(); // Recargar la tabla
            } catch (error) {
            }
        });

        // --- Anular Gasto (desde la tabla) ---
        if (tablaGastosBody) {
            tablaGastosBody.addEventListener('click', async (e) => {
                if (e.target.classList.contains('btn-delete')) {
                    const id = e.target.dataset.id;
                    if (!confirm(`¿Está seguro de ANULAR el gasto ID ${id}? Esta acción no se puede deshacer.`)) return;

                    try {
                        await apiFetch(`/api/admin/gastos/${id}`, 'DELETE');
                        alert('Gasto anulado correctamente');
                        cargarTablaGastos(); // Recargar la tabla
                    } catch (error) {
                        // error manejado por apiFetch
                    }
                }
            });
        }
        
        // --- Botón Cancelar (Formulario) ---
        if (btnCancelarGasto) {
            btnCancelarGasto.addEventListener('click', () => {
                formGasto.reset();
            });
        }

        // --- Cargas iniciales en Movimientos ---
        cargarSelectCategorias();
        cargarSelectProveedores();
        cargarTablaGastos();
    }
});