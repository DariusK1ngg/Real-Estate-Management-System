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
            // Popup detallado
            let content = `
                <b>Manzana:</b> ${f.properties.manzana}<br>
                <b>Lote:</b> ${f.properties.numero_lote}<br>
                <b>Estado:</b> ${f.properties.estado}<br>
                <b>Sup:</b> ${f.properties.metros_cuadrados} m²`;
            
            if (f.properties.precio) {
                content += `<br><b>Precio:</b> Gs. ${f.properties.precio.toLocaleString('es-PY')}`;
            }
            l.bindPopup(content);
            
            l.on('mouseover', function(){ this.setStyle({ weight: 3, fillOpacity: 0.4 }); });
            l.on('mouseout', function(){ this.setStyle({ weight: 2, fillOpacity: 0.25 }); });
          }
        }).addTo(map);
      })
      .catch(console.error);
}

// Carga inicial
cargarLotes('/api/lotes');

// EVENTO DE CAMBIO (Aquí estaba el problema)
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