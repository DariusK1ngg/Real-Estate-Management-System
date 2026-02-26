/* static/js/inventario_contratos.js */

// Funciones auxiliares globales
function formatMoney(amount) {
    if (!amount) return '0';
    return new Intl.NumberFormat('es-PY').format(amount);
}

function parseMoney(str) {
    if (!str) return 0;
    return parseFloat(str.toString().replace(/\./g, '').replace(',', '.'));
}

document.addEventListener('DOMContentLoaded', function() {
    // Detectar pantalla
    if(document.getElementById('formContrato')) initCargaContrato();
    if(document.getElementById('tablaContratos')) cargarContratos();
});

// ==========================================
// 1. LÓGICA DE CARGA (NUEVO CONTRATO)
// ==========================================
let cuotasGeneradas = []; 

function initCargaContrato() {
    // Cargar Vendedores
    fetch('/api/admin/vendedores').then(r=>r.json()).then(data => {
        const sel = document.getElementById('selectVendedor');
        if(sel) {
            sel.innerHTML = '<option value="">-- Sin Vendedor --</option>';
            data.forEach(v => {
                const opt = document.createElement('option');
                opt.value = v.id; opt.text = v.nombre_completo;
                sel.appendChild(opt);
            });
        }
    });

    // --- BÚSQUEDA DE CLIENTES SIMPLE (SIN SELECT2) ---
    const inputBuscador = document.getElementById('cliente_buscador');
    const inputHidden = document.getElementById('cliente_id');
    const listaResultados = document.getElementById('lista_resultados_clientes');

    if(inputBuscador) {
        inputBuscador.addEventListener('input', function() {
            const query = this.value;
            
            if (query.length < 2) {
                listaResultados.style.display = 'none';
                listaResultados.innerHTML = '';
                inputHidden.value = '';
                return;
            }

            fetch(`/api/inventario/clientes/buscar_simple?q=${query}`)
                .then(r => r.json())
                .then(data => {
                    listaResultados.innerHTML = '';
                    if (data.length > 0) {
                        listaResultados.style.display = 'block';
                        data.forEach(c => {
                            const item = document.createElement('a');
                            item.className = 'list-group-item list-group-item-action';
                            item.style.cursor = 'pointer';
                            item.textContent = c.texto;
                            
                            item.addEventListener('click', function() {
                                inputBuscador.value = c.texto;
                                inputHidden.value = c.id;
                                listaResultados.style.display = 'none';
                            });
                            
                            listaResultados.appendChild(item);
                        });
                    } else {
                        listaResultados.style.display = 'none';
                    }
                })
                .catch(err => console.error("Error buscando cliente:", err));
        });

        // Ocultar lista al hacer click fuera
        document.addEventListener('click', function(e) {
            if (e.target !== inputBuscador && e.target !== listaResultados) {
                listaResultados.style.display = 'none';
            }
        });
    }

    // 1. Cargar Fraccionamientos (Inmuebles)
    fetch('/api/admin/fraccionamientos').then(r=>r.json()).then(data => {
        const sel = document.getElementById('selectFraccionamiento');
        sel.innerHTML = '<option value="">-- Seleccione --</option>';
        data.forEach(f => {
            const opt = document.createElement('option');
            opt.value = f.id; opt.text = f.nombre;
            sel.appendChild(opt);
        });
    });

    // 2. Al elegir Fraccionamiento -> Cargar Lotes Disponibles
    document.getElementById('selectFraccionamiento').addEventListener('change', function(e) {
        const fid = e.target.value;
        const selLote = document.getElementById('selectLote');
        
        selLote.innerHTML = '<option value="">Cargando...</option>';
        selLote.disabled = true;

        if(!fid) {
            selLote.innerHTML = '<option value="">-- Seleccione Fraccionamiento --</option>';
            return;
        }

        fetch(`/api/admin/fraccionamientos/${fid}/lotes-disponibles`).then(r=>r.json()).then(lotes => {
            selLote.innerHTML = '<option value="">-- Seleccione Lote --</option>';
            if(lotes.length === 0) {
                 selLote.innerHTML = '<option value="">No hay lotes disponibles</option>';
            } else {
                lotes.forEach(l => {
                    const opt = document.createElement('option');
                    opt.value = l.id; opt.text = l.texto;
                    selLote.appendChild(opt);
                });
                selLote.disabled = false;
            }
        });
    });

    // Planes (Al elegir lote)
    $('#selectLote').on('change', function() {
        const lid = $(this).val();
        if(!lid) return;
        fetch(`/api/admin/lotes/${lid}/precios`).then(r=>r.json()).then(planes => {
            const sel = document.getElementById('selectPlan');
            sel.innerHTML = '<option value="">-- Personalizado --</option>';
            planes.forEach(p => {
                const opt = document.createElement('option');
                opt.text = `${p.cantidad_cuotas}x Gs. ${formatMoney(p.precio_cuota)} (Total: ${formatMoney(p.precio_total)})`;
                opt.dataset.total = p.precio_total;
                opt.dataset.cuotas = p.cantidad_cuotas;
                opt.dataset.valor = p.precio_cuota;
                sel.appendChild(opt);
            });
        });
    });

    // Auto-llenado desde Plan
    document.getElementById('selectPlan').addEventListener('change', function(e) {
        const opt = e.target.options[e.target.selectedIndex];
        if(opt.dataset.total) {
            document.getElementById('valor_total').value = formatMoney(opt.dataset.total);
            document.getElementById('cantidad_cuotas').value = opt.dataset.cuotas;
            document.getElementById('valor_cuota').value = formatMoney(opt.dataset.valor);
            document.getElementById('cuota_inicial').value = '0';
        }
    });

    // Envío Final
    document.getElementById('formContrato').addEventListener('submit', function(e) {
        e.preventDefault();
        
        // Validación manual del cliente
        if (!document.getElementById('cliente_id').value) {
            return Swal.fire('Error', 'Debe buscar y seleccionar un cliente de la lista.', 'warning');
        }

        if(cuotasGeneradas.length === 0) {
            return Swal.fire('Alto', 'Debe generar las cuotas antes de guardar.', 'warning');
        }

        const formData = new FormData(this);
        const data = Object.fromEntries(formData.entries());
        
        // Limpiar números
        data.valor_total = parseMoney(data.valor_total);
        data.cuota_inicial = parseMoney(data.cuota_inicial);
        data.valor_cuota = parseMoney(data.valor_cuota);
        
        // Adjuntar tabla
        data.cuotas_generadas = cuotasGeneradas;

        fetch('/api/admin/contratos', {
            method: 'POST', headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(data)
        }).then(r=>r.json()).then(res => {
            if(res.ok) {
                Swal.fire('Guardado', 'Contrato creado con éxito', 'success').then(() => window.location.href="/admin/inventario/movimientos");
            } else {
                Swal.fire('Error', res.error, 'error');
            }
        }).catch(()=> Swal.fire('Error', 'Fallo de red', 'error'));
    });
}

