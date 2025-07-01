// Ganti seluruh isi file 'static/js/map.js' dengan kode di bawah ini

const map = L.map('map', {
    maxBounds: [[-12, 90], [7, 142]],
    maxBoundsViscosity: 1.0
}).setView([-2.5, 120], 5);

L.tileLayer('https://mt1.google.com/vt/lyrs=y&x={x}&y={y}&z={z}', {
    attribution: 'Map data &copy; Google',
    maxZoom: 20
}).addTo(map);

const sidebar = document.getElementById("sidebar");
const sidebarContent = document.getElementById("sidebarContent");

let currentFeature = null;
let currentLayer = null;
let currentTableName = null;
let isEditMode = false;

function showSidebar(html) {
    sidebarContent.innerHTML = html;
    sidebar.classList.add("open");
}

function hideSidebar() {
    sidebar.classList.remove("open");
    resetEditMode();
}

function resetEditMode() {
    currentFeature = null;
    currentLayer = null;
    currentTableName = null;
    isEditMode = false;
}

function showNotification(message, type = 'success') {
    const existingNotification = document.querySelector('.notification');
    if (existingNotification) existingNotification.remove();
    const notification = document.createElement('div');
    notification.className = `notification ${type}`;
    notification.textContent = message;
    document.body.appendChild(notification);
    setTimeout(() => {
        notification.classList.add('fadeOut');
        setTimeout(() => { if (notification.parentNode) notification.parentNode.removeChild(notification); }, 300);
    }, 3000);
}

function buildSidebarContent(feature, data, layerInstance, tableName) {
    const order = data.field_order ?? Object.keys(feature.properties);
    let html = "<table>";
    order.forEach(key => {
        const value = feature.properties[key] ?? "-";
        if (key === "Okupansi Telkom (%)" && feature.properties.hasOwnProperty("Okupansi Telkom (%)")) {
            html += `<tr><td><strong>${key}</strong></td><td><div class="okupansi-value-container"><div class="okupansi-display" id="okupansiDisplay"><span>: ${value}%</span><button class="btn-edit" onclick="startEdit()">edit</button></div><div class="okupansi-edit-form" id="okupansiEditForm"><span>:</span><input type="number" id="okupansiInput" class="edit-input" min="0" max="100" step="0.01" value="${value}" /><span>%</span><button class="btn-save" onclick="saveOkupansi()">Simpan</button><button class="btn-cancel" onclick="cancelEdit()">Batal</button><span id="loadingStatus" class="loading-text" style="display: none;"></span></div></div></td></tr>`;
        } else {
            html += `<tr><td><strong>${key}</strong></td><td>: ${value}</td></tr>`;
        }
    });
    html += "</table>";
    return html;
}

function startEdit() {
    if (!currentFeature || !currentTableName) return;
    isEditMode = true;
    document.getElementById('okupansiDisplay').style.display = 'none';
    document.getElementById('okupansiEditForm').style.display = 'flex';
    document.getElementById('okupansiInput').focus();
}

function cancelEdit() {
    document.getElementById('okupansiDisplay').style.display = 'flex';
    document.getElementById('okupansiEditForm').style.display = 'none';
    document.getElementById('loadingStatus').style.display = 'none';
    isEditMode = false;
    if (currentFeature) document.getElementById('okupansiInput').value = currentFeature.properties['Okupansi Telkom (%)'] || '';
}

async function saveOkupansi() {
    if (!currentFeature || !currentTableName) return;
    const okupansiValue = document.getElementById('okupansiInput').value;
    const statusSpan = document.getElementById('loadingStatus');
    const linkValue = currentFeature.properties.Link;
    const apiEndpoint = `/api/update-by-link/${currentTableName}`;
    
    if (!linkValue) { showNotification('Link Name tidak ditemukan untuk update', 'error'); return; }
    if (okupansiValue === '' || isNaN(okupansiValue) || okupansiValue < 0 || okupansiValue > 100) { showNotification('Nilai okupansi harus antara 0-100', 'error'); return; }

    statusSpan.style.display = 'inline';
    statusSpan.textContent = 'Menyimpan...';

    try {
        const response = await fetch(apiEndpoint, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ 'link': linkValue, 'Okupansi Telkom (%)': parseFloat(okupansiValue) })
        });
        const result = await response.json();
        if (response.ok) {
            showNotification('Okupansi berhasil diupdate', 'success');
            currentFeature.properties['Okupansi Telkom (%)'] = parseFloat(okupansiValue);
            document.querySelector('#okupansiDisplay span').textContent = `: ${okupansiValue}%`;
            if (currentLayer && currentLayer.setStyle) { currentLayer.setStyle(styleAlur(currentFeature)); }
            setTimeout(() => refreshSpecificLayer(), 500);
            setTimeout(() => cancelEdit(), 1000);
        } else {
            showNotification(`Error: ${result.error || 'Gagal menyimpan'}`, 'error');
        }
    } catch (error) {
        showNotification('Error: Gagal menghubungi server', 'error');
    } finally {
        statusSpan.style.display = 'none';
    }
}

