// ======== TOGGLE SECCIONES PANEL ========

fetch('/api/admin/ciudades')
    .then(r => r.json())
    .then(data => {
        const sel = document.getElementById('frac-ciudad');
        if(sel) {
            data.forEach(c => {
                const opt = document.createElement('option');
                opt.value = c.id;
                opt.textContent = c.nombre;
                sel.appendChild(opt);
            });
        }
    });

document.addEventListener('DOMContentLoaded', function() {
    // Referencias a los elementos
    const btnFraccionamientos = document.getElementById('btn-show-fraccionamientos');
    const btnLotes = document.getElementById('btn-show-lotes');
    const seccionFraccionamientos = document.getElementById('seccion-fraccionamientos');
    const seccionLotes = document.getElementById('seccion-lotes');
    
    // Función para mostrar una sección y ocultar las demás
    function mostrarSeccion(seccionMostrar, botonActivo) {
        // Ocultar todas las secciones
        seccionFraccionamientos.classList.remove('seccion-activa');
        seccionFraccionamientos.classList.add('seccion-oculta');
        seccionLotes.classList.remove('seccion-activa');
        seccionLotes.classList.add('seccion-oculta');
        
        // Quitar clase active de todos los botones
        btnFraccionamientos.classList.remove('active');
        btnLotes.classList.remove('active');
        
        // Mostrar la sección seleccionada y activar el botón
        seccionMostrar.classList.remove('seccion-oculta');
        seccionMostrar.classList.add('seccion-activa');
        botonActivo.classList.add('active');
    }
    
    // Event listeners para los botones
    btnFraccionamientos.addEventListener('click', function() {
        mostrarSeccion(seccionFraccionamientos, btnFraccionamientos);
    });
    
    btnLotes.addEventListener('click', function() {
        mostrarSeccion(seccionLotes, btnLotes);
    });
    
    // Por defecto mostrar fraccionamientos
    mostrarSeccion(seccionFraccionamientos, btnFraccionamientos);
});

// Mapa
const map = L.map('map').setView([-25.304, -57.635], 15);
L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: '&copy; OpenStreetMap contributors'
}).addTo(map);

// Leyenda bottom-right
const legend = L.control({position: "bottomright"});
legend.onAdd = function () {
    const div = L.DomUtil.create("div", "legend");
    div.innerHTML = `
        <div class="row"><span class="sw" style="background:#2ECC71"></span>Disponible</div>
        <div class="row"><span class="sw" style="background:#F1C40F"></span>Reservado</div>
        <div class="row"><span class="sw" style="background:#E74C3C"></span>Vendido</div>
    `;
    return div;
};
legend.addTo(map);

function styleByEstado(e) {
    if (e === "disponible") return { color:"#2ECC71", weight:2, fillOpacity:0.25, fillColor:"#2ECC71" };
    if (e === "reservado")  return { color:"#F1C40F", weight:2, fillOpacity:0.25, fillColor:"#F1C40F" };
    return { color:"#E74C3C",  weight:2, fillOpacity:0.25, fillColor:"#E74C3C" };
}

// Grupos/capas
const fracDrawn = new L.FeatureGroup();
const lotesEditable = new L.FeatureGroup();
map.addLayer(fracDrawn);
map.addLayer(lotesEditable);

// Controles de dibujo
const drawControl = new L.Control.Draw({
    edit: { featureGroup: lotesEditable, remove: false },
    draw: {
        polygon: { allowIntersection: false, showArea: true, shapeOptions: { color: '#2e7dff' } },
        rectangle: { shapeOptions: { color: '#2e7dff' } },
        circle: false, marker: false, polyline: false, circlemarker: false
    }
});
map.addControl(drawControl);

// Estados
let currentDraftLote = null;
let selectedLoteLayer = null;
let fracsLayer = null;
let lotesLayer = null;
let currentFracDraft = null;
let fracForFilter = null;
let allFracsData = []; // Variable para guardar los datos de los fraccionamientos

// ======== FUNCIONALIDAD MOVER LOTES ========
let moveMarker = null;
let isDragging = false;

