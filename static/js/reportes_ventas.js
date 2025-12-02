document.addEventListener('DOMContentLoaded', function() {
    // Fechas por defecto
    const hoy = new Date();
    const primerDia = new Date(hoy.getFullYear(), hoy.getMonth(), 1);
    
    const inpDesde = document.getElementById('fechaDesde');
    const inpHasta = document.getElementById('fechaHasta');
    
    if(inpDesde) inpDesde.valueAsDate = primerDia;
    if(inpHasta) inpHasta.valueAsDate = hoy;

    const form = document.getElementById('formReporteVentas');
    if (form) {
        form.addEventListener('submit', generarReporte);
    }
});

async function generarReporte(e) {
    e.preventDefault();
    
    const tipo = document.getElementById('tipoReporte').value;
    const desde = document.getElementById('fechaDesde').value;
    const hasta = document.getElementById('fechaHasta').value;
    const btn = e.submitter;

    const originalText = btn.innerHTML;
    btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> ...';
    btn.disabled = true;

    try {
        const res = await fetch('/api/reportes/ventas/resumen', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ tipo, fecha_desde: desde, fecha_hasta: hasta })
        });

        if(!res.ok) throw new Error('Error al conectar con el servidor');
        const data = await res.json();

        renderizarTabla(data, tipo, desde, hasta);

    } catch (error) {
        console.error(error);
        alert('Error: ' + error.message);
    } finally {
        btn.innerHTML = originalText;
        btn.disabled = false;
    }
}

function renderizarTabla(data, tipo, desde, hasta) {
    const tbody = document.getElementById('tbodyResultados');
    const titulo = document.getElementById('tituloReporte');
    const periodo = document.getElementById('periodoReporte');
    const totalGen = document.getElementById('totalGeneral');
    const thPrincipal = document.getElementById('thColumnaPrincipal');
    
    tbody.innerHTML = '';
    
    // Títulos dinámicos
    if (tipo === 'servicios_tipo') {
        titulo.textContent = 'REPORTE DE SERVICIOS POR CONCEPTO';
        thPrincipal.textContent = 'Servicio / Concepto';
    } else {
        titulo.textContent = 'ESTADO DE COBRO DE SERVICIOS';
        thPrincipal.textContent = 'Estado (Pagado / Pendiente)';
    }
    
    periodo.textContent = `Periodo: ${formatoFecha(desde)} al ${formatoFecha(hasta)}`;

    let sumaTotal = 0;

    if (data.length === 0) {
        tbody.innerHTML = '<tr><td colspan="3" class="text-center text-muted py-4">No se encontraron servicios en este periodo.</td></tr>';
    } else {
        data.forEach(item => {
            sumaTotal += item.total;
            
            // Colorear badge si es estado
            let labelHtml = item.label;
            if (tipo === 'servicios_estado') {
                let color = item.label === 'PAGADA' ? 'success' : 'danger';
                if (item.label === 'PENDIENTE') color = 'warning text-dark';
                labelHtml = `<span class="badge bg-${color}">${item.label}</span>`;
            }

            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td>${labelHtml}</td>
                <td class="text-center">${item.cantidad}</td>
                <td class="text-end fw-bold">${item.total.toLocaleString('es-PY')}</td>
            `;
            tbody.appendChild(tr);
        });
    }

    totalGen.textContent = sumaTotal.toLocaleString('es-PY');
    document.getElementById('panelResultados').style.display = 'block';
}

function formatoFecha(fechaStr) {
    if (!fechaStr) return '';
    const [y, m, d] = fechaStr.split('-');
    return `${d}/${m}/${y}`;
}