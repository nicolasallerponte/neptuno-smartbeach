/* ================================================================
   NEPTUNO - Leaflet Map
   Dark-themed beach detail map with markers
   ================================================================ */

const NeptunoMap = {
    map: null,
    marker: null,

    init(lat, lon, name, occupation) {
        if (typeof L === 'undefined') return;

        // Destroy previous map if exists
        if (this.map) {
            this.map.remove();
            this.map = null;
        }

        const container = document.getElementById('beach-map');
        if (!container) return;

        // Reset container
        container.innerHTML = '';
        container.style.height = '350px';

        this.map = L.map('beach-map', {
            center: [lat, lon],
            zoom: 14,
            zoomControl: true,
            attributionControl: true,
        });

        // CartoDB Light: fondo limpio y neutro
        L.tileLayer('https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png', {
            attribution: '&copy; <a href="https://carto.com/">CARTO</a> | &copy; <a href="https://www.openstreetmap.org/copyright">OSM</a>',
            subdomains: 'abcd',
            maxZoom: 19,
        }).addTo(this.map);

        // Custom marker icon
        const markerIcon = L.divIcon({
            className: 'neptuno-marker',
            html: '<div style="width:26px;height:26px;background:linear-gradient(135deg,#06A3B7,#1565C0);border-radius:50%;border:3px solid rgba(255,255,255,0.9);box-shadow:0 3px 14px rgba(6,163,183,0.5);"></div>',
            iconSize: [24, 24],
            iconAnchor: [12, 12],
        });

        this.marker = L.marker([lat, lon], { icon: markerIcon }).addTo(this.map);
        this.marker.bindPopup(`<b>${name}</b>`).openPopup();

        // Beach area circle
        L.circle([lat, lon], {
            radius: 300,
            color: '#06A3B7',
            fillColor: '#06A3B7',
            fillOpacity: 0.08,
            weight: 1,
            opacity: 0.3,
        }).addTo(this.map);

        // Heatmap simulation (crowd density visualization)
        this._addDensityOverlay(lat, lon, occupation);

        // Force resize after small delay
        setTimeout(() => {
            if (this.map) this.map.invalidateSize();
        }, 200);
    },

    _addDensityOverlay(lat, lon, occupation) {
        // Crowd density overlay — color scales from green (low) to red (high)
        const pct = Math.min(100, Math.max(0, parseFloat(occupation) || 30));
        let fillColor;
        if (pct < 40) fillColor = '#059669';
        else if (pct < 70) fillColor = '#F59E0B';
        else fillColor = '#E05C3A';

        const baseOpacity = 0.04 + (pct / 100) * 0.14;

        for (let i = 0; i < 8; i++) {
            const dlat = (Math.random() - 0.5) * 0.003;
            const dlon = (Math.random() - 0.5) * 0.004;
            L.circle([lat + dlat, lon + dlon], {
                radius: 40 + Math.random() * 80,
                color: 'transparent',
                fillColor: fillColor,
                fillOpacity: baseOpacity + Math.random() * 0.05,
                weight: 0,
            }).addTo(this.map);
        }
    },

    destroy() {
        if (this.map) {
            this.map.remove();
            this.map = null;
        }
    }
};