function refreshSpecificLayer() {
    if (!currentTableName) return;
    let projectGroup, alurUrl;
    if (currentTableName.includes('Barat')) { projectGroup = groupLayers.PalapaRingBarat; alurUrl = `${BASE}/alur/barat`; }
    else if (currentTableName.includes('Tengah')) { projectGroup = groupLayers.PalapaRingTengah; alurUrl = `${BASE}/alur/tengah`; }
    else if (currentTableName.includes('Timur')) { projectGroup = groupLayers.PalapaRingTimur; alurUrl = `${BASE}/alur/timur`; }
    
    if(projectGroup) {
        loadGeoJsonFromAPI(alurUrl, "alur", projectGroup.alur);
        setTimeout(() => {
            projectGroup.all.clearLayers();
            projectGroup.all.addLayer(projectGroup.alur);
            projectGroup.all.addLayer(projectGroup.point);
        }, 200);
    }
}

document.getElementById("closeSidebar").addEventListener("click", hideSidebar);
map.on("click", hideSidebar);

function styleTitik(feature) {
    let warna = "#cccccc";
    if (feature.properties.Keterangan === "Kota Interkoneksi") warna = "#00bfff";
    else if (feature.properties.Keterangan === "Kota Layanan") warna = "#ffff00";
    return { radius: 6, fillColor: warna, color: "#000", weight: 1, opacity: 1, fillOpacity: 0.8 };
}

function styleAlur(feature) {
    if (feature.properties.Description) return { color: "#d3f462", weight: 2, dashArray: "4 4", opacity: 0.7 };
    const okupansi = parseFloat(feature.properties["Okupansi Telkom (%)"]);
    let warna = "gray";
    if (!isNaN(okupansi)) {
        if (okupansi > 80) warna = "red";
        else if (okupansi >= 50) warna = "yellow";
        else warna = "green";
    }
    return { color: warna, weight: 3, opacity: 0.8 };
}

const groupLayers = {
    'PalapaRingBarat': { alur: L.layerGroup(), point: L.layerGroup(), all: L.layerGroup() },
    'PalapaRingTengah': { alur: L.layerGroup(), point: L.layerGroup(), all: L.layerGroup() },
    'PalapaRingTimur': { alur: L.layerGroup(), point: L.layerGroup(), all: L.layerGroup() },
    'submarineCable': L.layerGroup()
};

const searchablePointsLayer = L.layerGroup();
const BASE = "/api"; 

function loadGeoJsonFromAPI(url, type = 'point', targetGroup) {
    fetch(url)
        .then(res => res.json())
        .then(data => {
            targetGroup.clearLayers();
            const kotaMicrowave = ["Sami", "Burmeso", "Elelim", "Wamena", "Kenyam", "Sumohai", "Dekai", "Oksibil", "Kobagma", "Tiom", "Karubaga", "Mulia", "Kepi Tower", "Ilaga", "Sugapa"];
            const microwaveIcon = L.icon({ iconUrl: '/static/images/microwave.png', iconSize: [24, 24], iconAnchor: [12, 12], popupAnchor: [0, -10] });
            const layer = L.geoJSON(data, {
                pointToLayer: (feature, latlng) => {
                    if (type === 'point' && kotaMicrowave.includes(feature.properties.Nama)) return L.marker(latlng, { icon: microwaveIcon });
                    if (type === 'point') return L.circleMarker(latlng, styleTitik(feature));
                },
                style: type === 'alur' ? styleAlur : undefined,
                onEachFeature: function (feature, layer) {
                    layer.on("click", function (e) {
                        L.DomEvent.stopPropagation(e);
                        currentFeature = feature;
                        currentLayer = layer;
                        if (type === 'alur') {
                            if (url.includes('/alur/barat')) currentTableName = 'Palapa_Ring_Barat_Alur';
                            else if (url.includes('/alur/tengah')) currentTableName = 'Palapa_Ring_Tengah_Alur';
                            else if (url.includes('/alur/timur')) currentTableName = 'Palapa_Ring_Timur_Alur';
                        }
                        showSidebar(buildSidebarContent(feature, data, layer, currentTableName));
                        if (layer.getBounds) map.fitBounds(layer.getBounds(), { maxZoom: 9 });
                        else if (layer.getLatLng) map.setView(layer.getLatLng(), 9);
                    });
                    if (type === 'point' && feature.properties.Nama) {
                        layer.bindTooltip(feature.properties.Nama, { permanent: true, direction: 'top', className: 'label-nama' }).openTooltip();
                        layer.options.title = feature.properties.Nama;
                        searchablePointsLayer.addLayer(layer);
                    }
                }
            });
            layer.addTo(targetGroup);
        })
        .catch(err => console.error("Failed to load:", url, err));
}

