/* static/js/main.js */

document.addEventListener('DOMContentLoaded', function () {
    
    // === 1. AUTO-FORMATO DE MONEDA (UX MEJORADA) ===
    // Detecta cualquier input con la clase 'input-money' y le pone puntos de miles al escribir
    document.body.addEventListener('input', function(e) {
        if (e.target.classList.contains('input-money')) {
            // 1. Guardar posición del cursor para no saltar al final
            let cursorPosition = e.target.selectionStart;
            let originalLength = e.target.value.length;

            // 2. Limpiar todo lo que no sea número
            let rawValue = e.target.value.replace(/\D/g, '');
            
            if (rawValue === '') {
                e.target.value = '';
                return;
            }

            // 3. Formatear con puntos (Estándar Paraguay)
            let formattedValue = new Intl.NumberFormat('es-PY').format(rawValue);
            e.target.value = formattedValue;

            // 4. Restaurar cursor (Ajuste fino para comodidad al borrar)
            let newLength = formattedValue.length;
            cursorPosition = cursorPosition + (newLength - originalLength);
            try {
                e.target.setSelectionRange(cursorPosition, cursorPosition);
            } catch(err) {} // Ignorar en inputs type="number" (aunque usaremos text)
        }
    });

    // === 2. CONFIGURACIÓN GLOBAL DE TOASTS (ALERTAS PEQUEÑAS) ===
    if (typeof Swal !== 'undefined') {
        window.Toast = Swal.mixin({
            toast: true,
            position: 'top-end',
            showConfirmButton: false,
            timer: 3000,
            timerProgressBar: true,
            didOpen: (toast) => {
                toast.addEventListener('mouseenter', Swal.stopTimer);
                toast.addEventListener('mouseleave', Swal.resumeTimer);
            }
        });
    }

    // === 3. LÓGICA DE MENÚ LATERAL ===
    const menuItems = document.querySelectorAll('.has-submenu > .nav-link');
    menuItems.forEach(item => {
        item.addEventListener('click', function (e) {
            e.preventDefault();
            const parent = this.parentElement;
            parent.classList.toggle('active');
        });
    });

    // === 4. SEGURIDAD CSRF GLOBAL ===
    const csrfTokenMeta = document.querySelector('meta[name="csrf-token"]');
    if (csrfTokenMeta) {
        const csrfToken = csrfTokenMeta.getAttribute('content');
        const originalFetch = window.fetch;
        window.fetch = function(url, options = {}) {
            if (options.method && options.method.toUpperCase() !== 'GET') {
                options.headers = options.headers || {};
                if (options.headers instanceof Headers) {
                    options.headers.append('X-CSRFToken', csrfToken);
                } else {
                    options.headers['X-CSRFToken'] = csrfToken;
                }
            }
            return originalFetch(url, options);
        };
    }
});

// === UTILIDADES GLOBALES PARA TODO EL SISTEMA ===

// Convierte "1.500.000" -> 1500000 (Para enviar al Backend)
window.parseMoney = function(str) {
    if (!str) return 0;
    return parseInt(str.toString().replace(/\./g, '')) || 0;
};

// Convierte 1500000 -> "1.500.000" (Para mostrar en Inputs)
window.formatMoney = function(num) {
    return new Intl.NumberFormat('es-PY').format(num);
};