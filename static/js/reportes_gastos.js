document.addEventListener('DOMContentLoaded', function() {
    // Configurar fechas por defecto (1er día del mes - Hoy)
    const hoy = new Date();
    const primerDia = new Date(hoy.getFullYear(), hoy.getMonth(), 1);
    
    const inputDesde = document.getElementById('fechaDesde');
    const inputHasta = document.getElementById('fechaHasta');

    if(inputDesde) inputDesde.valueAsDate = primerDia;
    if(inputHasta) inputHasta.valueAsDate = hoy;

    const form = document.getElementById('formReporteGastos');
    if (form) {
        form.addEventListener('submit', generarReporteGastos);
    }
});

async function generarReporteGastos(e) {
    e.preventDefault();
    
    const desde = document.getElementById('fechaDesde').value;
    const hasta = document.getElementById('fechaHasta').value;
    const btn = e.target.querySelector('button[type="submit"]');
    
    // Feedback de carga
    const textoOriginal = btn.innerHTML;
    btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Procesando...';
    btn.disabled = true;

    try {
        const res = await fetch('/api/reportes/gastos/resumen', {
            method: 'POST', 
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ fecha_desde: desde, fecha_hasta: hasta })
        });
        
        if(!res.ok) throw new Error('Error al obtener datos');

        const data = await res.json();
        renderizarReporte(data, desde, hasta);
        
    } catch (error) {
        console.error(error);
        alert('Error al generar el reporte de gastos.');
    } finally {
        btn.innerHTML = textoOriginal;
        btn.disabled = false;
    }
}

function renderizarReporte(data, desde, hasta) {
    // 1. Renderizar Resumen
    const tbodyRes = document.getElementById('tbodyResumen');
    tbodyRes.innerHTML = '';
    
    if (data.resumen.length === 0) {
        tbodyRes.innerHTML = '<tr><td colspan="2" class="text-center">Sin movimientos</td></tr>';
    } else {
        data.resumen.forEach(r => {
            tbodyRes.innerHTML += `
                <tr>
                    <td>${r.nombre}</td>
                    <td class="text-end fw-bold">${r.total.toLocaleString('es-PY')}</td>
                </tr>`;
        });
    }

    // 2. Renderizar Detalle
    const tbodyDet = document.getElementById('tbodyDetalle');
    tbodyDet.innerHTML = '';
    
    if (data.detalles.length === 0) {
        tbodyDet.innerHTML = '<tr><td colspan="5" class="text-center text-muted py-3">No se encontraron gastos en este periodo.</td></tr>';
    } else {
        data.detalles.forEach(d => {
            // Manejo de fecha seguro
            const fecha = new Date(d.fecha_factura + 'T00:00:00').toLocaleDateString('es-PY');
            
            tbodyDet.innerHTML += `
                <tr>
                    <td>${fecha}</td>
                    <td>${d.proveedor_nombre}</td>
                    <td>${d.numero_factura || '-'}</td>
                    <td>${d.categoria_nombre} <br><small class="text-muted">${d.detalle}</small></td>
                    <td class="text-end">${d.monto.toLocaleString('es-PY')}</td>
                </tr>
            `;
        });
    }

    // 3. Actualizar Totales y Mostrar
    document.getElementById('tdTotalGeneral').textContent = data.total_general.toLocaleString('es-PY');
    document.getElementById('spanPeriodo').textContent = `${formatoFecha(desde)} al ${formatoFecha(hasta)}`;
    document.getElementById('panelResultados').style.display = 'block';
}

function formatoFecha(fechaStr) {
    if(!fechaStr) return '';
    const [y, m, d] = fechaStr.split('-');
    return `${d}/${m}/${y}`;
}