function addMoveMarker(layer) {
    if (moveMarker) {
        map.removeLayer(moveMarker);
    }
    
    const center = layer.getBounds().getCenter();
    moveMarker = L.marker(center, {
        icon: L.divIcon({
            className: 'move-marker',
            html: '<div style="background:#2980b9; width:12px; height:12px; border:2px solid white; border-radius:2px; box-shadow:0 0 5px rgba(0,0,0,0.5);"></div>',
            iconSize: [16, 16],
            iconAnchor: [8, 8]
        }),
        draggable: true,
        zIndexOffset: 1000
    }).addTo(map);
    
    // Evento para arrastrar el marcador
    moveMarker.on('dragstart', function() {
        isDragging = true;
    });
    
    moveMarker.on('drag', function() {
        if (selectedLoteLayer && isDragging) {
            const newCenter = moveMarker.getLatLng();
            const oldCenter = selectedLoteLayer.getBounds().getCenter();
            
            const offsetLng = newCenter.lng - oldCenter.lng;
            const offsetLat = newCenter.lat - oldCenter.lat;
            
            moveLote(offsetLng, offsetLat);
        }
    });
    
    moveMarker.on('dragend', function() {
        isDragging = false;
    });
}

function moveLote(offsetLng, offsetLat) {
    if (!selectedLoteLayer) return;
    
    // Obtener la geometría actual
    const currentGeojson = selectedLoteLayer.toGeoJSON().geometry;
    
    // Función para trasladar coordenadas
    function translateCoords(coords) {
        if (Array.isArray(coords[0])) {
            return coords.map(inner => translateCoords(inner));
        } else {
            return [coords[0] + offsetLng, coords[1] + offsetLat];
        }
    }
    
    // Aplicar la traslación
    const translatedGeojson = JSON.parse(JSON.stringify(currentGeojson));
    translatedGeojson.coordinates = translateCoords(translatedGeojson.coordinates);
    
    // Remover el layer actual
    if (lotesEditable.hasLayer(selectedLoteLayer)) {
        lotesEditable.removeLayer(selectedLoteLayer);
    }
    if (lotesLayer && lotesLayer.hasLayer(selectedLoteLayer)) {
        lotesLayer.removeLayer(selectedLoteLayer);
    }
    
    // Crear nuevo layer con la geometría trasladada
    const newLayer = L.geoJSON(translatedGeojson, {
        style: styleByEstado(selectedLoteLayer._props.estado)
    }).getLayers()[0];
    
    // Mantener las propiedades
    newLayer._loteId = selectedLoteLayer._loteId;
    newLayer._props = selectedLoteLayer._props;
    
    // Añadir bindings y eventos
    newLayer.bindPopup(selectedLoteLayer.getPopup().getContent());
    newLayer.on('click', function(e) {
        e.originalEvent.__selected = true;
        
        if (selectedLoteLayer && selectedLoteLayer !== newLayer) {
            try { selectedLoteLayer.setStyle(styleByEstado(selectedLoteLayer._props.estado)); } catch(e){}
        }
        selectedLoteLayer = newLayer;
        newLayer.setStyle({ weight: 4, color: '#2e7dff' });
        
        if (!lotesEditable.hasLayer(newLayer)) lotesEditable.addLayer(newLayer);
        
        // Añadir marcador de movimiento
        addMoveMarker(newLayer);
    });
    
    // Añadir a los grupos
    lotesEditable.addLayer(newLayer);
    if (lotesLayer) lotesLayer.addLayer(newLayer);
    
    // Actualizar referencia
    selectedLoteLayer = newLayer;
    
    // Actualizar posición del marcador
    if (moveMarker) {
        const newCenter = newLayer.getBounds().getCenter();
        moveMarker.setLatLng(newCenter);
    }
}

// Evento de teclado para mover con flechas
document.addEventListener('keydown', function(e) {
    if (!selectedLoteLayer) return;
    
    let offsetLng = 0;
    let offsetLat = 0;
    const step = e.shiftKey ? 0.0001 : 0.00001; // Paso más grande con Shift
    
    switch(e.key) {
        case 'ArrowUp':
            offsetLat = step;
            break;
        case 'ArrowDown':
            offsetLat = -step;
            break;
        case 'ArrowLeft':
            offsetLng = -step;
            break;
        case 'ArrowRight':
            offsetLng = step;
            break;
        default:
            return; // No hacer nada para otras teclas
    }
    
    if (offsetLng !== 0 || offsetLat !== 0) {
        e.preventDefault();
        moveLote(offsetLng, offsetLat);
    }
});

