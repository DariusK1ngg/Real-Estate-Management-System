/* static/js/inventario_contrato_nuevo.js */

// Funciones auxiliares de formateo (si no están en base_module.js)
function formatMoney(amount) {
    if (!amount) return '0';
    return new Intl.NumberFormat('es-PY').format(amount);
}

function parseMoney(str) {
    if (!str) return 0;
    // Elimina puntos de mil y reemplaza coma decimal por punto (si aplica)
    return parseFloat(str.toString().replace(/\./g, '').replace(',', '.'));
}

$(document).ready(function() {
    
    // --- INICIALIZACIÓN ---
    cargarVendedores(); // <--- NUEVA LLAMADA
    cargarLotes();      // Refactorizado abajo

    // 1. Select2 Clientes (AJAX)
    $('#selectCliente').select2({
        ajax: {
            url: '/api/admin/clientes/buscar', // Asegúrate que esta ruta exista en ventas.py o search.py
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

    // 2. Función para cargar Lotes Disponibles
    function cargarLotes() {
        fetch('/api/admin/lotes-disponibles') // Ruta en inventario.py
        .then(r => r.json())
        .then(data => {
            const sel = $('#selectLote');
            sel.empty(); // Limpiar antes de llenar
            sel.append(new Option('-- Seleccionar Lote --', ''));
            
            data.forEach(l => {
                // l.texto viene del backend formateado
                sel.append(new Option(l.texto, l.id));
            });
            
            // Inicializar Select2 en el lote también
            sel.select2({ placeholder: "Seleccione un lote...", width: '100%' });
        })
        .catch(err => console.error("Error cargando lotes:", err));
    }

    // 3. Función NUEVA para cargar Vendedores
    function cargarVendedores() {
        fetch('/api/inventario/vendedores-activos') // La ruta nueva que creaste
        .then(r => r.json())
        .then(data => {
            const sel = document.getElementById('selectVendedor');
            // Mantenemos la primera opción por defecto
            sel.innerHTML = '<option value="">-- Sin Vendedor (Venta Directa) --</option>';
            
            data.forEach(v => {
                const opt = document.createElement('option');
                opt.value = v.id;
                // v.nombre_completo o armarlo manual
                opt.textContent = v.nombre_completo || `${v.nombre} ${v.apellido}`;
                sel.appendChild(opt);
            });
        })
        .catch(err => console.error("Error cargando vendedores:", err));
    }

    // 4. Lógica de Planes de Pago (Predefinidos) al seleccionar Lote
    $('#selectLote').on('change', function() {
        const loteId = $(this).val();
        if(!loteId) return;
        
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
                    // Mostramos precio formateado en el texto
                    opt.textContent = `${p.condicion_pago_nombre} - ${p.cantidad_cuotas} cuotas de Gs. ${formatMoney(p.precio_cuota)}`;
                    // Guardamos valores crudos en dataset para usarlos después
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

    // 5. Al elegir plan, rellenar inputs automáticamente
    document.getElementById('selectPrecio').addEventListener('change', function(e) {
        const opt = e.target.options[e.target.selectedIndex];
        if(opt.value && opt.dataset.total) {
            document.getElementById('valor_total').value = formatMoney(opt.dataset.total);
            document.getElementById('cantidad_cuotas').value = opt.dataset.cuotas;
            document.getElementById('valor_cuota').value = formatMoney(opt.dataset.valor);
        }
    });

    // 6. Calcular Cuota Manualmente (Botón Calcular)
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

    // 7. Guardar Contrato (Submit)
    document.getElementById('formNuevoContrato').addEventListener('submit', function(e) {
        e.preventDefault();
        
        // Obtenemos los valores
        const data = {
            numero_contrato: document.getElementsByName('numero_contrato')[0].value,
            fecha_contrato: document.getElementsByName('fecha_contrato')[0].value,
            tipo_contrato: document.getElementsByName('tipo_contrato')[0].value,
            cliente_id: $('#selectCliente').val(),
            lote_id: $('#selectLote').val(),
            // AQUI SE AGREGA EL VENDEDOR
            vendedor_id: document.getElementById('selectVendedor').value || null,
            
            valor_total: parseMoney(document.getElementById('valor_total').value),
            cuota_inicial: parseMoney(document.getElementById('cuota_inicial').value),
            fecha_vencimiento_entrega: document.getElementsByName('fecha_vencimiento_entrega')[0].value,
            cantidad_cuotas: parseInt(document.getElementById('cantidad_cuotas').value),
            valor_cuota: parseMoney(document.getElementById('valor_cuota').value),
            observaciones: document.getElementsByName('observaciones')[0].value,
            
            // Campos extras de documentación
            doc_modelo_contrato: document.getElementsByName('doc_modelo_contrato')[0].value,
            doc_identidad: document.getElementsByName('doc_identidad')[0].value,
            doc_factura_servicios: document.getElementsByName('doc_factura_servicios')[0].value,
            doc_ingresos: document.getElementsByName('doc_ingresos')[0].value,
            
            uso: document.getElementsByName('uso')[0].value,
            moneda: document.getElementsByName('moneda')[0].value,
            medida_tiempo: document.getElementsByName('medida_tiempo')[0].value
        };

        if(!data.cliente_id || !data.lote_id) return Swal.fire('Atención', 'Complete Cliente y Lote', 'warning');
        if(!data.numero_contrato) return Swal.fire('Atención', 'Ingrese el Número de Contrato', 'warning');

        // Botón loading
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
    $('.input-money').on('input', function() {
        // Esta es una implementación simple, podrías usar una librería como AutoNumeric
        // Aquí solo permitimos números y formateamos al perder el foco para no molestar al usuario
    });
    
    $('.input-money').on('change', function() {
        let val = parseMoney($(this).val());
        $(this).val(formatMoney(val));
    });
});