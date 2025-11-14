document.addEventListener('DOMContentLoaded', function() {
    // Establecer fechas por defecto (1er día del mes actual - Hoy)
    const hoy = new Date();
    const primerDia = new Date(hoy.getFullYear(), hoy.getMonth(), 1);
    
    document.getElementById('fechaDesde').valueAsDate = primerDia;
    document.getElementById('fechaHasta').valueAsDate = hoy;

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

    // Efecto de carga en botón
    const originalText = btn.innerHTML;
    btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Procesando...';
    btn.disabled = true;

    try {
        const res = await fetch('/api/reportes/ventas/resumen', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                tipo: tipo,
                fecha_desde: desde,
                fecha_hasta: hasta
            })
        });

        if(!res.ok) throw new Error('Error al conectar con el servidor');
        const data = await res.json();

        renderizarTabla(data, tipo, desde, hasta);

    } catch (error) {
        console.error(error);
        alert('Ocurrió un error al generar el reporte: ' + error.message);
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
    
    tbody.innerHTML = '';
    
    // Configurar encabezados
    titulo.textContent = tipo === 'vendedores' ? 'INFORME DE RENDIMIENTO DE VENDEDORES' : 'RANKING DE MEJORES CLIENTES';
    periodo.textContent = `Periodo del reporte: ${formatoFecha(desde)} al ${formatoFecha(hasta)}`;

    let sumaTotal = 0;

    if (data.length === 0) {
        tbody.innerHTML = '<tr><td colspan="3" class="text-center text-muted py-4">No se encontraron datos para los criterios seleccionados.</td></tr>';
    } else {
        data.forEach(item => {
            sumaTotal += item.total;
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td>${item.label}</td>
                <td class="text-center">${item.cantidad}</td>
                <td class="text-end">${item.total.toLocaleString('es-PY')}</td>
            `;
            tbody.appendChild(tr);
        });
    }

    totalGen.textContent = sumaTotal.toLocaleString('es-PY');
    document.getElementById('panelResultados').style.display = 'block';
}

function formatoFecha(fechaStr) {
    // Convierte YYYY-MM-DD a DD/MM/YYYY
    if (!fechaStr) return '';
    const [y, m, d] = fechaStr.split('-');
    return `${d}/${m}/${y}`;
}