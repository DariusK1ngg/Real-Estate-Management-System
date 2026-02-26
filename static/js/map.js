// static/js/map.js

// Mapa centrado en la región
const map = L.map('map').setView([-27.033, -56.133], 10);
L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
  attribution: '&copy; OpenStreetMap contributors'
}).addTo(map);

// Estilos
function styleByEstado(e) {
  if (e === "disponible") return { color:"#2ECC71", weight:2, fillOpacity:0.25, fillColor:"#2ECC71" };
  if (e === "reservado")  return { color:"#F1C40F", weight:2, fillOpacity:0.25, fillColor:"#F1C40F" };
  return { color:"#E74C3C",  weight:2, fillOpacity:0.25, fillColor:"#E74C3C" };
}

// Leyenda
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

// Variables globales
let lotesLayer = null;
let fracsLayer = null;
let allFracsData = []; // Guardaremos los datos crudos aquí para buscarlos fácil

// Cargar Fraccionamientos
fetch('/api/fraccionamientos')
  .then(r => r.json())
  .then(fc => {
    allFracsData = fc.features; // 1. Guardar datos
    
    const sel = document.getElementById('sel-frac');
    // Limpiar opciones previas (excepto la primera)
    sel.innerHTML = '<option value="">— Selecciona —</option>';
    
    fc.features.forEach(f => {
      const opt = document.createElement('option');
      opt.value = f.properties.id;
      opt.textContent = f.properties.nombre;
      sel.appendChild(opt);
    });

    // Dibujar en el mapa
    fracsLayer = L.geoJSON(fc, {
      style: { color: '#2e7dff', weight: 2, fillOpacity: 0.06 },
      onEachFeature: function (feature, layer) {
          const p = feature.properties;
          if (p && p.nombre) {
              layer.bindPopup(`<strong>${p.nombre}</strong><br>${p.descripcion || ''}`);
          }
      }
    }).addTo(map);

    // Ajustar vista inicial si hay datos
    if (fc.features.length > 0) {
        try { map.fitBounds(fracsLayer.getBounds(), {padding:[20,20]}); } catch(e){}
    }
  })
  .catch(console.error);

// Función para cargar lotes
function cargarLotes(url) {
    fetch(url)
      .then(r => r.json())
      .then(fc => {
        if (lotesLayer) map.removeLayer(lotesLayer);

        lotesLayer = L.geoJSON(fc, {
          style: feat => styleByEstado(feat.properties.estado),
          onEachFeature: (f, l) => {
            const props = f.properties; 

            // 1. Información Base (Siempre visible: Lote, Mz, Superficie, Estado)
            let content = `
                <div style="font-size: 14px; line-height: 1.5;">
                    <b>Manzana:</b> ${props.manzana}<br>
                    <b>Lote:</b> ${props.numero_lote}<br>
                    <b>Estado:</b> ${props.estado.toUpperCase()}<br>
                    <b>Superficie:</b> ${props.metros_cuadrados} m²
            `;

            // 2. Lógica de Precios (SOLO SE MUESTRA SI NO ESTÁ VENDIDO)
            if (props.estado !== 'vendido') {
                
                // A) Precio Contado (Se muestra siempre que exista)
                if (props.precio && props.precio > 0) {
                    content += `<br><b>Precio Contado:</b> Gs. ${props.precio.toLocaleString('es-PY')}`;
                }

                // B) Financiación 130 cuotas (Se agrega DEBAJO si existe)
                if (props.precio_cuota_130 && props.precio_cuota_130 > 0) {
                    content += `
                        <div style="margin-top: 8px; padding: 8px; background-color: #e6fffa; border: 1px solid #38b2ac; border-radius: 5px; text-align: center;">
                            <strong style="color: #234e52; display: block; margin-bottom: 2px;">¡FINANCIACIÓN PROPIA!</strong>
                            <span style="font-size: 0.9em; color: #2c7a7b;">130 cuotas de:</span><br>
                            <span style="font-size: 1.2em; font-weight: bold; color: #285e61;">
                                Gs. ${props.precio_cuota_130.toLocaleString('es-PY')}
                            </span>
                        </div>
                    `;
                }
            }
            // Si es 'vendido', el código salta aquí directamente y no muestra precios.

            content += `</div>`; // Cerrar div principal

            l.bindPopup(content);
            
            // Efectos visuales al pasar el mouse
            l.on('mouseover', function(){ this.setStyle({ weight: 3, fillOpacity: 0.4 }); });
            l.on('mouseout', function(){ this.setStyle({ weight: 2, fillOpacity: 0.25 }); });
          }
        }).addTo(map);
      })
      .catch(console.error);
}

// Carga inicial
cargarLotes('/api/lotes');

// EVENTO DE CAMBIO EN EL SELECT
document.getElementById('sel-frac').addEventListener('change', e => {
  const fid = e.target.value;

  if (!fid) {
    cargarLotes('/api/lotes');
    if (fracsLayer) map.fitBounds(fracsLayer.getBounds());
    return;
  }

  // 2. Buscar en los datos crudos (Más robusto que buscar en capas)
  const featureEncontrado = allFracsData.find(f => String(f.properties.id) === String(fid));

  if (featureEncontrado) {
      // Crear una capa temporal solo para calcular los bordes (bounds)
      const tempLayer = L.geoJSON(featureEncontrado);
      try {
          map.fitBounds(tempLayer.getBounds(), { padding: [50, 50] });
      } catch (error) {
          console.log("Error al hacer zoom:", error);
      }
  }

  // Cargar lotes filtrados
  cargarLotes(`/api/fraccionamientos/${fid}/lotes`);
});