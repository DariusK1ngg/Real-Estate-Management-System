/* static/js/inventario_contrato_nuevo.js */

// Funciones auxiliares de formateo
function formatMoney(amount) {
    if (!amount) return '0';
    return new Intl.NumberFormat('es-PY').format(amount);
}

function parseMoney(str) {
    if (!str) return 0;
    // Elimina puntos de mil y reemplaza coma decimal por punto (si aplica)
    return parseFloat(str.toString().replace(/\./g, '').replace(',', '.'));
}

// Variable global para almacenar las cuotas generadas
let cuotasGeneradas = [];

$(document).ready(function() {
    
    // --- INICIALIZACIÓN ---
    cargarVendedores(); 
    
    // 0. Select2 para Fraccionamientos
    $('#fraccionamiento_id').select2({
        ajax: {
            url: '/api/search/fraccionamientos', 
            dataType: 'json',
            delay: 250,
            data: params => ({ term: params.term }),
            processResults: data => ({ results: data })
        },
        placeholder: "Seleccione Fraccionamiento...",
        width: '100%',
        language: "es"
    });

    // Evento: Cuando cambia el Fraccionamiento, cargamos sus lotes
    $('#fraccionamiento_id').on('change', function() {
        const idFraccionamiento = $(this).val();
        if (idFraccionamiento) {
            cargarLotes(idFraccionamiento);
        } else {
            $('#selectLote').empty().trigger('change');
        }
    });

    // 1. Select2 Clientes (AJAX)
    $('#selectCliente').select2({
        ajax: {
            url: '/api/admin/clientes/buscar',
            dataType: 'json',
            delay: 250,
            data: params => ({ q: params.term }),
            processResults: data => ({ 
                results: data.map(c => ({ 
                    id: c.id, 
                    text: `${c.nombre} ${c.apellido} - ${c.documento}` 
                })) 
            })
        },
        placeholder: "Buscar cliente...",
        width: '100%',
        language: "es"
    });

    // 2. Función para cargar Lotes
    function cargarLotes(fraccionamientoId) {
        const sel = $('#selectLote');
        sel.html('<option>Cargando lotes...</option>');
        sel.prop('disabled', true);

        fetch(`/api/admin/fraccionamientos/${fraccionamientoId}/lotes-disponibles`)
        .then(r => r.json())
        .then(data => {
            sel.empty(); 
            sel.append(new Option('-- Seleccionar Lote --', ''));
            
            if (data.length === 0) {
                sel.append(new Option('-- No hay lotes disponibles --', ''));
            }

            data.forEach(l => {
                sel.append(new Option(l.text || l.texto, l.id));
            });
            
            sel.prop('disabled', false);
            sel.select2({ placeholder: "Seleccione un lote...", width: '100%' });
        })
        .catch(err => {
            console.error("Error cargando lotes:", err);
            sel.html('<option>Error al cargar lotes</option>');
            sel.prop('disabled', false);
        });
    }

    // 3. Función para cargar Vendedores
    function cargarVendedores() {
        fetch('/api/inventario/vendedores-activos')
        .then(r => r.json())
        .then(data => {
            const sel = document.getElementById('selectVendedor');
            sel.innerHTML = '<option value="">-- Sin Vendedor (Venta Directa) --</option>';
            data.forEach(v => {
                const opt = document.createElement('option');
                opt.value = v.id;
                opt.textContent = v.nombre_completo || `${v.nombre} ${v.apellido}`;
                sel.appendChild(opt);
            });
        })
        .catch(err => console.error("Error cargando vendedores:", err));
    }

    // 4. Lógica de Planes de Pago
    $('#selectLote').on('change', function() {
        const loteId = $(this).val();
        if(!loteId) {
            document.getElementById('seccion-precios').style.display = 'none';
            return;
        }
        
        fetch(`/api/admin/lotes/${loteId}/precios`)
        .then(r=>r.json())
        .then(precios => {
            const div = document.getElementById('seccion-precios');
            const sel = document.getElementById('selectPrecio');
            sel.innerHTML = '<option value="">-- Personalizado --</option>';
            
            if(precios.length > 0) {
                div.style.display = 'block';
                precios.forEach(p => {
                    const opt = document.createElement('option');
                    opt.value = p.id;
                    opt.textContent = `${p.condicion_pago_nombre || 'Plan'} - ${p.cantidad_cuotas} cuotas de Gs. ${formatMoney(p.precio_cuota)}`;
                    opt.dataset.total = p.precio_total;
                    opt.dataset.cuotas = p.cantidad_cuotas;
                    opt.dataset.valor = p.precio_cuota;
                    sel.appendChild(opt);
                });
            } else {
                div.style.display = 'none';
            }
        });
    });

    // 5. Al elegir plan, rellenar inputs
    document.getElementById('selectPrecio').addEventListener('change', function(e) {
        const opt = e.target.options[e.target.selectedIndex];
        if(opt.value && opt.dataset.total) {
            document.getElementById('valor_total').value = formatMoney(opt.dataset.total);
            document.getElementById('cantidad_cuotas').value = opt.dataset.cuotas;
            document.getElementById('valor_cuota').value = formatMoney(opt.dataset.valor);
        }
    });

    // 6. Calcular Cuota Manualmente
    $('#btnCalcular').on('click', function() {
        calcularCuota();
    });

    function calcularCuota() {
        const total = parseMoney(document.getElementById('valor_total').value);
        const entrega = parseMoney(document.getElementById('cuota_inicial').value);
        const cantidad = parseInt(document.getElementById('cantidad_cuotas').value) || 1;
        
        if (cantidad <= 0) return;

        const saldo = total - entrega;
        const cuota = saldo / cantidad;
        
        document.getElementById('valor_cuota').value = formatMoney(cuota);
    }

    // 7. --- NUEVA FUNCIONALIDAD: GENERAR VISTA PREVIA ---
    $('#btnGenerarVistaPrevia').on('click', function() {
        const cantidad = parseInt($('#cantidad_cuotas').val()) || 0;
        const valorCuota = parseMoney($('#valor_cuota').val());
        
        // Usar fecha de primer vencimiento si existe, sino fecha de contrato
        let fechaInicioStr = $('input[name="fecha_vencimiento_entrega"]').val();
        if (!fechaInicioStr) {
            fechaInicioStr = $('#fecha_contrato').val();
        }
        
        if (cantidad <= 0 || valorCuota <= 0) {
            if(typeof Swal !== 'undefined') Swal.fire('Error', 'Ingrese cantidad de cuotas y valor válido.', 'warning');
            else alert('Ingrese cantidad de cuotas y valor válido.');
            return;
        }
        if (!fechaInicioStr) {
            if(typeof Swal !== 'undefined') Swal.fire('Error', 'Ingrese una fecha de inicio.', 'warning');
            else alert('Ingrese una fecha de inicio.');
            return;
        }

        const tbody = $('#tbodyCuotas');
        tbody.empty();
        cuotasGeneradas = [];

        // Parsear fecha manualmente para evitar problemas de zona horaria
        const parts = fechaInicioStr.split('-');
        // Crear fecha (mes es 0-indexado)
        let fecha = new Date(parts[0], parts[1] - 1, parts[2]);

        for (let i = 1; i <= cantidad; i++) {
            // Formatear fecha para mostrar (dd/mm/yyyy)
            const dia = String(fecha.getDate()).padStart(2, '0');
            const mes = String(fecha.getMonth() + 1).padStart(2, '0');
            const anio = fecha.getFullYear();
            const fechaFmt = `${dia}/${mes}/${anio}`;

            const rowHtml = `
                <tr>
                    <td>${i}</td>
                    <td>${fechaFmt}</td>
                    <td>Gs. ${formatMoney(valorCuota)}</td>
                </tr>
            `;
            tbody.append(rowHtml);

            // Guardar para enviar al backend
            cuotasGeneradas.push({
                numero: i,
                vencimiento: fechaFmt, // Enviamos como string dd/mm/yyyy
                monto: valorCuota
            });

            // Sumar 1 mes para la siguiente cuota
            fecha.setMonth(fecha.getMonth() + 1);
        }

        $('#totalCuotasSum').text(cantidad);
    });

    // 8. Guardar Contrato
    document.getElementById('formNuevoContrato').addEventListener('submit', function(e) {
        e.preventDefault();
        
        const data = {
            numero_contrato: document.getElementsByName('numero_contrato')[0].value,
            fecha_contrato: document.getElementsByName('fecha_contrato')[0].value,
            tipo_contrato: document.getElementsByName('tipo_contrato')[0].value,
            cliente_id: $('#selectCliente').val(),
            lote_id: $('#selectLote').val(),
            vendedor_id: document.getElementById('selectVendedor').value || null,
            
            valor_total: parseMoney(document.getElementById('valor_total').value),
            cuota_inicial: parseMoney(document.getElementById('cuota_inicial').value),
            fecha_vencimiento_entrega: document.getElementsByName('fecha_vencimiento_entrega')[0].value,
            cantidad_cuotas: parseInt(document.getElementById('cantidad_cuotas').value),
            valor_cuota: parseMoney(document.getElementById('valor_cuota').value),
            observaciones: document.getElementsByName('observaciones')[0].value,
            
            doc_modelo_contrato: document.getElementsByName('doc_modelo_contrato')[0].value,
            doc_identidad: document.getElementsByName('doc_identidad')[0].value,
            doc_factura_servicios: document.getElementsByName('doc_factura_servicios')[0].value,
            doc_ingresos: document.getElementsByName('doc_ingresos')[0].value,
            
            uso: document.getElementsByName('uso')[0].value,
            moneda: document.getElementsByName('moneda')[0].value,
            medida_tiempo: document.getElementsByName('medida_tiempo')[0].value,
            
            // Adjuntamos las cuotas generadas en el paso anterior
            cuotas_generadas: cuotasGeneradas
        };

        if(!data.cliente_id || !data.lote_id) return Swal.fire('Atención', 'Complete Cliente y Lote', 'warning');
        if(!data.numero_contrato) return Swal.fire('Atención', 'Ingrese el Número de Contrato', 'warning');

        const btn = document.getElementById('btnGuardar');
        const originalText = btn.innerHTML;
        btn.disabled = true;
        btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Guardando...';

        fetch('/api/admin/contratos', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(data)
        })
        .then(r => r.json())
        .then(res => {
            if(res.ok) {
                Swal.fire('¡Creado!', 'Contrato registrado exitosamente', 'success').then(() => {
                    window.location.href = "/admin/inventario/movimientos";
                });
            } else {
                Swal.fire('Error', res.error, 'error');
                btn.disabled = false;
                btn.innerHTML = originalText;
            }
        })
        .catch(err => {
            console.error(err);
            Swal.fire('Error', 'Fallo de conexión', 'error');
            btn.disabled = false;
            btn.innerHTML = originalText;
        });
    });

    // Formateo visual al escribir en campos de dinero
    $('.input-money').on('change', function() {
        let val = parseMoney($(this).val());
        $(this).val(formatMoney(val));
    });
});