document.addEventListener('DOMContentLoaded', function() {
    // --- 1. CONFIGURACIÓN INICIAL ---
    const hoy = new Date();
    const inputDesde = document.getElementById('fechaDesde');
    const inputHasta = document.getElementById('fechaHasta');
    
    if(inputDesde) inputDesde.valueAsDate = hoy;
    if(inputHasta) inputHasta.valueAsDate = hoy;

    const formArqueo = document.getElementById('formArqueo');
    if (formArqueo) {
        formArqueo.addEventListener('submit', generarReporteArqueo);
    }

    // --- 2. LOGICA DEL BUSCADOR DE CLIENTES (TIPO NUEVO CONTRATO) ---
    const inputBusqueda = document.getElementById('cliente_buscador_reporte');
    const listaResultados = document.getElementById('lista_resultados_cliente_reporte');
    const inputId = document.getElementById('cliente_id_reporte');
    const btnGenerar = document.getElementById('btnGenerarExtracto');

    if (inputBusqueda) {
        inputBusqueda.addEventListener('input', function() {
            const query = this.value;

            // Si está vacío o es muy corto, ocultamos la lista
            if (query.length < 2) {
                listaResultados.style.display = 'none';
                return;
            }

            // Usamos la API de búsqueda existente
            fetch(`/api/admin/clientes/buscar?q=${encodeURIComponent(query)}`)
                .then(response => response.json())
                .then(data => {
                    listaResultados.innerHTML = ''; // Limpiar lista anterior

                    if (data.length > 0) {
                        listaResultados.style.display = 'block';
                        data.forEach(cliente => {
                            // Crear el item de la lista
                            const item = document.createElement('a');
                            item.className = 'list-group-item list-group-item-action';
                            item.href = '#';
                            item.style.cursor = 'pointer';
                            
                            // Mostrar Nombre y Documento
                            const nombreMostrar = cliente.nombre_completo || `${cliente.nombre} ${cliente.apellido}`;
                            item.innerHTML = `<strong>${nombreMostrar}</strong> <br><small class='text-muted'>${cliente.documento || 'Sin doc'}</small>`;

                            // Al hacer clic
                            item.addEventListener('click', function(e) {
                                e.preventDefault();
                                inputBusqueda.value = nombreMostrar; // Poner nombre en el input visible
                                inputId.value = cliente.id;          // Guardar ID en el input oculto
                                listaResultados.style.display = 'none'; // Ocultar lista
                                if(btnGenerar) btnGenerar.disabled = false; // Activar botón
                            });

                            listaResultados.appendChild(item);
                        });
                    } else {
                        listaResultados.style.display = 'none';
                    }
                })
                .catch(err => console.error('Error buscando clientes:', err));
        });

        // Ocultar lista si hacemos clic fuera
        document.addEventListener('click', function(e) {
            if (e.target !== inputBusqueda && e.target !== listaResultados) {
                listaResultados.style.display = 'none';
            }
        });
    }
});

// ==========================================
// FUNCIONES DE ARQUEO
// ==========================================

async function generarReporteArqueo(e) {
    e.preventDefault();
    
    const data = {
        caja_id: document.getElementById('cajaId').value,
        fecha_desde: document.getElementById('fechaDesde').value,
        fecha_hasta: document.getElementById('fechaHasta').value
    };

    const btnSubmit = e.target.querySelector('button[type="submit"]');
    const txtOriginal = btnSubmit.innerHTML;
    btnSubmit.disabled = true;
    btnSubmit.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Generando...';

    try {
        const res = await fetch('/api/reportes/arqueo', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(data)
        });
        
        if (!res.ok) throw new Error('Error en el servidor');
        
        const reporte = await res.json();
        renderizarTablaArqueo(reporte);
        
    } catch(err) {
        console.error(err);
        alert('Error al generar el arqueo. Revise la consola.');
    } finally {
        btnSubmit.disabled = false;
        btnSubmit.innerHTML = txtOriginal;
    }
}

function renderizarTablaArqueo(reporte) {
    const tbody = document.getElementById('tbodyMovimientos');
    tbody.innerHTML = '';
    
    if(!reporte.movimientos || reporte.movimientos.length === 0) {
        tbody.innerHTML = '<tr><td colspan="5" class="text-center py-4 text-muted">No hay movimientos registrados en este periodo.</td></tr>';
    } else {
        reporte.movimientos.forEach(m => {
            const badgeClass = m.tipo === 'ingreso' ? 'bg-success' : 'bg-danger';
            const montoClass = m.tipo === 'ingreso' ? 'text-success' : 'text-danger';
            
            tbody.innerHTML += `
                <tr>
                    <td>${m.fecha}</td>
                    <td><span class="badge ${badgeClass}">${m.tipo.toUpperCase()}</span></td>
                    <td>${m.concepto}</td>
                    <td>${m.usuario}</td>
                    <td class="text-end ${montoClass}">${m.monto.toLocaleString('es-PY')}</td>
                </tr>
            `;
        });
    }

    // Actualizar Totales
    document.getElementById('totalIngresos').textContent = (reporte.total_ingresos || 0).toLocaleString('es-PY');
    document.getElementById('totalEgresos').textContent = (reporte.total_egresos || 0).toLocaleString('es-PY');
    document.getElementById('saldoPeriodo').textContent = (reporte.saldo_periodo || 0).toLocaleString('es-PY');
    
    document.getElementById('resultadoArqueo').style.display = 'block';
}

