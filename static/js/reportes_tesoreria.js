// static/js/reportes_tesoreria.js

document.addEventListener('DOMContentLoaded', async function() {
    // Fechas por defecto
    const hoy = new Date();
    document.getElementById('fechaDesde').valueAsDate = hoy;
    document.getElementById('fechaHasta').valueAsDate = hoy;

    // Cargar lista de cuentas bancarias
    await cargarCuentasSelect();

    const formExtracto = document.getElementById('formExtracto');
    if (formExtracto) {
        formExtracto.addEventListener('submit', generarExtracto);
    }
});

async function cargarCuentasSelect() {
    const select = document.getElementById('cuentaId');
    try {
        const res = await fetch('/api/admin/cuentas-bancarias');
        const cuentas = await res.json();
        
        select.innerHTML = '';
        cuentas.forEach(c => {
            const option = document.createElement('option');
            option.value = c.id;
            option.textContent = `${c.entidad_nombre} - ${c.numero_cuenta} (${c.moneda})`;
            select.appendChild(option);
        });
    } catch (e) {
        console.error("Error cargando cuentas:", e);
        select.innerHTML = '<option value="">Error al cargar cuentas</option>';
    }
}

async function generarExtracto(e) {
    e.preventDefault();
    
    const data = {
        cuenta_id: document.getElementById('cuentaId').value,
        fecha_desde: document.getElementById('fechaDesde').value,
        fecha_hasta: document.getElementById('fechaHasta').value
    };

    const btnSubmit = e.target.querySelector('button[type="submit"]');
    btnSubmit.disabled = true;
    btnSubmit.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Cargando...';

    try {
        const res = await fetch('/api/reportes/extracto', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(data)
        });
        
        if (!res.ok) throw new Error('Error al obtener datos');
        
        const movimientos = await res.json();
        renderizarTablaExtracto(movimientos);
        
    } catch(err) {
        console.error(err);
        alert('Error al generar el extracto.');
    } finally {
        btnSubmit.disabled = false;
        btnSubmit.innerHTML = '<i class="fas fa-search"></i> Generar';
    }
}

function renderizarTablaExtracto(movimientos) {
    const tbody = document.getElementById('tbodyExtracto');
    tbody.innerHTML = '';
    
    if(movimientos.length === 0) {
        tbody.innerHTML = '<tr><td colspan="5" class="text-center py-4 text-muted">No hay movimientos en este rango de fechas.</td></tr>';
    } else {
        movimientos.forEach(m => {
            // Monto positivo es Crédito (ingreso), negativo es Débito (egreso)
            const esDebito = m.monto < 0;
            const debito = esDebito ? Math.abs(m.monto).toLocaleString('es-PY') : '';
            const credito = !esDebito ? m.monto.toLocaleString('es-PY') : '';
            
            tbody.innerHTML += `
                <tr>
                    <td>${m.fecha}</td>
                    <td>${m.concepto}</td>
                    <td>${m.referencia || '-'}</td>
                    <td class="text-end text-danger">${debito}</td>
                    <td class="text-end text-success">${credito}</td>
                </tr>
            `;
        });
    }
    
    document.getElementById('resultadoExtracto').style.display = 'block';
}