window.calcularCuota = function() {
    const total = parseMoney(document.getElementById('valor_total').value);
    const inicial = parseMoney(document.getElementById('cuota_inicial').value);
    const cant = parseInt(document.getElementById('cantidad_cuotas').value) || 1;
    
    if(total <= 0) return;
    
    const saldo = total - inicial;
    const valor = Math.round(saldo / cant);
    document.getElementById('valor_cuota').value = formatMoney(valor);
};

window.generarCuotas = function() {
    const cant = parseInt(document.getElementById('cantidad_cuotas').value);
    const valor = parseMoney(document.getElementById('valor_cuota').value);
    
    // Obtener fecha de inicio (string YYYY-MM-DD)
    const fechaStr = document.getElementById('fecha_contrato').value;
    if(!fechaStr) return Swal.fire('Atención', 'Seleccione fecha de inicio', 'warning');

    // Crear objeto fecha (evitando problemas de zona horaria)
    const parts = fechaStr.split('-');
    const fechaInicio = new Date(parts[0], parts[1]-1, parts[2]); 
    
    if(cant <= 0 || valor <= 0) return Swal.fire('Error', 'Revise montos y plazos', 'error');

    const tbody = document.getElementById('tbodyCuotas');
    tbody.innerHTML = '';
    cuotasGeneradas = []; 

    for(let i=1; i<=cant; i++) {
        // Cuota 1 = Misma fecha de inicio. Cuota 2 = +1 mes.
        let fecha = new Date(fechaInicio);
        fecha.setMonth(fecha.getMonth() + (i - 1));
        
        // Formatear fecha
        const dia = String(fecha.getDate()).padStart(2, '0');
        const mes = String(fecha.getMonth() + 1).padStart(2, '0');
        const anio = fecha.getFullYear();
        const fechaFmt = `${dia}/${mes}/${anio}`;

        const row = {
            numero: i,
            vencimiento: fechaFmt,
            monto: formatMoney(valor)
        };
        
        cuotasGeneradas.push(row);

        tbody.innerHTML += `
            <tr>
                <td>${row.numero}</td>
                <td>${row.vencimiento}</td>
                <td>Gs. ${row.monto}</td>
            </tr>
        `;
    }
    
    document.getElementById('totalCuotasSum').textContent = cant;
    document.getElementById('btnGuardar').disabled = false;
};

