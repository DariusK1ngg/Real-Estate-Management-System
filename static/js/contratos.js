document.addEventListener('DOMContentLoaded', function () {
    inicializarSelectCliente();
    inicializarSelectLote();

    const formContrato = document.getElementById('formContrato');
    
    // Listener para cambio de lote -> cargar planes
    $('#lote_id').on('select2:select', function (e) {
        const loteId = e.params.data.id;
        cargarPlanesPago(loteId);
    });

    formContrato.addEventListener('submit', function (event) {
        event.preventDefault();
        guardarContrato();
    });
});

function inicializarSelectCliente() {
    $('#cliente_id').select2({
        placeholder: 'Buscar por nombre, apellido o documento',
        minimumInputLength: 2,
        ajax: {
            url: '/api/admin/clientes/buscar',
            dataType: 'json',
            delay: 250,
            data: function (params) {
                return { q: params.term };
            },
            processResults: function (data) {
                return {
                    results: data.map(cliente => ({
                        id: cliente.id,
                        text: `${cliente.nombre} ${cliente.apellido} (${cliente.documento})`
                    }))
                };
            },
            cache: true
        }
    });
}

function inicializarSelectLote() {
    // Cargar lotes disponibles en el select
    $.ajax({
        url: '/api/admin/lotes-disponibles',
        dataType: 'json'
    }).then(function (data) {
        var options = '<option value="">Seleccione un lote</option>';
        data.forEach(function (lote) {
            options += `<option value="${lote.id}" data-precio="${lote.precio}">${lote.texto}</option>`;
        });
        $('#lote_id').html(options).select2({ placeholder: "Seleccione un lote" });
    });
}

async function cargarPlanesPago(loteId) {
    const selectPlan = document.getElementById('plan_pago_id');
    selectPlan.innerHTML = '<option value="">Cargando...</option>';
    
    try {
        const response = await fetch(`/api/admin/lotes/${loteId}/precios`);
        const planes = await response.json();
        
        selectPlan.innerHTML = '<option value="">-- Seleccione un Plan de Pago --</option>';
        
        if (planes.length === 0) {
            // Opción de precio contado por defecto si no hay planes
            selectPlan.innerHTML += `<option value="custom">Precio Manual / Personalizado</option>`;
        } else {
            planes.forEach(p => {
                const texto = `${p.condicion_pago_nombre} - ${p.cantidad_cuotas} cuotas de Gs. ${p.precio_cuota.toLocaleString('es-PY')} (Total: Gs. ${p.precio_total.toLocaleString('es-PY')})`;
                const option = document.createElement('option');
                option.value = p.id;
                option.text = texto;
                // Guardamos datos en el dataset para usarlos al seleccionar
                option.dataset.total = p.precio_total;
                option.dataset.cuotas = p.cantidad_cuotas;
                option.dataset.cuotaValor = p.precio_cuota;
                selectPlan.appendChild(option);
            });
            selectPlan.innerHTML += `<option value="custom">Otro / Personalizado</option>`;
        }
    } catch (e) {
        console.error(e);
        selectPlan.innerHTML = '<option value="">Error al cargar planes</option>';
    }
}

// Evento al seleccionar un plan
document.getElementById('plan_pago_id').addEventListener('change', function(e) {
    const selectedOption = e.target.options[e.target.selectedIndex];
    const val = selectedOption.value;
    
    const inputTotal = document.getElementById('valor_total');
    const inputCuotas = document.getElementById('cantidad_cuotas');
    const inputValorCuota = document.getElementById('valor_cuota');
    
    if (val && val !== 'custom') {
        // Rellenar automáticamente y bloquear
        inputTotal.value = selectedOption.dataset.total;
        inputCuotas.value = selectedOption.dataset.cuotas;
        inputValorCuota.value = selectedOption.dataset.cuotaValor;
        
        inputTotal.readOnly = true;
        inputCuotas.readOnly = true;
    } else {
        // Permitir edición manual
        inputTotal.readOnly = false;
        inputCuotas.readOnly = false;
        inputTotal.value = '';
        inputCuotas.value = '';
        inputValorCuota.value = '';
    }
});

// Calcular valor cuota si es manual
document.getElementById('valor_total').addEventListener('input', calcularManual);
document.getElementById('cantidad_cuotas').addEventListener('input', calcularManual);

function calcularManual() {
    const total = parseFloat(document.getElementById('valor_total').value) || 0;
    const cuotas = parseInt(document.getElementById('cantidad_cuotas').value) || 0;
    if(total > 0 && cuotas > 0) {
        document.getElementById('valor_cuota').value = (total / cuotas).toFixed(2);
    }
}

async function guardarContrato() {
    const form = document.getElementById('formContrato');
    const formData = new FormData(form);
    const data = Object.fromEntries(formData.entries());

    // Datos numéricos
    data.valor_total = parseFloat(data.valor_total);
    data.cuota_inicial = parseFloat(data.cuota_inicial);
    data.cantidad_cuotas = parseInt(data.cantidad_cuotas);
    data.valor_cuota = parseFloat(data.valor_cuota);
    
    // Enviar ID de precio si se seleccionó uno
    const planId = document.getElementById('plan_pago_id').value;
    if (planId && planId !== 'custom') {
        data.precio_id = parseInt(planId);
    }

    const response = await fetch('/api/admin/contratos', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data)
    });

    if (response.ok) {
        alert('Contrato guardado exitosamente');
        window.location.href = '/admin/ventas/movimientos';
    } else {
        const error = await response.json();
        alert(`Error al guardar el contrato: ${error.error}`);
    }
}