// ==========================================
// FUNCIONES DE ESTADO DE CUENTA
// ==========================================

async function generarEstadoCuenta() {
    const clienteId = document.getElementById('cliente_id_reporte').value;
    
    if (!clienteId) {
        alert('Por favor, busque y seleccione un cliente primero.');
        return;
    }

    const btn = document.getElementById('btnGenerarExtracto');
    const txtOriginal = btn.innerHTML;
    btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Cargando...';
    btn.disabled = true;

    try {
        const res = await fetch('/api/cobros/reporte/estado-cuenta', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ cliente_id: clienteId })
        });

        if (!res.ok) throw new Error('Error al obtener datos del cliente');
        
        const data = await res.json();
        renderizarEstadoCuenta(data);

    } catch (error) {
        console.error(error);
        alert('Ocurrió un error al generar el estado de cuenta.');
    } finally {
        btn.innerHTML = txtOriginal;
        btn.disabled = false;
    }
}

function renderizarEstadoCuenta(data) {
    document.getElementById('nombreClienteHeader').textContent = data.cliente;
    document.getElementById('docClienteHeader').textContent = `Documento / RUC: ${data.documento}`;
    
    const container = document.getElementById('contenedorContratos');
    container.innerHTML = '';

    if (!data.contratos || data.contratos.length === 0) {
        container.innerHTML = '<div class="alert alert-warning text-center">Este cliente no tiene contratos activos registrados.</div>';
    } else {
        data.contratos.forEach(c => {
            // Generar filas de historial de pagos
            let filasPagos = '';
            if (c.historial_pagos && c.historial_pagos.length > 0) {
                c.historial_pagos.forEach(p => {
                    filasPagos += `
                        <tr>
                            <td>${formatoFecha(p.fecha_pago)}</td>
                            <td>${p.forma_pago}</td>
                            <td>${p.referencia || '-'}</td>
                            <td class="text-end">${p.monto.toLocaleString('es-PY')}</td>
                        </tr>
                    `;
                });
            } else {
                filasPagos = '<tr><td colspan="4" class="text-center text-muted">Sin pagos registrados</td></tr>';
            }

            const htmlContrato = `
                <div class="contrato-card mb-4 border rounded shadow-sm">
                    <div class="contrato-header bg-light p-3 border-bottom">
                        <div class="row align-items-center">
                            <div class="col-8">
                                <h5 class="m-0 text-primary fw-bold">Contrato N° ${c.numero}</h5>
                                <small class="text-muted"><i class="fas fa-map-marker-alt me-1"></i>${c.lote}</small>
                            </div>
                            <div class="col-4 text-end">
                                <span class="badge ${c.cuotas_vencidas > 0 ? 'bg-danger' : 'bg-success'} p-2">
                                    ${c.cuotas_vencidas > 0 ? c.cuotas_vencidas + ' Cuotas Vencidas' : 'Al día'}
                                </span>
                            </div>
                        </div>
                    </div>
                    <div class="card-body p-3">
                        <div class="row mb-4 g-2">
                            <div class="col-md-4">
                                <div class="p-2 border rounded text-center">
                                    <span class="d-block text-muted small">Valor Total</span>
                                    <span class="d-block fw-bold">Gs. ${c.total_contrato.toLocaleString('es-PY')}</span>
                                </div>
                            </div>
                            <div class="col-md-4">
                                <div class="p-2 border rounded text-center bg-light">
                                    <span class="d-block text-muted small">Total Pagado</span>
                                    <span class="d-block fw-bold text-success">Gs. ${c.total_pagado.toLocaleString('es-PY')}</span>
                                </div>
                            </div>
                            <div class="col-md-4">
                                <div class="p-2 border rounded text-center" style="background-color: #fff5f5;">
                                    <span class="d-block text-muted small">Saldo Pendiente</span>
                                    <span class="d-block fw-bold text-danger">Gs. ${c.saldo_pendiente.toLocaleString('es-PY')}</span>
                                </div>
                            </div>
                        </div>

                        <h6 class="border-bottom pb-2 mb-3">Historial de Pagos</h6>
                        <div class="table-responsive">
                            <table class="table table-sm table-bordered mb-0">
                                <thead class="table-light">
                                    <tr>
                                        <th>Fecha</th>
                                        <th>Forma Pago</th>
                                        <th>Referencia</th>
                                        <th class="text-end">Monto (Gs.)</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    ${filasPagos}
                                </tbody>
                            </table>
                        </div>
                    </div>
                </div>
            `;
            container.innerHTML += htmlContrato;
        });
    }

    document.getElementById('resultadoCliente').style.display = 'block';
}

function formatoFecha(fechaIso) {
    if (!fechaIso) return '';
    const fecha = new Date(fechaIso);
    return fecha.toLocaleDateString('es-PY');
}