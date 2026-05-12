/* ================================================================
   NEPTUNO - Main Application Controller
   Hash-based SPA router, health check, beach sidebar
   ================================================================ */

const API_BASE = '';

const NeptunoApp = {
    beaches: [],
    currentBeach: null,
    alertCount: 0,
    _healthInterval: null,
    _webcamInterval: null,

    // ---- API helpers ----
    async fetchJSON(url) {
        try {
            const resp = await fetch(API_BASE + url);
            if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
            return await resp.json();
        } catch (err) {
            console.warn('API fetch failed:', url, err.message);
            return null;
        }
    },

    showError(msg) {
        const container = document.getElementById('toast-container');
        if (!container) return;
        const toast = document.createElement('div');
        toast.className = 'toast error';
        toast.textContent = msg;
        container.appendChild(toast);
        setTimeout(() => {
            toast.style.animation = 'toastOut 0.3s ease forwards';
            setTimeout(() => toast.remove(), 300);
        }, 4000);
    },

    // ---- Router ----
    init() {
        // Nav link clicks
        document.querySelectorAll('.nav-link').forEach(link => {
            link.addEventListener('click', e => {
                e.preventDefault();
                const view = link.dataset.view;
                if (view) window.location.hash = '#' + view;
                // Close mobile menu
                document.getElementById('nav-links').classList.remove('open');
                document.getElementById('nav-hamburger').setAttribute('aria-expanded', 'false');
            });
        });

        // Hamburger menu
        const hamburger = document.getElementById('nav-hamburger');
        if (hamburger) {
            hamburger.addEventListener('click', () => {
                const links = document.getElementById('nav-links');
                const isOpen = links.classList.toggle('open');
                hamburger.setAttribute('aria-expanded', isOpen ? 'true' : 'false');
            });
        }

        // Brand click -> globe
        document.getElementById('nav-brand').addEventListener('click', () => {
            window.location.hash = '#globe';
        });
        document.getElementById('nav-brand').addEventListener('keydown', e => {
            if (e.key === 'Enter') window.location.hash = '#globe';
        });

        // Back button in beach view
        document.getElementById('back-btn').addEventListener('click', () => {
            window.location.hash = '#globe';
        });

        // Hash change routing
        window.addEventListener('hashchange', () => this.route());

        // Initial route
        if (!window.location.hash) window.location.hash = '#globe';
        this.route();

        // Health check immediately + every 30s
        this.checkHealth();
        this._healthInterval = setInterval(() => this.checkHealth(), 30000);

        // Load beaches
        this.loadBeaches().then(() => this._hideLoadingScreen());
    },

    _hideLoadingScreen() {
        const screen = document.getElementById('loading-screen');
        if (screen) {
            screen.classList.add('hidden');
            setTimeout(() => screen.remove(), 600);
        }
    },

    route() {
        const hash = window.location.hash.slice(1) || 'globe';
        const parts = hash.split('/');
        const viewName = parts[0];

        // Close mobile menu on navigate
        document.getElementById('nav-links').classList.remove('open');

        // Nav active state
        document.querySelectorAll('.nav-link').forEach(link => {
            link.classList.toggle('active', link.dataset.view === viewName);
        });

        // Toggle views
        document.querySelectorAll('.view').forEach(s => s.classList.remove('active'));

        if (viewName === 'beach' && parts[1]) {
            document.getElementById('view-beach').classList.add('active');
            this.openBeach(parts[1]);
        } else if (document.getElementById('view-' + viewName)) {
            document.getElementById('view-' + viewName).classList.add('active');
        } else {
            document.getElementById('view-globe').classList.add('active');
        }

        if (viewName === 'globe' && typeof NeptunoGlobe !== 'undefined') NeptunoGlobe.onShow();
        if (viewName === 'alerts' && typeof NeptunoAlerts !== 'undefined') NeptunoAlerts.refresh();
    },

    async loadBeaches() {
        const data = await this.fetchJSON('/api/beaches');
        if (data && Array.isArray(data)) {
            this.beaches = data;
            console.log(`Loaded ${data.length} beaches from Orion`);
            if (typeof NeptunoGlobe !== 'undefined') NeptunoGlobe.updateMarkers(data);
            this._renderSidebar(data);
        } else {
            // Render sidebar with static fallback names so it's not empty
            this._renderSidebarFallback();
        }
    },

    _renderSidebar(beaches) {
        const list = document.getElementById('sidebar-list');
        if (!list) return;
        list.innerHTML = '';
        const count = document.getElementById('sidebar-count');
        if (count) count.textContent = beaches.length;

        beaches.forEach(beach => {
            const id = beach.id ? beach.id.split(':').pop() : '';
            const name = this.extractValue(beach, 'name') || id;
            const address = this.extractValue(beach, 'address') || {};
            const city = address.addressLocality || '';
            const status = this.getStatusColor(beach);
            const sea = beach.currentSeaConditions || {};
            const weather = beach.currentWeather || {};
            const waveH = sea.waveHeight != null ? `${sea.waveHeight}m` : '--';
            const sst = sea.seaSurfaceTemperature != null ? `${sea.seaSurfaceTemperature}°` : '--';

            const card = document.createElement('div');
            card.className = 'beach-card';
            card.setAttribute('role', 'button');
            card.setAttribute('tabindex', '0');
            card.setAttribute('aria-label', `Open ${name}`);
            card.innerHTML = `
                <div class="beach-card-dot ${status}"></div>
                <div class="beach-card-info">
                    <div class="beach-card-name">${this._esc(name)}</div>
                    <div class="beach-card-city">${this._esc(city)}</div>
                </div>
                <div class="beach-card-meta">
                    <div class="beach-card-wave">${waveH}</div>
                    <div class="beach-card-label">${sst} agua</div>
                </div>
            `;
            card.addEventListener('click', () => {
                window.location.hash = `#beach/${id}`;
            });
            card.addEventListener('keydown', e => {
                if (e.key === 'Enter') window.location.hash = `#beach/${id}`;
            });
            list.appendChild(card);
        });
    },

    _renderSidebarFallback() {
        const beaches = [
            {id:'Riazor', name:'Playa de Riazor', city:'A Coruña'},
            {id:'Orzan', name:'Playa de Orzán', city:'A Coruña'},
            {id:'SantaCristina', name:'Praia de Santa Cristina', city:'Oleiros'},
            {id:'Bastiagueiro', name:'Praia de Bastiagueiro', city:'Oleiros'},
            {id:'Mino', name:'Praia de Miño', city:'Miño'},
            {id:'Cabanas', name:'Praia de Cabanas', city:'Cabanas'},
            {id:'Doninos', name:'Praia de Doniños', city:'Ferrol'},
            {id:'Valdovino', name:'Praia de Valdoviño', city:'Valdoviño'},
            {id:'Pantin', name:'Praia de Pantín', city:'Cedeira'},
            {id:'Sabon', name:'Praia de Sabón', city:'Arteixo'},
            {id:'Caion', name:'Praia de Caión', city:'A Laracha'},
            {id:'Baldaio', name:'Praia de Baldaio', city:'Carballo'},
            {id:'Razo', name:'Praia de Razo', city:'Carballo'},
            {id:'Malpica', name:'Playa de Malpica', city:'Malpica de Bergantiños'},
            {id:'Laxe', name:'Praia de Laxe', city:'Laxe'},
            {id:'Carnota', name:'Praia de Carnota', city:'Carnota'},
            {id:'Larino', name:'Praia de Lariño', city:'Carnota'},
            {id:'Barona', name:'Praia de Barona', city:'Porto do Son'},
        ];
        const list = document.getElementById('sidebar-list');
        if (!list) return;
        list.innerHTML = '';
        beaches.forEach(b => {
            const card = document.createElement('div');
            card.className = 'beach-card';
            card.setAttribute('role', 'button');
            card.setAttribute('tabindex', '0');
            card.innerHTML = `
                <div class="beach-card-dot warning"></div>
                <div class="beach-card-info">
                    <div class="beach-card-name">${this._esc(b.name)}</div>
                    <div class="beach-card-city">${this._esc(b.city)}</div>
                </div>
                <div class="beach-card-meta">
                    <div class="beach-card-wave">--</div>
                    <div class="beach-card-label">sin datos</div>
                </div>
            `;
            card.addEventListener('click', () => { window.location.hash = `#beach/${b.id}`; });
            card.addEventListener('keydown', e => { if (e.key === 'Enter') window.location.hash = `#beach/${b.id}`; });
            list.appendChild(card);
        });
    },

    async openBeach(beachId) {
        this.currentBeach = beachId;

        // Reset UI
        document.getElementById('beach-name').textContent = 'Cargando...';
        document.getElementById('beach-location').textContent = '';
        const badge = document.getElementById('beach-status-badge');
        if (badge) { badge.className = 'beach-status-badge'; badge.textContent = ''; }
        ['val-temp','val-waves','val-wind','val-water','val-uv','val-occupation',
         'val-water-temp','val-pressure','val-gust','val-bath']
            .forEach(id => { const el = document.getElementById(id); if (el) el.textContent = '--'; });

        const detail = await this.fetchJSON(`/api/beaches/${beachId}`);
        if (!detail) {
            document.getElementById('beach-name').textContent = beachId;
            this.showError('No se pudo cargar la playa. Comprueba que Orion esta activo.');
            return;
        }

        // Header
        const name = this.extractValue(detail, 'name') || beachId;
        const address = this.extractValue(detail, 'address');
        document.getElementById('beach-name').textContent = name;
        document.getElementById('beach-location').textContent =
            address ? `${address.addressLocality || ''}, ${address.addressRegion || ''}` : '';

        // Status badge
        const status = this.getStatusColor(detail);
        const statusLabels = { good: 'Buenas condiciones', warning: 'Condiciones moderadas', danger: 'Precaucion' };
        if (badge) { badge.className = `beach-status-badge ${status}`; badge.textContent = statusLabels[status]; }

        // Condition cards
        const weather = detail.currentWeather || {};
        const sea = detail.currentSeaConditions || {};
        const wq = detail.currentWaterQuality || {};

        const setVal = (id, val, unit) => {
            const el = document.getElementById(id);
            if (!el) return;
            el.textContent = val != null ? val : '--';
        };
        setVal('val-temp', weather.temperature != null ? weather.temperature : null);
        setVal('val-waves', sea.waveHeight != null ? sea.waveHeight : null);
        setVal('val-wind', weather.windSpeed != null ? weather.windSpeed : null);
        setVal('val-uv', weather.uVIndexMax != null ? weather.uVIndexMax : null);
        setVal('val-occupation', this.extractValue(detail, 'occupationRate') || null);

        const ecoli = wq.escherichiaColi;
        const ecoliEl = document.getElementById('val-water');
        if (ecoliEl) ecoliEl.textContent = ecoli != null ? ecoli : '--';

        // New enriched fields
        setVal('val-water-temp', sea.seaSurfaceTemperature != null ? sea.seaSurfaceTemperature : null);
        setVal('val-pressure', weather.atmosphericPressure != null ? weather.atmosphericPressure : null);
        setVal('val-gust', weather.windGust != null ? weather.windGust : null);

        // Bathing index (0-5 stars)
        const bathIdx = this._calcBathingIndex(sea.waveHeight, ecoli, weather.uVIndexMax);
        const bathEl = document.getElementById('val-bath');
        if (bathEl) bathEl.textContent = bathIdx != null ? bathIdx : '--';
        this._colorCard('card-bath', 5 - bathIdx, 1.5, 3);

        // Maritime text info
        const maritime = document.getElementById('maritime-info');
        if (maritime) {
            const seaDesc = sea.seaStateDescription;
            const swellDesc = sea.swellDescription;
            const waveRange = sea.waveHeightText;
            if (seaDesc || swellDesc || waveRange) {
                maritime.style.display = '';
                const r1 = document.getElementById('row-sea-state');
                const r2 = document.getElementById('row-swell');
                const r3 = document.getElementById('row-wave-range');
                if (r1 && seaDesc) r1.innerHTML = `<span class="maritime-label">Mar:</span> ${this._esc(seaDesc)}`;
                if (r2 && swellDesc) r2.innerHTML = `<span class="maritime-label">Fondo:</span> ${this._esc(swellDesc)}`;
                if (r3 && waveRange) r3.innerHTML = `<span class="maritime-label">Rango olas:</span> ${this._esc(waveRange)} m`;
            }
        }

        // Color-code condition cards
        this._colorCard('card-waves', sea.waveHeight, 1.5, 2.5);
        this._colorCard('card-water', ecoli, 200, 500);
        this._colorCard('card-uv', weather.uVIndexMax, 6, 9);
        this._colorCard('card-water-temp', 20 - (sea.seaSurfaceTemperature || 15), 4, 7);

        // Update map coords badge
        const location = this.extractValue(detail, 'location');
        const coords = location ? location.coordinates : [-8.42, 43.37];
        const mapCoords = document.getElementById('map-coords');
        if (mapCoords && coords) mapCoords.textContent = `${coords[1].toFixed(4)}, ${coords[0].toFixed(4)}`;

        const gmLink = document.getElementById('googlemaps-link');
        if (gmLink && coords) gmLink.href = `https://www.google.com/maps?q=${coords[1]},${coords[0]}`;

        const earthLink = document.getElementById('earth3d-link');
        if (earthLink && coords) earthLink.href = `https://earth.google.com/web/@${coords[1]},${coords[0]},10a,400d,35y,0h,60t,0r`;

        if (coords && typeof NeptunoMap !== 'undefined') {
            NeptunoMap.init(coords[1], coords[0], name, this.extractValue(detail, 'occupationRate'));
        }

        // Wind direction arrow (rotates to show where wind is coming FROM)
        const windArrow = document.getElementById('val-wind-arrow');
        if (!windArrow) {
            const windCard = document.getElementById('card-wind');
            if (windCard) {
                const arrow = document.createElement('span');
                arrow.id = 'val-wind-arrow';
                arrow.className = 'wind-dir-arrow';
                arrow.style.cssText = 'display:block;font-size:.85rem;color:var(--text-secondary);margin-top:2px';
                windCard.appendChild(arrow);
            }
        }
        if (weather.windDirection != null) {
            const el = document.getElementById('val-wind-arrow');
            if (el) {
                el.textContent = this._windLabel(weather.windDirection);
                el.title = `${weather.windDirection}°`;
            }
        }

        // Forecast strip
        const fc = detail.forecast || {};
        const fcStrip = document.getElementById('forecast-strip');
        if (fcStrip && (fc.temperature || fc.windSpeed != null || fc.precipitationProbability != null)) {
            fcStrip.style.display = '';
            const temp = fc.temperature;
            const fcTempEl = document.getElementById('fc-temp');
            if (fcTempEl && temp) {
                const mn = temp.minimum != null ? temp.minimum : (fc.temperatureMin || '--');
                const mx = temp.maximum != null ? temp.maximum : (fc.temperatureMax || '--');
                fcTempEl.textContent = `${mn} / ${mx}`;
            }
            const fcWindEl = document.getElementById('fc-wind');
            if (fcWindEl && fc.windSpeed != null) fcWindEl.childNodes[0].textContent = `${fc.windSpeed} `;
            const fcWindArrow = document.getElementById('fc-wind-arrow');
            if (fcWindArrow && fc.windDirection != null) {
                fcWindArrow.textContent = this._windLabel(fc.windDirection);
                fcWindArrow.title = `${fc.windDirection}°`;
            }
            const fcPrecipEl = document.getElementById('fc-precip');
            if (fcPrecipEl && fc.precipitationProbability != null)
                fcPrecipEl.textContent = Math.round(fc.precipitationProbability * 100);
            const fcUvEl = document.getElementById('fc-uv');
            if (fcUvEl && fc.uVIndexMax != null) fcUvEl.textContent = fc.uVIndexMax;
        }

        if (typeof NeptunoCharts !== 'undefined') NeptunoCharts.loadAll(beachId, weather, sea);

        // Webcam panel
        this._loadWebcam(beachId);
    },

    async _loadWebcam(beachId) {
        const panel = document.getElementById('webcam-panel');
        if (!panel) return;
        panel.style.display = 'none';
        if (this._webcamInterval) { clearInterval(this._webcamInterval); this._webcamInterval = null; }

        const data = await this.fetchJSON(`/api/beaches/${beachId}/webcam`);
        if (!data || !data.available) return;

        const img = document.getElementById('webcam-img');
        const titleEl = document.getElementById('webcam-title');
        const link = document.getElementById('webcam-windy-link');
        const refreshBtn = document.getElementById('webcam-refresh');

        if (titleEl) titleEl.textContent = data.title || '';
        if (link) link.href = data.player_url || '#';

        const loadSnapshot = () => {
            if (!img) return;
            img.classList.add('loading');
            img.onload = () => img.classList.remove('loading');
            img.onerror = () => { panel.style.display = 'none'; };
            img.src = data.snapshot_url + '?t=' + Date.now();
        };

        if (refreshBtn) refreshBtn.addEventListener('click', loadSnapshot);

        loadSnapshot();
        panel.style.display = '';

        // Auto-refresh every 5 minutes
        this._webcamInterval = setInterval(loadSnapshot, 5 * 60 * 1000);
    },

    _colorCard(cardId, value, warnThresh, dangerThresh) {
        const card = document.getElementById(cardId);
        if (!card || value == null) return;
        card.classList.remove('status-good', 'status-warning', 'status-danger');
        if (value >= dangerThresh) card.classList.add('status-danger');
        else if (value >= warnThresh) card.classList.add('status-warning');
        else card.classList.add('status-good');
    },

    async checkHealth() {
        const data = await this.fetchJSON('/api/health');
        const dot = document.getElementById('status-dot');
        const text = document.getElementById('status-text');
        if (!dot || !text) return;
        if (data && data.status === 'ok') {
            if (data.ollama === 'connected') {
                dot.className = 'status-dot connected';
                text.textContent = 'Conectado · IA activa';
            } else {
                dot.className = 'status-dot warning';
                text.textContent = 'Conectado · IA offline';
            }
        } else if (data === null) {
            dot.className = 'status-dot error';
            text.textContent = 'Backend offline';
        } else {
            dot.className = 'status-dot error';
            text.textContent = 'Error';
        }
        const chatStatus = document.getElementById('chat-status');
        if (chatStatus) {
            chatStatus.textContent = (data && data.ollama === 'connected')
                ? 'Propulsado por Llama 3.1 · Datos en tiempo real de Orion'
                : 'Asistente no disponible · Ollama no está activo';
        }
    },

    // ---- Utility: extract NGSI-LD property value ----
    extractValue(entity, key) {
        const prop = entity[key];
        if (prop == null) return null;
        if (typeof prop === 'object' && 'value' in prop) return prop.value;
        return prop;
    },

    // ---- Utility: beach status color ----
    getStatusColor(beach) {
        const sea = beach.currentSeaConditions || {};
        const wq = beach.currentWaterQuality || {};
        const weather = beach.currentWeather || {};
        const waveH = sea.waveHeight || 0;
        const ecoli = wq.escherichiaColi || 0;
        const uv = weather.uVIndexMax || 0;

        if (waveH > 2.5 || ecoli > 500) return 'danger';
        if (waveH > 1.5 || ecoli > 200 || uv > 8) return 'warning';
        return 'good';
    },

    // Wind direction degrees → compass label
    _windLabel(deg) {
        const dirs = ['N','NE','E','SE','S','SO','O','NO'];
        return dirs[Math.round(deg / 45) % 8];
    },

    // Bathing quality index 0-5 stars
    // wave < 1m → ok, ecoli < 100 → ok, uv < 6 → ok
    _calcBathingIndex(waveH, ecoli, uv) {
        if (waveH == null && ecoli == null && uv == null) return null;
        let score = 5;
        const w = waveH || 0;
        const e = ecoli || 0;
        const u = uv || 0;
        if (w > 2.5) score -= 3;
        else if (w > 1.5) score -= 2;
        else if (w > 1.0) score -= 1;
        if (e > 500) score -= 3;
        else if (e > 200) score -= 2;
        else if (e > 100) score -= 1;
        if (u > 8) score -= 1;
        return Math.max(0, Math.min(5, score));
    },

    _esc(str) {
        const d = document.createElement('div');
        d.textContent = str || '';
        return d.innerHTML;
    }
};

document.addEventListener('DOMContentLoaded', () => NeptunoApp.init());
