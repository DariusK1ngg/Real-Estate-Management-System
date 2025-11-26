/* static/js/inventario_contrato_nuevo.js */

$(document).ready(function() {
    
    // 1. Select2 Clientes
    $('#selectCliente').select2({
        ajax: {
            url: '/api/admin/clientes/buscar',
            dataType: 'json',
            delay: 250,
            data: params => ({ q: params.term }),
            processResults: data => ({ results: data.map(c => ({ id: c.id, text: `${c.nombre} ${c.apellido} - ${c.documento}` })) })
        },
        placeholder: "Buscar cliente...",
        width: '100%'
    });

    // 2. Cargar Lotes
    fetch('/api/admin/lotes-disponibles')
    .then(r => r.json())
    .then(data => {
        const sel = $('#selectLote');
        sel.append(new Option('-- Seleccionar Lote --', ''));
        data.forEach(l => {
            sel.append(new Option(l.texto, l.id));
        });
        sel.select2({ placeholder: "Seleccione un lote...", width: '100%' });
    });

    // 3. Lógica de Planes de Pago (Predefinidos)
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
                    // Guardamos valores crudos
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

    // 4. Al elegir plan, rellenar inputs con formato visual
    document.getElementById('selectPrecio').addEventListener('change', function(e) {
        const opt = e.target.options[e.target.selectedIndex];
        if(opt.value && opt.dataset.total) {
            document.getElementById('valor_total').value = formatMoney(opt.dataset.total);
            document.getElementById('cantidad_cuotas').value = opt.dataset.cuotas;
            document.getElementById('valor_cuota').value = formatMoney(opt.dataset.valor);
        }
    });

    // 5. Guardar Contrato (Limpiando los puntos)
    document.getElementById('formNuevoContrato').addEventListener('submit', function(e) {
        e.preventDefault();
        
        const data = {
            numero_contrato: document.getElementsByName('numero_contrato')[0].value,
            fecha_contrato: document.getElementsByName('fecha_contrato')[0].value,
            tipo_contrato: document.getElementsByName('tipo_contrato')[0].value,
            cliente_id: $('#selectCliente').val(),
            lote_id: $('#selectLote').val(),
            // USAMOS parseMoney PARA LIMPIAR PUNTOS
            valor_total: parseMoney(document.getElementById('valor_total').value),
            cuota_inicial: parseMoney(document.getElementsByName('cuota_inicial')[0].value),
            cantidad_cuotas: parseInt(document.getElementById('cantidad_cuotas').value),
            valor_cuota: parseMoney(document.getElementById('valor_cuota').value),
            observaciones: document.getElementsByName('observaciones')[0].value
        };

        if(!data.cliente_id || !data.lote_id) return Swal.fire('Atención', 'Complete Cliente y Lote', 'warning');

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
            }
        })
        .catch(err => Swal.fire('Error', 'Fallo de conexión', 'error'));
    });
});