document.addEventListener('DOMContentLoaded', function() {
    cargarContratos();
});

async function cargarContratos() {
    const tbody = document.getElementById('tbodyContratos');
    tbody.innerHTML = '<tr><td colspan="9" class="text-center">Cargando contratos...</td></tr>';
    
    try {
        const response = await fetch('/api/admin/contratos');
        if (!response.ok) throw new Error('Error al cargar la lista de contratos.');
        
        const contratos = await response.json();
        
        if (contratos.length === 0) {
            tbody.innerHTML = '<tr><td colspan="9" class="text-center text-muted">No hay contratos registrados.</td></tr>';
            return;
        }
        
        tbody.innerHTML = '';
        contratos.forEach(contrato => {
            const tr = document.createElement('tr');
            const fechaFormateada = new Date(contrato.fecha_contrato + 'T00:00:00').toLocaleDateString('es-ES', { timeZone: 'UTC' });
            
            tr.innerHTML = `
                <td><strong>${contrato.numero_contrato}</strong></td>
                <td>${fechaFormateada}</td>
                <td>${contrato.cliente_nombre}</td>
                <td>${contrato.lote_info}</td>
                <td>${contrato.fraccionamiento}</td>
                <td>${contrato.valor_total.toLocaleString('es-PY')}</td>
                <td>${contrato.cantidad_cuotas}</td>
                <td><span class="badge ${contrato.estado === 'activo' ? 'bg-success' : 'bg-secondary'}">${contrato.estado}</span></td>
                <td>
                    <button class="btn btn-sm btn-secondary" 
                            onclick="window.open('/admin/inventario/contrato_pdf/${contrato.id}', '_blank')" 
                            title="Ver Contrato PDF">
                        <i class="fas fa-file-pdf"></i>
                    </button>
                    
                    </td>
            `;
            tbody.appendChild(tr);
        });
        
    } catch (error) {
        console.error(error);
        tbody.innerHTML = `<tr><td colspan="9" class="text-center text-danger">${error.message}</td></tr>`;
    }
}