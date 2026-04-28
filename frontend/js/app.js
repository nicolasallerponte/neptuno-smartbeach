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
            const waveH = sea.waveHeight != null ? `${sea.waveHeight}m` : '--';

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
                    <div class="beach-card-label">olas</div>
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
            {id:'Riazor', name:'Playa de Riazor', city:'A Coruna'},
            {id:'Orzan', name:'Playa de Orzan', city:'A Coruna'},
            {id:'Doninos', name:'Praia de Doninos', city:'Ferrol'},
            {id:'Valdovino', name:'Praia de Valdovino', city:'Valdovino'},
            {id:'Pantin', name:'Praia de Pantin', city:'Cedeira'},
            {id:'Caion', name:'Praia de Caion', city:'A Laracha'},
            {id:'Baldaio', name:'Praia de Baldaio', city:'Carballo'},
            {id:'Malpica', name:'Playa de Malpica', city:'Malpica'},
            {id:'Cabanas', name:'Praia de Cabanas', city:'Cabanas'},
            {id:'Carnota', name:'Praia de Carnota', city:'Carnota'},
            {id:'Larino', name:'Praia de Larino', city:'Carnota'},
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
        ['val-temp','val-waves','val-wind','val-water','val-uv','val-occupation']
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

        // Color-code condition cards
        this._colorCard('card-waves', sea.waveHeight, 1.5, 2.5);
        this._colorCard('card-water', ecoli, 200, 500);
        this._colorCard('card-uv', weather.uVIndexMax, 6, 9);

        // Update map coords badge
        const location = this.extractValue(detail, 'location');
        const coords = location ? location.coordinates : [-8.42, 43.37];
        const mapCoords = document.getElementById('map-coords');
        if (mapCoords && coords) mapCoords.textContent = `${coords[1].toFixed(4)}, ${coords[0].toFixed(4)}`;

        const gmLink = document.getElementById('googlemaps-link');
        if (gmLink && coords) gmLink.href = `https://www.google.com/maps?q=${coords[1]},${coords[0]}`;

        if (coords && typeof NeptunoMap !== 'undefined') {
            NeptunoMap.init(coords[1], coords[0], name, this.extractValue(detail, 'occupationRate'));
        }

        if (typeof NeptunoCharts !== 'undefined') NeptunoCharts.loadAll(beachId, weather, sea);
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
            dot.className = 'status-dot connected';
            text.textContent = data.ollama === 'connected' ? 'Conectado · IA activa' : 'Conectado';
        } else if (data === null) {
            dot.className = 'status-dot error';
            text.textContent = 'Backend offline';
        } else {
            dot.className = 'status-dot error';
            text.textContent = 'Error';
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

    _esc(str) {
        const d = document.createElement('div');
        d.textContent = str || '';
        return d.innerHTML;
    }
};

document.addEventListener('DOMContentLoaded', () => NeptunoApp.init());
