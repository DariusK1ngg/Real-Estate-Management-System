document.addEventListener('DOMContentLoaded', function () {
    // === SEGURIDAD: CONFIGURACIÓN CSRF GLOBAL ===
    const csrfToken = document.querySelector('meta[name="csrf-token"]').getAttribute('content');

    // Interceptor para inyectar el token CSRF en todas las peticiones fetch que no sean GET
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

    // === LÓGICA DE MENÚ LATERAL (Submenús) ===
    const menuItems = document.querySelectorAll('.has-submenu > .nav-link');
    menuItems.forEach(item => {
        item.addEventListener('click', function (e) {
            e.preventDefault();
            const parent = this.parentElement;
            parent.classList.toggle('active');
        });
    });

    // === LÓGICA PARA PESTAÑAS PERSONALIZADAS ===
    const tabLinks = document.querySelectorAll('.tab-link');
    const tabContents = document.querySelectorAll('.tab-content');

    if (tabLinks.length > 0) {
        tabContents.forEach(content => {
            if (!content.classList.contains('tab-pane')) {
                 content.style.display = 'none';
            }
        });

        tabLinks.forEach(link => {
            link.addEventListener('click', (e) => {
                const tabId = link.dataset.tab;
                if (!tabId) return;
                
                e.preventDefault();

                tabContents.forEach(content => {
                    if (!content.classList.contains('tab-pane')) {
                        content.style.display = 'none';
                    }
                });
                tabLinks.forEach(l => l.classList.remove('active'));

                const activeTab = document.getElementById(tabId);
                if (activeTab) activeTab.style.display = 'block';
                
                link.classList.add('active');
            });
        });

        const firstTabLink = document.querySelector('.tab-link');
        if (firstTabLink && firstTabLink.dataset.tab && !firstTabLink.classList.contains('active')) {
             firstTabLink.click();
        }
    }
});

// --- FUNCIONES GLOBALES PARA MANEJAR MODALES ---
window.abrirModal = function(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) modal.style.display = 'block';
}

window.cerrarModal = function(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) modal.style.display = 'none';
}

window.addEventListener('click', function(event) {
    if (event.target.classList.contains('close')) {
        const modal = event.target.closest('.modal:not(.fade)');
        if(modal) cerrarModal(modal.id);
    }
});