// ======== FUNCIONALIDAD COPIAR/ PEGAR LOTES ========

let copiedLote = null;
let isPasting = false;
let originalCursor = '';

function copyLote() {
    if (!selectedLoteLayer || !selectedLoteLayer._loteId) {
        return false;
    }
    
    // Obtener la geometría exacta del lote seleccionado
    const geojson = selectedLoteLayer.toGeoJSON().geometry;
    
    copiedLote = {
        numero_lote: selectedLoteLayer._props.numero_lote,
        manzana: selectedLoteLayer._props.manzana,
        precio: selectedLoteLayer._props.precio,
        metros_cuadrados: selectedLoteLayer._props.metros_cuadrados,
        estado: selectedLoteLayer._props.estado,
        fraccionamiento_id: selectedLoteLayer._props.fraccionamiento_id,
        geojson: geojson, // Guardar la geometría exacta
        bounds: selectedLoteLayer.getBounds(),
        // Guardar el tipo de geometría para recrearla correctamente
        layerType: selectedLoteLayer instanceof L.Polygon ? 'polygon' : 
                   selectedLoteLayer instanceof L.Rectangle ? 'rectangle' : 'unknown'
    };
    
    // Feedback visual
    if (selectedLoteLayer) {
        selectedLoteLayer.setStyle({ weight: 6, color: '#00ff00' });
        setTimeout(() => {
            if (selectedLoteLayer) {
                selectedLoteLayer.setStyle(styleByEstado(selectedLoteLayer._props.estado));
            }
        }, 300);
    }
    
    return true;
}

function startPasteMode() {
    if (!copiedLote) {
        return false;
    }
    
    isPasting = true;
    originalCursor = map.getContainer().style.cursor;
    map.getContainer().style.cursor = 'crosshair';
    
    map._container.classList.add('pasting-mode');
    
    map.once('click', handleMapClickForPaste);
    
    const cancelPaste = function(e) {
        if (e.key === 'Escape') {
            cancelPasteMode();
        }
    };
    document.addEventListener('keydown', cancelPaste);
    
    return true;
}

function handleMapClickForPaste(e) {
    if (!isPasting || !copiedLote) return;
    
    const clickLatLng = e.latlng;
    
    // Remover draft anterior
    if (currentDraftLote) {
        lotesEditable.removeLayer(currentDraftLote);
        currentDraftLote = null;
    }
    
    // Calcular el offset entre el centro original y el nuevo punto de colocación
    const originalCenter = copiedLote.bounds.getCenter();
    const offsetLng = clickLatLng.lng - originalCenter.lng;
    const offsetLat = clickLatLng.lat - originalCenter.lat;
    
    // Crear una copia trasladada de la geometría
    const translatedGeojson = JSON.parse(JSON.stringify(copiedLote.geojson));
    
    // Función recursiva para trasladar todas las coordenadas
    function translateCoords(coords) {
        if (Array.isArray(coords[0])) {
            return coords.map(inner => translateCoords(inner));
        } else {
            return [coords[0] + offsetLng, coords[1] + offsetLat];
        }
    }
    
    // Aplicar la traslación a todas las coordenadas
    translatedGeojson.coordinates = translateCoords(translatedGeojson.coordinates);
    
    // Crear el nuevo layer basado en el tipo de geometría original
    let newLayer;
    if (copiedLote.layerType === 'rectangle') {
        // Para rectángulos, crear un rectángulo desde las coordenadas
        const coords = translatedGeojson.coordinates[0];
        const latLngs = coords.map(coord => L.latLng(coord[1], coord[0]));
        newLayer = L.rectangle(latLngs, {
            color: '#2e7dff',
            weight: 2,
            fillOpacity: 0.15
        });
    } else {
        // Para polígonos, crear un polígono
        newLayer = L.geoJSON(translatedGeojson, {
            style: {
                color: '#2e7dff',
                weight: 2,
                fillOpacity: 0.15
            }
        }).getLayers()[0];
    }
    
    // Añadir al grupo editable
    lotesEditable.addLayer(newLayer);
    
    // IMPORTANTE: Asignar a currentDraftLote
    currentDraftLote = newLayer;
    
    // Generar número de lote
    let newNumero = generateNextLoteNumber(copiedLote.numero_lote);
    
    // Llenar formulario
    document.getElementById('f-numero').value = newNumero;
    document.getElementById('f-manzana').value = copiedLote.manzana;
    document.getElementById('f-precio').value = copiedLote.precio;
    document.getElementById('f-m2').value = copiedLote.metros_cuadrados;
    document.getElementById('f-estado').value = 'disponible';
    
    const fracSelect = document.getElementById('lote-frac');
    if (fracSelect.value !== copiedLote.fraccionamiento_id.toString()) {
        fracSelect.value = copiedLote.fraccionamiento_id;
    }
    
    // Feedback visual
    currentDraftLote.setStyle({ weight: 4, color: '#ff9900' });
    setTimeout(() => {
        if (currentDraftLote && map.hasLayer(currentDraftLote)) {
            currentDraftLote.setStyle({ weight: 2, color: '#2e7dff' });
        }
    }, 500);
    
    cancelPasteMode();
}

