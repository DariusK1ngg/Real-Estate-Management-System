/* static/js/main.js */

const formateadorPYG = new Intl.NumberFormat('es-PY');

document.addEventListener('DOMContentLoaded', function () {
    
    // === 1. AUTO-FORMATO DE MONEDA ===
    document.body.addEventListener('input', function(e) {
        if (e.target.classList.contains('input-money')) {
            let cursorPosition = e.target.selectionStart;
            let originalLength = e.target.value.length;
            let rawValue = e.target.value.replace(/\D/g, '');
            if (rawValue === '') { e.target.value = ''; return; }
            let formattedValue = new Intl.NumberFormat('es-PY').format(rawValue);
            e.target.value = formattedValue;
            let newLength = formattedValue.length;
            cursorPosition = cursorPosition + (newLength - originalLength);
            try { e.target.setSelectionRange(cursorPosition, cursorPosition); } catch(err) {}
        }
    });

    // === 2. SWEETALERT GLOBAL ===
    if (typeof Swal !== 'undefined') {
        window.Toast = Swal.mixin({
            toast: true, position: 'top-end', showConfirmButton: false, timer: 3000, timerProgressBar: true,
            didOpen: (toast) => {
                toast.addEventListener('mouseenter', Swal.stopTimer);
                toast.addEventListener('mouseleave', Swal.resumeTimer);
            }
        });
    }

    // === 3. MENÚ LATERAL ===
    const menuItems = document.querySelectorAll('.has-submenu > .nav-link');
    menuItems.forEach(item => {
        item.addEventListener('click', function (e) {
            e.preventDefault();
            const parent = this.parentElement;
            parent.classList.toggle('active');
        });
    });

    // === 4. DATATABLES AUTOMÁTICO (FILTROS Y BÚSQUEDA EN TABLAS) ===
    // Si existe jQuery y DataTables, convierte todas las tablas en tablas inteligentes
    if ($.fn.DataTable) {
        $('.table').each(function() {
            // Evitamos reinicializar si ya es DataTable o si tiene clase 'no-datatable'
            if (!$.fn.DataTable.isDataTable(this) && !$(this).hasClass('no-datatable')) {
                $(this).DataTable({
                    language: {
                        url: '//cdn.datatables.net/plug-ins/1.13.6/i18n/es-ES.json'
                    },
                    responsive: true,
                    pageLength: 10,
                    order: [] // No ordenar por defecto la primera columna
                });
            }
        });
    }

    // === 5. BUSCADOR GLOBAL ===
    const searchInput = document.getElementById('globalSearchInput');
    const searchResults = document.getElementById('globalSearchResults');
    let searchTimeout = null;

    if (searchInput && searchResults) {
        searchInput.addEventListener('input', function(e) {
            const query = e.target.value.trim();
            clearTimeout(searchTimeout);
            
            if (query.length < 2) {
                searchResults.style.display = 'none';
                return;
            }

            searchTimeout = setTimeout(() => {
                fetch(`/api/global-search?q=${encodeURIComponent(query)}`)
                    .then(r => r.json())
                    .then(data => {
                        searchResults.innerHTML = '';
                        if (data.length === 0) {
                            searchResults.innerHTML = '<div class="p-3 text-muted text-center">No se encontraron resultados</div>';
                        } else {
                            data.forEach(item => {
                                const div = document.createElement('div');
                                div.className = 'search-result-item p-2 border-bottom';
                                div.style.cursor = 'pointer';
                                div.innerHTML = `
                                    <div class="d-flex align-items-center">
                                        <div class="me-3 text-primary"><i class="${item.icon}"></i></div>
                                        <div>
                                            <div class="fw-bold">${item.title}</div>
                                            <div class="small text-muted">${item.subtitle}</div>
                                            <div class="x-small text-uppercase text-secondary" style="font-size:0.7em">${item.category}</div>
                                        </div>
                                    </div>
                                `;
                                div.onclick = () => { window.location.href = item.url; };
                                searchResults.appendChild(div);
                            });
                        }
                        searchResults.style.display = 'block';
                    });
            }, 300);
        });

        // Cerrar al hacer clic fuera
        document.addEventListener('click', function(e) {
            if (!searchInput.contains(e.target) && !searchResults.contains(e.target)) {
                searchResults.style.display = 'none';
            }
        });
    }

    // === 6. SEGURIDAD CSRF ===
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

// === UTILIDADES GLOBALES ===
window.parseMoney = function(str) {
    if (!str) return 0;
    return parseInt(str.toString().replace(/\./g, '')) || 0;
};

window.formatMoney = function(num) {
    return new Intl.NumberFormat('es-PY').format(num);
};