document.addEventListener('DOMContentLoaded', function () {
    // === LÓGICA DE MENÚ LATERAL (Submenús) ===
    const menuItems = document.querySelectorAll('.has-submenu > .nav-link');
    menuItems.forEach(item => {
        item.addEventListener('click', function (e) {
            e.preventDefault();
            const parent = this.parentElement;
            parent.classList.toggle('active');
        });
    });

    // === LÓGICA PARA PESTAÑAS PERSONALIZADAS (Clase .tab-link) ===
    // Esto solo afecta a Gastos y Tesorería (Definiciones)
    const tabLinks = document.querySelectorAll('.tab-link');
    const tabContents = document.querySelectorAll('.tab-content');

    if (tabLinks.length > 0) {
        // Ocultar todos los contenidos que no sean de bootstrap
        tabContents.forEach(content => {
            if (!content.classList.contains('tab-pane')) {
                 content.style.display = 'none';
            }
        });

        tabLinks.forEach(link => {
            link.addEventListener('click', (e) => {
                const tabId = link.dataset.tab;
                if (!tabId) {
                    return;
                }
                
                e.preventDefault();

                // Ocultar todos los contenidos (que no sean de bootstrap)
                tabContents.forEach(content => {
                    if (!content.classList.contains('tab-pane')) {
                        content.style.display = 'none';
                    }
                });
                // Quitar clase activa de todos los links
                tabLinks.forEach(l => {
                    l.classList.remove('active');
                });

                // Mostrar el contenido seleccionado
                const activeTab = document.getElementById(tabId);
                if (activeTab) {
                    activeTab.style.display = 'block';
                }
                // Añadir clase activa al link
                link.classList.add('active');
            });
        });

        // Activar la primera pestaña por defecto (si existe y no es de bootstrap)
        const firstTabLink = document.querySelector('.tab-link');
        if (firstTabLink && firstTabLink.dataset.tab && !firstTabLink.classList.contains('active')) {
             firstTabLink.click();
        } else if (firstTabLink && firstTabLink.classList.contains('active')) {
            // Asegurar que la activa se muestre
            const activeId = firstTabLink.dataset.tab;
            if(activeId) {
                const activeContent = document.getElementById(activeId);
                if(activeContent) activeContent.style.display = 'block';
            }
        }
    }
});

// --- FUNCIONES GLOBALES PARA MANEJAR MODALES (LEGACY) ---
// Se asignan a window para que funcionen con onclick="..."
window.abrirModal = function(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) modal.style.display = 'block';
}

window.cerrarModal = function(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) modal.style.display = 'none';
}

// Cierra el modal si se hace clic en la 'X'
window.addEventListener('click', function(event) {
    if (event.target.classList.contains('close')) {
        const modal = event.target.closest('.modal:not(.fade)');
        if(modal) {
            cerrarModal(modal.id);
        }
    }
});