function generateNextLoteNumber(baseNumber) {
    const match = baseNumber.match(/(.*?)(\d+)$/);
    if (match) {
        const base = match[1];
        const num = parseInt(match[2]) + 1;
        return base + num;
    } else {
        return baseNumber + '-1';
    }
}

function cancelPasteMode() {
    isPasting = false;
    map.getContainer().style.cursor = originalCursor;
    map._container.classList.remove('pasting-mode');
    map.off('click', handleMapClickForPaste);
    document.removeEventListener('keydown', cancelPasteMode);
}

function pasteLote() {
    if (!copiedLote) {
        return false;
    }
    return startPasteMode();
}

// ======== CARGAS INICIALES ========

function loadFraccionamientos() {
    return fetch('/api/fraccionamientos')
        .then(r=>r.json())
        .then(fc=>{
            allFracsData = fc.features; // *** GUARDAMOS LOS DATOS DE FRACCIONAMIENTOS ***
            if (fracsLayer) map.removeLayer(fracsLayer);
            fracsLayer = L.geoJSON(fc, {
                style: { color: '#2e7dff', weight: 2, fillOpacity: 0.06 },
                onEachFeature: (f, layer) => {
                    layer._fracId = f.properties.id;
                    layer._fracProps = f.properties;
                    layer.bindPopup(`<b>${f.properties.nombre}</b><br>${f.properties.descripcion || ''}`);
                    layer.on('click', () => {
                        document.getElementById('lote-frac').value = f.properties.id;
                        fracForFilter = f.properties.id;
                        loadLotes(fracForFilter).then(()=>{
                            try { map.fitBounds(layer.getBounds(), {padding:[20,20]}); } catch(e){}
                        });
                        document.getElementById('frac-select').value = f.properties.id;
                    });
                }
            }).addTo(map);

            const sel1 = document.getElementById('lote-frac');
            const sel2 = document.getElementById('frac-select');
            const selFiltro = document.getElementById('admin-frac-filter'); // El nuevo filtro
            sel1.innerHTML = `<option value="">— Selecciona —</option>`;
            sel2.innerHTML = `<option value="">— Selecciona para editar —</option>`;
            selFiltro.innerHTML = '<option value="">-- Todos --</option>'; // Opción "Todos"
            
            fc.features.forEach(f=>{
                const id = f.properties.id, nombre = f.properties.nombre;
                const o1 = document.createElement('option'); o1.value=id; o1.textContent=nombre; sel1.appendChild(o1);
                const o2 = document.createElement('option'); o2.value=id; o2.textContent=nombre; sel2.appendChild(o2);
                const o3 = document.createElement('option'); o3.value=id; o3.textContent=nombre; selFiltro.appendChild(o3); // Poblar filtro
            });

            try { map.fitBounds(fracsLayer.getBounds(), {padding:[20,20]}); } catch(e){}
        });
}