// ==========================================
// 2. CONSULTA Y EDICIÓN (AQUÍ ESTÁ EL CAMBIO)
// ==========================================
let modalEditar = null;

async function cargarContratos() {
    const q = document.getElementById('filtroTexto').value;
    const estado = document.getElementById('filtroEstado').value;
    const tbody = document.querySelector('#tablaContratos tbody');
    
    // CAMBIO: Colspan ahora es 8 porque agregamos la columna de Fraccionamiento
    tbody.innerHTML = '<tr><td colspan="8" class="text-center">Cargando...</td></tr>';
    
    const res = await fetch(`/api/admin/contratos?q=${q}&estado=${estado}`);
    const data = await res.json();
    tbody.innerHTML = '';
    
    if(data.length === 0) {
        tbody.innerHTML = '<tr><td colspan="8" class="text-center">Sin resultados</td></tr>'; return;
    }

    data.forEach(c => {
        const str = JSON.stringify(c).replace(/"/g, '&quot;');
        let badge = 'success';
        if(c.estado==='rescindido') badge='danger';
        if(c.estado==='finalizado') badge='primary';
        if(c.estado==='inactivo') badge='secondary';
        
        // Formatear fecha si viene en formato ISO YYYY-MM-DD
        let fechaMostrar = c.fecha_contrato;
        if(c.fecha_contrato && c.fecha_contrato.includes('-')) {
             const parts = c.fecha_contrato.split('-');
             fechaMostrar = `${parts[2]}/${parts[1]}/${parts[0]}`;
        }

        tbody.innerHTML += `
            <tr>
                <td><strong>${c.numero_contrato}</strong></td>
                <td>${fechaMostrar}</td>
                <td>${c.cliente_nombre}</td>
                <!-- CAMBIO: AGREGADA COLUMNA FRACCIONAMIENTO -->
                <td>${c.fraccionamiento || '-'}</td>
                <td>${c.lote_info}</td>
                <td class="text-end">Gs. ${formatMoney(c.valor_total)}</td>
                <td><span class="badge bg-${badge}">${c.estado.toUpperCase()}</span></td>
                <td class="text-end">
                    <button class="btn btn-sm btn-warning" onclick="abrirEditar(${str})"><i class="fas fa-edit"></i></button>
                    <a href="/admin/inventario/contrato_pdf/${c.id}" target="_blank" class="btn btn-sm btn-info"><i class="fas fa-print"></i></a>
                </td>
            </tr>
        `;
    });
}

window.abrirEditar = function(c) {
    if(!modalEditar) modalEditar = new bootstrap.Modal(document.getElementById('modalEditar'));
    document.getElementById('editId').value = c.id;
    document.getElementById('editNumero').value = c.numero_contrato;
    document.getElementById('editEstado').value = c.estado;
    document.getElementById('editObs').value = c.observaciones || '';
    modalEditar.show();
};

window.guardarEdicion = async function() {
    const id = document.getElementById('editId').value;
    const data = {
        numero_contrato: document.getElementById('editNumero').value,
        estado: document.getElementById('editEstado').value,
        observaciones: document.getElementById('editObs').value
    };
    
    if(data.estado === 'rescindido' && !confirm("¿RESCINDIR? Esto eliminará la deuda y liberará el lote.")) return;

    await fetch(`/api/admin/contratos/${id}`, {
        method: 'PATCH', 
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(data)
    });
    
    modalEditar.hide();
    cargarContratos();
};