function refreshAllLayers() {
    searchablePointsLayer.clearLayers();
    const projects = ['Barat', 'Tengah', 'Timur'];
    projects.forEach(proj => {
        const groupName = `PalapaRing${proj}`;
        const projectLayerGroup = groupLayers[groupName].all;
        if (map.hasLayer(projectLayerGroup)) {
            const group = groupLayers[groupName];
            loadGeoJsonFromAPI(`${BASE}/alur/${proj.toLowerCase()}`, "alur", group.alur);
            loadGeoJsonFromAPI(`${BASE}/point/${proj.toLowerCase()}`, "point", group.point);
        }
    });
}

refreshAllLayers();
setInterval(refreshAllLayers, 30000);

const legend = L.control({ position: "bottomright" });
legend.onAdd = function () {
    const div = L.DomUtil.create("div", "legend");
    div.innerHTML = `<h4>Keterangan Peta</h4>
        <img src='/static/images/microwave.png' style='width:18px; height:18px; margin-right:8px;'>Microwave/Radio<br>
        <i style='background:#00bfff'></i> Kota Interkoneksi<br>
        <i style='background:#ffff00'></i> Kota Layanan<br><hr>
        <i style='background:green'></i> Okupansi < 50%<br>
        <i style='background:yellow'></i> Okupansi 50–80%<br>
        <i style='background:red'></i> Okupansi > 80%<br>
        <i style='background:#d3f462; border:1px dashed #d3f462;'></i> Submarine Cable<br>`;
    return div;
};
legend.addTo(map);

const layerControl = L.control.layers(null, {
    "Palapa Ring Barat": groupLayers.PalapaRingBarat.all.addTo(map),
    "Palapa Ring Tengah": groupLayers.PalapaRingTengah.all.addTo(map),
    "Palapa Ring Timur": groupLayers.PalapaRingTimur.all.addTo(map),
    "Submarine Cable": groupLayers.submarineCable.addTo(map)
}).addTo(map);

L.Control.HistoryButton = L.Control.extend({
    onAdd: function(map) {
        const a = L.DomUtil.create('a');
        a.href = '/history';
        a.innerHTML = 'Update History';
        const container = L.DomUtil.create('div', 'leaflet-control-history leaflet-control');
        container.appendChild(a);
        L.DomEvent.disableClickPropagation(container);
        return container;
    },
});
new L.Control.HistoryButton({ position: 'topleft' }).addTo(map);

map.addControl(new L.Control.Search({
    layer: searchablePointsLayer,
    propertyName: 'title',
    marker: false,
    textPlaceholder: 'Cari nama lokasi...',
    textErr: 'Lokasi tidak ditemukan',
    moveToLocation: function(latlng, title, map) {
        map.setView(latlng, 10);
    }
}));

// ===== KODE UNTUK MEMUAT FILE GEOJSON STATIS =====
// Kita akan memuat file SKKL dan menambahkannya ke layer group 'submarineCable'
fetch('/static/data/skklmap.geojson')
    .then(response => {
        if (!response.ok) throw new Error('File skklmap.geojson tidak ditemukan');
        return response.json();
    })
    .then(data => {
        L.geoJSON(data, {
            style: { color: "#d3f462", weight: 2, dashArray: "4 4", opacity: 0.7 }
        }).addTo(groupLayers.submarineCable); // Ditambahkan ke layer group yang benar
        console.log("File skklmap.geojson berhasil dimuat dan ditambahkan ke kontrol layer.");
    })
    .catch(error => console.error('Gagal memuat file skklmap.geojson:', error));