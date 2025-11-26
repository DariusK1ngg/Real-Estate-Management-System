document.addEventListener('DOMContentLoaded', function() {
    cargarContratos();

    document.getElementById('edit-estado').addEventListener('change', function(e) {
        const val = e.target.value;
        const aviso = document.getElementById('aviso-deuda');
        if (val === 'rescindido' || val === 'inactivo') {
            aviso.style.display = 'block';
        } else {
            aviso.style.display = 'none';
        }
    });
});

async function cargarContratos() {
    const texto = document.getElementById('filtro-texto').value;
    const estado = document.getElementById('filtro-estado').value;
    
    const tbody = document.getElementById('tabla-contratos');
    tbody.innerHTML = '<tr><td colspan="6" class="text-center">Cargando...</td></tr>';

    try {
        const res = await fetch(`/api/admin/contratos?q=${texto}&estado=${estado}`);
        const contratos = await res.json();
        
        tbody.innerHTML = '';
        
        if(contratos.length === 0) {
            tbody.innerHTML = '<tr><td colspan="6" class="text-center">No se encontraron contratos.</td></tr>';
            return;
        }

        contratos.forEach(c => {
            let badgeClass = 'bg-secondary';
            if(c.estado === 'activo') badgeClass = 'bg-success';
            if(c.estado === 'rescindido') badgeClass = 'bg-danger';
            if(c.estado === 'finalizado') badgeClass = 'bg-primary';

            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td>${c.numero_contrato}</td>
                <td>
                    ${c.cliente_nombre}<br>
                    <small class="text-muted">CI: ${c.cliente_documento || 'N/A'}</small>
                </td>
                <td>${c.fraccionamiento} - ${c.lote_info}</td>
                <td><span class="badge ${badgeClass}">${c.estado.toUpperCase()}</span></td>
                <td>Gs. ${new Intl.NumberFormat('es-PY').format(c.valor_total)}</td>
                <td>
                    <button class="btn btn-sm btn-info" onclick="verPDF(${c.id})"><i class="fas fa-print"></i></button>
                    <button class="btn btn-sm btn-warning" onclick="abrirEditarContrato(${c.id})"><i class="fas fa-edit"></i></button>
                </td>
            `;
            tbody.appendChild(tr);
        });

    } catch (error) {
        console.error(error);
        tbody.innerHTML = '<tr><td colspan="6" class="text-center text-danger">Error al cargar datos</td></tr>';
    }
}

let modalEditar = null;

async function abrirEditarContrato(id) {
    if(!modalEditar) modalEditar = new bootstrap.Modal(document.getElementById('modalEditarContrato'));
    
    try {
        const res = await fetch(`/api/admin/contratos/${id}`);
        const data = await res.json();
        
        document.getElementById('edit-contrato-id').value = data.id;
        document.getElementById('edit-numero').value = data.numero_contrato;
        document.getElementById('edit-estado').value = data.estado;
        document.getElementById('edit-obs').value = data.observaciones || '';
        
        document.getElementById('aviso-deuda').style.display = 'none';
        
        modalEditar.show();
    } catch (e) {
        alert("Error al cargar datos del contrato");
    }
}

async function guardarEdicionContrato() {
    const id = document.getElementById('edit-contrato-id').value;
    const data = {
        numero_contrato: document.getElementById('edit-numero').value,
        estado: document.getElementById('edit-estado').value,
        observaciones: document.getElementById('edit-obs').value
    };
    
    if (confirm("¿Estás seguro de guardar los cambios? Si cambias a Rescindido/Inactivo se eliminará la deuda.")) {
        try {
            const res = await fetch(`/api/admin/contratos/${id}`, {
                method: 'PATCH',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            });
            const result = await res.json();
            
            if(res.ok) {
                if(typeof Swal !== 'undefined') {
                    Swal.fire('Éxito', result.message, 'success');
                } else {
                    alert(result.message);
                }
                modalEditar.hide();
                cargarContratos();
            } else {
                if(typeof Swal !== 'undefined') {
                    Swal.fire('Error', 'No se pudo actualizar', 'error');
                } else {
                    alert('No se pudo actualizar');
                }
            }
        } catch (e) {
            if(typeof Swal !== 'undefined') {
                Swal.fire('Error', 'Error de red', 'error');
            } else {
                alert('Error de red');
            }
        }
    }
}

function verPDF(id) {
    window.open(`/admin/inventario/contrato_pdf/${id}`, '_blank');
}