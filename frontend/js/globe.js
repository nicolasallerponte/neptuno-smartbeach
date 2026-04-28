/* ================================================================
   NEPTUNO - Mapa Costero A Coruna
   Leaflet · CartoDB Light · marcadores animados
   ================================================================ */

const NeptunoGlobe = {
    map: null,
    markerLayer: null,
    pendingBeaches: null,
    initialized: false,

    CENTER: [43.28, -8.60],
    ZOOM: 9,

    init() {
        if (this.initialized) return;
        if (typeof L === 'undefined') return;

        const container = document.getElementById('globe-container');
        if (!container) return;

        // Crear el div del mapa si no existe en el HTML
        let mapDiv = document.getElementById('coast-map');
        if (!mapDiv) {
            mapDiv = document.createElement('div');
            mapDiv.id = 'coast-map';
            container.insertBefore(mapDiv, container.firstChild);
        }

        // Asegurar que el contenedor tiene altura real antes de inicializar Leaflet
        const rect = container.getBoundingClientRect();
        if (rect.height < 20) {
            requestAnimationFrame(() => { this.initialized = false; this.init(); });
            return;
        }

        this.map = L.map('coast-map', {
            center: this.CENTER,
            zoom: this.ZOOM,
            zoomControl: false,
            attributionControl: false,
            minZoom: 7,
            maxZoom: 17,
        });

        // CartoDB Light: fondo limpio y neutro, los marcadores son el protagonista
        L.tileLayer('https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png', {
            attribution: '&copy; <a href="https://carto.com/">CARTO</a> &copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
            subdomains: 'abcd',
            maxZoom: 19,
        }).addTo(this.map);

        L.control.zoom({ position: 'bottomright' }).addTo(this.map);
        L.control.attribution({ position: 'bottomleft', prefix: 'CARTO · OpenStreetMap' }).addTo(this.map);

        this.markerLayer = L.layerGroup().addTo(this.map);
        this.initialized = true;

        // Pintar playas pendientes si las habia
        if (this.pendingBeaches) {
            this.updateMarkers(this.pendingBeaches);
            this.pendingBeaches = null;
        }
    },

    _popupHtml(name, status, waveStr, tempStr, beachId) {
        const labels = { good: 'Buenas condiciones', warning: 'Condiciones moderadas', danger: 'Precaucion' };
        return `<div class="coast-popup">
            <div class="coast-popup-header status-${status}">
                <span class="coast-popup-name">${NeptunoApp._esc(name)}</span>
                <span class="coast-popup-status">${labels[status] || ''}</span>
            </div>
            <div class="coast-popup-body">
                <div class="coast-popup-row"><span>Altura olas</span><b>${waveStr}</b></div>
                <div class="coast-popup-row"><span>Temperatura mar</span><b>${tempStr}</b></div>
            </div>
            <div class="coast-popup-footer" data-beach="${beachId.replace(/"/g, '')}">Ver condiciones detalladas</div>
        </div>`;
    },

    updateMarkers(beaches) {
        if (!this.initialized || !this.map) {
            this.pendingBeaches = beaches;
            return;
        }

        this.markerLayer.clearLayers();

        beaches.forEach(beach => {
            const loc = NeptunoApp.extractValue(beach, 'location');
            if (!loc || !loc.coordinates) return;

            const [lon, lat] = loc.coordinates;
            const beachId = (beach.id || '').split(':').pop();
            const name = NeptunoApp.extractValue(beach, 'name') || beachId;
            const status = NeptunoApp.getStatusColor(beach);

            const sea = beach.currentSeaConditions || {};
            const waveVal = sea.waveHeight;
            const tempVal = sea.seaSurfaceTemperature;
            const waveStr = waveVal != null ? `${Number(waveVal).toFixed(1)} m` : '--';
            const tempStr = tempVal != null ? `${Number(tempVal).toFixed(1)} °C` : '--';

            const shortName = name.replace(/^(Playa|Praia)\s+de\s+/i, '');
            const initial = shortName.charAt(0).toUpperCase();

            const icon = L.divIcon({
                className: 'coast-marker-wrapper',
                html: `<div class="coast-marker status-${status}">
                    <div class="coast-marker-pulse"></div>
                    <div class="coast-marker-dot"><span class="coast-marker-initial">${initial}</span></div>
                </div>`,
                iconSize: [42, 42],
                iconAnchor: [21, 21],
                popupAnchor: [0, -24],
            });

            const popup = L.popup({
                maxWidth: 230,
                className: 'coast-leaflet-popup',
                closeButton: true,
                autoClose: true,
            }).setContent(this._popupHtml(name, status, waveStr, tempStr, beachId));

            const marker = L.marker([lat, lon], { icon })
                .bindPopup(popup)
                .addTo(this.markerLayer);

            marker.on('popupopen', () => {
                const footer = document.querySelector(`.coast-popup-footer[data-beach="${beachId}"]`);
                if (footer) footer.onclick = () => { window.location.hash = '#beach/' + beachId; };
            });
        });
    },

    onShow() {
        if (!this.initialized) {
            this.init();
        } else {
            setTimeout(() => { if (this.map) this.map.invalidateSize({ animate: false }); }, 80);
        }
    },
};