function loadLotes(fraccionamientoId = null) {
    const url = fraccionamientoId ? `/api/lotes?fraccionamiento_id=${fraccionamientoId}` : '/api/lotes';
    return fetch(url)
        .then(r=>r.json())
        .then(fc=>{
            if (lotesLayer) map.removeLayer(lotesLayer);
            lotesEditable.clearLayers();
            selectedLoteLayer = null;
            
            // Remover marcador de movimiento
            if (moveMarker) {
                map.removeLayer(moveMarker);
                moveMarker = null;
            }

            lotesLayer = L.geoJSON(fc, {
                style: f => styleByEstado(f.properties.estado),
                onEachFeature: (f, layer) => {
                    layer._loteId = f.properties.id;
                    layer._props = f.properties;
                    layer.bindPopup(`
                        <b>Manzana:</b> ${f.properties.manzana}<br>
                        <b>Lote:</b> ${f.properties.numero_lote}<br>
                        <b>Estado:</b> ${f.properties.estado}<br>
                        <b>Precio:</b> $${f.properties.precio.toLocaleString()}<br>
                        <b>Sup:</b> ${f.properties.metros_cuadrados} m²
                    `);
                    layer.on('click', (e) => {
                        // Marcar que este click fue en un lote
                        e.originalEvent.__selected = true;
                        
                        if (selectedLoteLayer && selectedLoteLayer !== layer) {
                            try { selectedLoteLayer.setStyle(styleByEstado(selectedLoteLayer._props.estado)); } catch(e){}
                        }
                        selectedLoteLayer = layer;
                        layer.setStyle({ weight: 4, color: '#2e7dff' });

                        if (!lotesEditable.hasLayer(layer)) lotesEditable.addLayer(layer);
                        
                        // Añadir marcador de movimiento
                        addMoveMarker(layer);

                        document.getElementById('f-numero').value = layer._props.numero_lote;
                        document.getElementById('f-manzana').value = layer._props.manzana;
                        document.getElementById('f-precio').value = layer._props.precio;
                        document.getElementById('f-m2').value = layer._props.metros_cuadrados;
                        document.getElementById('f-estado').value = layer._props.estado;
                        document.getElementById('lote-frac').value = layer._props.fraccionamiento_id;
                        fracForFilter = layer._props.fraccionamiento_id;
                    });
                }
            }).addTo(map);
        });
}

// Inicial
loadFraccionamientos().then(()=> loadLotes());

// ======== DIBUJO / EVENTOS DRAW ========

let currentDrawMode = null;

document.getElementById('btn-draw-rect').addEventListener('click', () => {
    currentDrawMode = "lote-rect";
    drawControl._toolbars.draw._modes.rectangle.handler.enable();
});

document.getElementById('btn-draw-poly').addEventListener('click', () => {
    currentDrawMode = "lote-poly";
    drawControl._toolbars.draw._modes.polygon.handler.enable();
});

document.getElementById('btn-frac-draw').addEventListener('click', () => {
    currentDrawMode = "frac-poly";
    drawControl._toolbars.draw._modes.polygon.handler.enable();
});

document.getElementById('btn-edit-lote').addEventListener('click', () => {
    if (!selectedLoteLayer) {
        alert('Selecciona un lote para editar');
        return;
    }
    
    if (!lotesEditable.hasLayer(selectedLoteLayer)) {
        lotesEditable.addLayer(selectedLoteLayer);
    }
    
    drawControl._toolbars.edit._modes.edit.handler.enable();
});

map.on(L.Draw.Event.CREATED, function(e) {
    const layer = e.layer;
    const geom = layer.toGeoJSON().geometry;

    if (currentDrawMode === "frac-poly") {
        if (currentFracDraft) fracDrawn.removeLayer(currentFracDraft);
        layer.setStyle({ color: '#2e7dff', weight: 2, fillOpacity: 0.08 });
        fracDrawn.addLayer(layer);
        currentFracDraft = layer;
    } else {
        if (currentDraftLote) lotesEditable.removeLayer(currentDraftLote);
        layer.setStyle({ color: '#2e7dff', weight: 2, fillOpacity: 0.15 });
        lotesEditable.addLayer(layer);
        currentDraftLote = layer;
        
        // Generar número de lote automático
        document.getElementById('f-numero').value = 'L' + (Math.floor(Math.random() * 100) + 1);
        document.getElementById('f-manzana').value = 'M' + (Math.floor(Math.random() * 10) + 1);
        document.getElementById('f-precio').value = '50000000';
        document.getElementById('f-m2').value = '200';
        document.getElementById('f-estado').value = 'disponible';
    }

    currentDrawMode = null;
});

// ======== DESELECCIONAR AL HACER CLICK EN EL MAPA ========

