// Mapa centrado en la región
const map = L.map('map').setView([-27.033, -56.133], 10);
L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
  attribution: '&copy; OpenStreetMap contributors'
}).addTo(map);

// Función de estilo por estado
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

let fracsLayer = null;
let lotesLayer = null;

// --- FUNCIÓN CENTRAL PARA CREAR POPUPS DE LOTES ---
function createLotePopup(properties) {
    let popupContent = `
        <b>Manzana:</b> ${properties.manzana}<br>
        <b>Lote:</b> ${properties.numero_lote}<br>
        <b>Estado:</b> ${properties.estado}<br>
        <b>Sup:</b> ${properties.metros_cuadrados} m²
    `;

    const precioContado = properties.precio;
    if (precioContado) {
        popupContent += `<br><b>Precio Contado:</b> Gs. ${precioContado.toLocaleString('es-PY')}`;
    }

    const precioCuota130 = properties.precio_cuota_130;
    if (precioCuota130) {
        popupContent += `<br><b>130 Meses:</b> Gs. ${precioCuota130.toLocaleString('es-PY')}`;
    }

    return popupContent;
}

// Cargar fraccionamientos en el selector y en el mapa
fetch('/api/fraccionamientos')
  .then(r => r.json())
  .then(fc => {
    const sel = document.getElementById('sel-frac');
    fc.features.forEach(f => {
      const opt = document.createElement('option');
      opt.value = f.properties.id;
      opt.textContent = f.properties.nombre;
      sel.appendChild(opt);
    });

    fracsLayer = L.geoJSON(fc, {
      style: { color: '#2e7dff', weight: 2, fillOpacity: 0.06 },
      
      // ===== LÓGICA AÑADIDA PARA POPUPS DE FRACCIONAMIENTOS =====
      onEachFeature: function (feature, layer) {
          const properties = feature.properties;
          if (properties && properties.nombre) {
              let popupContent = `<strong>${properties.nombre}</strong>`;
              if (properties.descripcion) {
                  popupContent += `<br>${properties.descripcion}`;
              }
              layer.bindPopup(popupContent);
          }
      }
      // ===== FIN DE LA LÓGICA AÑADIDA =====

    }).addTo(map);

    try {
      map.fitBounds(fracsLayer.getBounds(), {padding:[20,20]});
    } catch(e){}
  })
  .catch(err => {
    console.error("Error cargando fraccionamientos:", err);
  });

// Función central para cargar y mostrar los lotes en el mapa
function cargarLotes(url) {
    fetch(url)
      .then(r => r.json())
      .then(fc => {
        if (lotesLayer) {
          map.removeLayer(lotesLayer);
        }

        lotesLayer = L.geoJSON(fc, {
          style: feat => styleByEstado(feat.properties.estado),
          onEachFeature: (f, l) => {
            l.bindPopup(createLotePopup(f.properties));
            l.on('mouseover', function(){ this.setStyle({ weight: 3 }); });
            l.on('mouseout', function(){ this.setStyle({ weight: 2 }); });
          }
        }).addTo(map);

        try {
          if(fc.features.length > 0) {
            map.fitBounds(lotesLayer.getBounds(), {padding:[20,20]});
          }
        } catch(e){}
      })
      .catch(err => {
        console.error("Error cargando lotes:", err);
      });
}

// Carga inicial de todos los lotes
cargarLotes('/api/lotes');

// Evento para cuando se cambia la selección de fraccionamiento
document.getElementById('sel-frac').addEventListener('change', e => {
  const fid = e.target.value;

  if (!fid) {
    // Si se deselecciona, mostrar todos los lotes de nuevo
    cargarLotes('/api/lotes');
    if (fracsLayer) {
        try { map.fitBounds(fracsLayer.getBounds(), {padding:[20,20]}); } catch(e) {}
    }
    return;
  }

  // Centrar en el fraccionamiento seleccionado
  const fraccionamientoSeleccionado = fracsLayer.getLayers().find(layer => String(layer.feature.properties.id) === String(fid));
  if (fraccionamientoSeleccionado) {
      try {
          map.fitBounds(fraccionamientoSeleccionado.getBounds(), { padding: [20, 20] });
      } catch (e) { }
  }

  // Cargar solo los lotes del fraccionamiento seleccionado
  cargarLotes(`/api/fraccionamientos/${fid}/lotes`);
});