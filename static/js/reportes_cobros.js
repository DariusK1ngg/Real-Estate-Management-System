// static/js/reportes_cobros.js

document.addEventListener('DOMContentLoaded', function() {
    // --- CONFIGURACIÓN ARQUEO ---
    const hoy = new Date();
    
    const inputDesde = document.getElementById('fechaDesde');
    const inputHasta = document.getElementById('fechaHasta');
    
    if(inputDesde) inputDesde.valueAsDate = hoy;
    if(inputHasta) inputHasta.valueAsDate = hoy;

    const formArqueo = document.getElementById('formArqueo');
    if (formArqueo) {
        formArqueo.addEventListener('submit', generarReporteArqueo);
    }

    // --- CONFIGURACIÓN CLIENTES (SELECT2) ---
    // Solo inicializar si existe el elemento
    if ($('#selectClienteReporte').length > 0) {
        $('#selectClienteReporte').select2({
            theme: 'bootstrap-5',
            placeholder: "Escriba nombre, apellido o documento...",
            minimumInputLength: 2,
            ajax: {
                url: '/api/admin/clientes/buscar',
                dataType: 'json',
                delay: 250,
                data: function(params) {
                    return { q: params.term };
                },
                processResults: function(data) {
                    return {
                        results: data.map(c => ({
                            id: c.id,
                            text: `${c.nombre_completo} (${c.documento})`
                        }))
                    };
                },
                cache: true
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
        alert('Error al generar el arqueo.');
    } finally {
        btnSubmit.disabled = false;
        btnSubmit.innerHTML = txtOriginal;
    }
}

function renderizarTablaArqueo(reporte) {
    const tbody = document.getElementById('tbodyMovimientos');
    tbody.innerHTML = '';
    
    if(reporte.movimientos.length === 0) {
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
    document.getElementById('totalIngresos').textContent = reporte.total_ingresos.toLocaleString('es-PY');
    document.getElementById('totalEgresos').textContent = reporte.total_egresos.toLocaleString('es-PY');
    document.getElementById('saldoPeriodo').textContent = reporte.saldo_periodo.toLocaleString('es-PY');
    
    // Mostrar contenedor
    document.getElementById('resultadoArqueo').style.display = 'block';
}

// ==========================================
// FUNCIONES DE ESTADO DE CUENTA (CLIENTES)
// ==========================================

async function generarEstadoCuenta() {
    const clienteId = $('#selectClienteReporte').val();
    
    if (!clienteId) {
        alert('Por favor, busque y seleccione un cliente primero.');
        return;
    }

    // Efecto loading manual porque este botón está fuera de un form estándar
    const btn = document.querySelector('#tab-clientes button.btn-info');
    const txtOriginal = btn.innerHTML;
    btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Cargando...';
    btn.disabled = true;

    try {
        const res = await fetch('/api/reportes/clientes/estado-cuenta', {
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

    if (data.contratos.length === 0) {
        container.innerHTML = '<div class="alert alert-warning text-center">Este cliente no tiene contratos activos registrados.</div>';
    } else {
        data.contratos.forEach(c => {
            // Generar filas de historial de pagos
            let filasPagos = '';
            if (c.historial_pagos.length > 0) {
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
                <div class="contrato-card">
                    <div class="contrato-header">
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
                    <div class="card-body">
                        <div class="row mb-4 g-2">
                            <div class="col-md-4">
                                <div class="info-box">
                                    <span class="info-label">Valor Total</span>
                                    <span class="info-value text-dark">Gs. ${c.total_contrato.toLocaleString('es-PY')}</span>
                                </div>
                            </div>
                            <div class="col-md-4">
                                <div class="info-box" style="border-color: #d1e7dd; background-color: #f8fffb;">
                                    <span class="info-label">Total Pagado</span>
                                    <span class="info-value text-success">Gs. ${c.total_pagado.toLocaleString('es-PY')}</span>
                                </div>
                            </div>
                            <div class="col-md-4">
                                <div class="info-box" style="border-color: #f8d7da; background-color: #fff8f8;">
                                    <span class="info-label">Saldo Pendiente</span>
                                    <span class="info-value text-danger">Gs. ${c.saldo_pendiente.toLocaleString('es-PY')}</span>
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
    // Manejar fecha ISO (2023-11-15T14:30:00)
    const fecha = new Date(fechaIso);
    return fecha.toLocaleDateString('es-PY');
}