map.on('click', function(e) {
    // Si estamos en modo pegado, manejar con la función correspondiente
    if (isPasting) {
        return;
    }
    
    // Si no se hizo click en un lote, deseleccionar el lote actual
    if (selectedLoteLayer && !e.originalEvent.__selected) {
        try { 
            selectedLoteLayer.setStyle(styleByEstado(selectedLoteLayer._props.estado)); 
        } catch(e){}
        selectedLoteLayer = null;
        
        // Remover marcador de movimiento
        if (moveMarker) {
            map.removeLayer(moveMarker);
            moveMarker = null;
        }
        
        // Limpiar formulario
        document.getElementById('f-numero').value = '';
        document.getElementById('f-manzana').value = '';
        document.getElementById('f-precio').value = '';
        document.getElementById('f-m2').value = '';
        document.getElementById('f-estado').value = 'disponible';
    }
    // Resetear la marca de selección
    if (e.originalEvent) {
        e.originalEvent.__selected = false;
    }
});

// ======== CRUD FRACCIONAMIENTOS ========

document.getElementById('btn-frac-save').addEventListener('click', () => {
    const nombre = document.getElementById('frac-nombre').value.trim();
    const descripcion = document.getElementById('frac-desc').value.trim();
    const ciudad_id = document.getElementById('frac-ciudad').value; // <--- Capturar Ciudad

    if (!nombre) { alert("Ingresa un nombre de fraccionamiento"); return; }
    if (!currentFracDraft) { alert("Dibuja el polígono del fraccionamiento primero."); return; }

    const geo = currentFracDraft.toGeoJSON().geometry;

    const selectedId = document.getElementById('frac-select').value;
    const method = selectedId ? 'PATCH' : 'POST';
    const url = selectedId ? `/api/admin/fraccionamientos/${selectedId}` : '/api/admin/fraccionamientos';

    fetch(url, {
        method,
        headers: {'Content-Type':'application/json'},
        body: JSON.stringify({ 
            nombre, 
            descripcion, 
            ciudad_id: ciudad_id, 
            geojson: geo 
        })
    })
    .then(r=>r.json())
    .then(res=>{
        if (res.ok || res.id) {
            alert(selectedId ? 'Fraccionamiento actualizado' : 'Fraccionamiento creado');
            if (currentFracDraft) { fracDrawn.removeLayer(currentFracDraft); currentFracDraft = null; }
            document.getElementById('frac-nombre').value = "";
            document.getElementById('frac-desc').value = "";
            document.getElementById('frac-select').value = "";
            document.getElementById('frac-ciudad').value = "";
            loadFraccionamientos();
        } else {
            alert('Error al guardar fraccionamiento');
        }
    }).catch(()=> alert('Error de red'));
});

document.getElementById('frac-select').addEventListener('change', (e)=>{
    const fid = e.target.value;
    if (!fid) {
        if (currentFracDraft) { fracDrawn.removeLayer(currentFracDraft); currentFracDraft = null; }
        document.getElementById('frac-nombre').value = "";
        document.getElementById('frac-desc').value = "";
        return;
    }
    fetch('/api/fraccionamientos').then(r=>r.json()).then(fc=>{
        const f = fc.features.find(x=> String(x.properties.id) === String(fid));
        if (!f) return;
        document.getElementById('frac-nombre').value = f.properties.nombre;
        document.getElementById('frac-desc').value = f.properties.descripcion || "";
        document.getElementById('frac-ciudad').value = f.properties.ciudad_id || "";

        if (currentFracDraft) fracDrawn.removeLayer(currentFracDraft);
        const g = L.geoJSON(f, { style: { color:'#2e7dff', weight:2, fillOpacity:0.08 }});
        const lyr = g.getLayers()[0];
        fracDrawn.addLayer(lyr);
        currentFracDraft = lyr;
        try { map.fitBounds(lyr.getBounds(), {padding:[20,20]}); } catch(e){}
    });
});

document.getElementById('btn-frac-del').addEventListener('click', ()=>{
    const fid = document.getElementById('frac-select').value;
    if (!fid) { alert('Selecciona un fraccionamiento para eliminar'); return; }
    if (!confirm('¿Eliminar fraccionamiento seleccionado? (Debe no tener lotes)')) return;

    fetch(`/api/admin/fraccionamientos/${fid}`, { method:'DELETE' })
        .then(r=>r.json())
        .then(res=>{
            if (res.ok) {
                alert('Fraccionamiento eliminado');
                if (currentFracDraft) { fracDrawn.removeLayer(currentFracDraft); currentFracDraft = null; }
                document.getElementById('frac-nombre').value = "";
                document.getElementById('frac-desc').value = "";
                document.getElementById('frac-select').value = "";
                loadFraccionamientos().then(()=> loadLotes());
            } else {
                alert(res.error || 'No se pudo eliminar');
            }
        }).catch(()=> alert('Error de red'));
});

