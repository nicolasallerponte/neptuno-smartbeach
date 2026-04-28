/* ================================================================
   NEPTUNO - Alerts Panel
   Polls /api/alerts every 30 seconds and renders alert cards
   ================================================================ */

const NeptunoAlerts = {
    intervalId: null,
    POLL_INTERVAL: 30000, // 30 seconds

    init() {
        this.startPolling();
    },

    startPolling() {
        // Initial fetch
        this.refresh();
        // Periodic polling
        this.intervalId = setInterval(() => this.refresh(), this.POLL_INTERVAL);
    },

    stopPolling() {
        if (this.intervalId) {
            clearInterval(this.intervalId);
            this.intervalId = null;
        }
    },

    async refresh() {
        const alerts = await NeptunoApp.fetchJSON('/api/alerts');
        this.render(alerts || []);

        // Update badge
        const count = alerts ? alerts.length : 0;
        NeptunoApp.alertCount = count;
        const badge = document.getElementById('alert-badge');
        if (badge) {
            if (count > 0) {
                badge.textContent = count;
                badge.style.display = 'inline-block';
            } else {
                badge.style.display = 'none';
            }
        }

        // Update timestamp
        const updatedEl = document.getElementById('alerts-updated');
        if (updatedEl) {
            const now = new Date();
            updatedEl.textContent = `Actualizado: ${now.toLocaleTimeString()} · cada 30s`;
        }
    },

    render(alerts) {
        const listEl = document.getElementById('alerts-list');
        const emptyEl = document.getElementById('alerts-empty');
        if (!listEl) return;

        if (alerts.length === 0) {
            listEl.innerHTML = '';
            if (emptyEl) {
                listEl.appendChild(emptyEl);
                emptyEl.style.display = 'block';
            }
            return;
        }

        // Hide empty state
        if (emptyEl) emptyEl.style.display = 'none';

        listEl.innerHTML = alerts.map(alert => this._renderAlertCard(alert)).join('');
    },

    _sourceClass(src) {
        const map = { MLModel: 'ml', IoTSensor: 'iot', CVSystem: 'cv', Citizen: 'citizen' };
        return map[src] || 'iot';
    },

    _renderAlertCard(alert) {
        const severity = (alert.severity || 'low').toLowerCase();
        const source = alert.alertSource || 'IoTSensor';
        const name = alert.name || 'Alerta';
        const description = alert.description || '';
        const dateIssued = alert.dateIssued || '';
        const beach = (alert.refPointOfInterest || '').split(':').pop();

        const formattedDate = dateIssued ? new Date(dateIssued).toLocaleString('es-ES') : '';
        const srcClass = this._sourceClass(source);

        return `
            <div class="alert-card severity-${severity}">
                <div class="alert-card-top">
                    <div class="alert-card-title">${this._escapeHtml(name)}</div>
                    <span class="severity-tag ${severity}">${severity.toUpperCase()}</span>
                </div>
                <div class="alert-card-description">${this._escapeHtml(description)}</div>
                <div class="alert-card-meta">
                    <span class="source-tag ${srcClass}">${source}</span>
                    ${beach ? `<span style="color:var(--text-secondary)">📍 ${this._escapeHtml(beach)}</span>` : ''}
                    ${formattedDate ? `<span style="color:var(--text-muted)">${formattedDate}</span>` : ''}
                </div>
            </div>
        `;
    },

    _escapeHtml(str) {
        const div = document.createElement('div');
        div.textContent = str;
        return div.innerHTML;
    }
};

document.addEventListener('DOMContentLoaded', () => NeptunoAlerts.init());