// ======== FUNCIÓN getLoteFormData ========

function getLoteFormData() {
    if (!currentDraftLote && !selectedLoteLayer) {
        alert('No hay un lote dibujado o seleccionado.');
        return null;
    }
    
    const targetLayer = currentDraftLote || selectedLoteLayer;
    let geojson = null;
    
    try {
        const layerGeoJSON = targetLayer.toGeoJSON();
        geojson = layerGeoJSON.geometry;
        
        if (!geojson || !geojson.coordinates || geojson.coordinates.length === 0) {
            console.error('Geometría inválida:', geojson);
            alert('La geometría del lote no es válida.');
            return null;
        }
    } catch (error) {
        console.error('Error obteniendo geometría:', error);
        alert('Error al obtener la geometría del lote.');
        return null;
    }
    
    const numeroLote = document.getElementById('f-numero').value.trim();
    const manzana = document.getElementById('f-manzana').value.trim();
    const precio = parseFloat(document.getElementById('f-precio').value);
    const metrosCuadrados = parseInt(document.getElementById('f-m2').value, 10);
    const estado = document.getElementById('f-estado').value;
    const fraccionamientoId = parseInt(document.getElementById('lote-frac').value, 10);
    
    if (!numeroLote) {
        alert('El número de lote es obligatorio');
        return null;
    }
    if (!manzana) {
        alert('La manzana es obligatoria');
        return null;
    }
    if (isNaN(precio) || precio <= 0) {
        alert('El precio debe ser un número mayor a 0');
        return null;
    }
    if (isNaN(metrosCuadrados) || metrosCuadrados <= 0) {
        alert('Los metros cuadrados deben ser un número mayor a 0');
        return null;
    }
    if (!fraccionamientoId || isNaN(fraccionamientoId)) {
        alert('Debes seleccionar un fraccionamiento');
        return null;
    }
    
    const data = {
        numero_lote: numeroLote,
        manzana: manzana,
        precio: precio,
        metros_cuadrados: metrosCuadrados,
        estado: estado,
        fraccionamiento_id: fraccionamientoId,
        geojson: geojson
    };
    
    return data;
}

// ======== BOTÓN GUARDAR ========

document.getElementById('btn-guardar').addEventListener('click', function() {
    const data = getLoteFormData();
    
    if (!data) {
        return false;
    }
    
    fetch('/api/admin/lotes', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(data)
    })
    .then(response => {
        if (!response.ok) {
            return response.json().then(errorData => {
                throw new Error(errorData.error || 'Error del servidor');
            });
        }
        return response.json();
    })
    .then(responseData => {
        if (responseData.ok) {
            alert('Lote creado correctamente');
            if (currentDraftLote) {
                lotesEditable.removeLayer(currentDraftLote);
                currentDraftLote = null;
            }
            
            document.getElementById('f-numero').value = '';
            document.getElementById('f-manzana').value = '';
            document.getElementById('f-precio').value = '';
            document.getElementById('f-m2').value = '';
            
            loadLotes(data.fraccionamiento_id);
        } else {
            alert('Error al crear el lote: ' + (responseData.error || 'Error desconocido'));
        }
    })
    .catch(error => {
        console.error('Error:', error);
        alert('Error al crear el lote: ' + error.message);
    });
});

// ======== EVENT LISTENERS PARA COPIAR/PEGAR ========

document.addEventListener('keydown', function(e) {
    if (e.ctrlKey && e.key === 'c') {
        e.preventDefault();
        copyLote();
    }
    
    if (e.ctrlKey && e.key === 'v') {
        e.preventDefault();
        pasteLote();
    }
    
    if (e.key === 'Escape' && isPasting) {
        e.preventDefault();
        cancelPasteMode();
    }
});

// Botones para copiar y pegar
document.addEventListener('DOMContentLoaded', function() {
    if (!document.getElementById('btn-copiar')) {
        const buttonRow = document.querySelector('.panel .section .row:last-of-type');
        const copyPasteDiv = document.createElement('div');
        copyPasteDiv.className = 'row';
        copyPasteDiv.style.display = 'flex';
        copyPasteDiv.style.gap = '8px';
        copyPasteDiv.style.flexDirection = 'row';
        copyPasteDiv.innerHTML = `
            <button id="btn-copiar" class="info" title="Ctrl+C">Copiar</button>
            <button id="btn-pegar" class="info" title="Ctrl+V">Pegar</button>
        `;
        buttonRow.parentNode.insertBefore(copyPasteDiv, buttonRow.nextSibling);
        
        document.getElementById('btn-copiar').addEventListener('click', copyLote);
        document.getElementById('btn-pegar').addEventListener('click', pasteLote);
    }
});

// ======== CRUD LOTES ORIGINAL ========

document.getElementById('btn-actualizar').addEventListener('click', ()=>{
    if (!selectedLoteLayer || !selectedLoteLayer._loteId) { alert('Selecciona un lote de la capa'); return; }
    const id = selectedLoteLayer._loteId;
    const data = getLoteFormData();
    if (!data) return;
    
    const geo = selectedLoteLayer.toGeoJSON().geometry;

    fetch(`/api/admin/lotes/${id}`, {
        method:'PATCH',
        headers:{'Content-Type':'application/json'},
        body: JSON.stringify({...data, geojson: geo})
    })
    .then(r=>r.json())
    .then(res=>{
        if (res.ok) {
            alert('Lote actualizado');
            selectedLoteLayer._props = {
                ...selectedLoteLayer._props,
                ...data
            };
            selectedLoteLayer.setStyle(styleByEstado(data.estado));
            loadLotes(data.fraccionamiento_id);
        } else {
            alert(res.error || 'Error al actualizar');
        }
    }).catch(()=> alert('Error de red'));
});

document.getElementById('btn-eliminar').addEventListener('click', ()=>{
    if (!selectedLoteLayer || !selectedLoteLayer._loteId) { alert('Selecciona un lote'); return; }
    if (!confirm('¿Eliminar este lote?')) return;
    const id = selectedLoteLayer._loteId;
    fetch(`/api/admin/lotes/${id}`, { method:'DELETE' })
        .then(r=>r.json())
        .then(res=>{
            if (res.ok) {
                alert('Lote eliminado');
                loadLotes(fracForFilter || undefined);
            } else {
                alert(res.error || 'Error al eliminar');
            }
        }).catch(()=> alert('Error de red'));
});

document.getElementById('lote-frac').addEventListener('change', (e)=>{
    const fid = e.target.value;
    fracForFilter = fid || null;
    loadLotes(fracForFilter || undefined);
    if (fid) {
        // *** CAMBIO: Usamos allFracsData en lugar de un nuevo fetch ***
        const selFeature = allFracsData.find(x => String(x.properties.id) === String(fid));
        if (selFeature) {
            const temp = L.geoJSON(selFeature);
            try { map.fitBounds(temp.getBounds(), {padding:[20,20]}); } catch(e){}
        }
    }
});

// ======== *** LÓGICA DEL NUEVO FILTRO (AÑADIDA) *** ========
document.getElementById('admin-frac-filter').addEventListener('change', e => {
    const fid = e.target.value;
    
    loadLotes(fid); 

    if (!fid) {
        if (fracsLayer.getLayers().length > 0) {
            map.fitBounds(fracsLayer.getBounds());
        }
    } else {
        const selFeature = allFracsData.find(x => String(x.properties.id) === String(fid));
        if (selFeature) {
            const temp = L.geoJSON(selFeature);
            try { map.fitBounds(temp.getBounds(), {padding:[20,20]}); } catch(e){}
        }
    }
});
// ==========================================================

// ======== ESTILOS ADICIONALES ========

document.addEventListener('DOMContentLoaded', function() {
    const style = document.createElement('style');
    style.textContent = `
        .move-marker {
            background: transparent;
            border: none;
        }
        
        .move-marker div {
            cursor: move;
        }
        
        .pasting-mode {
            cursor: crosshair !important;
        }
    `;
    document.head.appendChild(style);
});

// ======== EVENTOS DRAW (TU CÓDIGO ORIGINAL) ========
map.on('draw:edited', function (e) {
    if (selectedLoteLayer && confirm('¿Deseas guardar la nueva forma del lote seleccionado?')) {
        document.getElementById('btn-actualizar').click();
    }
});