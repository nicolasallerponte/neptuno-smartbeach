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
                badge.style.display = 'inline-grid';
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

    _sourceLabel(src) {
        const map = { MLModel: 'Modelo ML', IoTSensor: 'Sensor IoT', CVSystem: 'Sistema CV', Citizen: 'Ciudadano' };
        return map[src] || src;
    },

    _renderAlertCard(alert) {
        const severity = (alert.severity || 'low').toLowerCase();
        const source = alert.alertSource || 'IoTSensor';
        const name = alert.name || 'Alerta';
        const description = alert.description || '';
        const dateIssued = alert.dateIssued || '';
        const beach = (alert.refPointOfInterest || '').split(':').pop();

        const severityLabel = { low: 'Bajo', medium: 'Medio', high: 'Alto' }[severity] || severity;
        const formattedDate = dateIssued
            ? new Date(dateIssued).toLocaleString('es-ES', { day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit' })
            : '';

        const metaParts = [this._escapeHtml(this._sourceLabel(source))];
        if (beach) metaParts.push(this._escapeHtml(beach));
        if (formattedDate) metaParts.push(formattedDate);

        return `
            <div class="alert-card severity-${severity}">
                <div class="alert-card-top">
                    <div class="alert-card-title">${this._escapeHtml(name)}</div>
                    <span class="alert-level ${severity}">${severityLabel}</span>
                </div>
                <div class="alert-card-description">${this._escapeHtml(description)}</div>
                <div class="alert-card-meta">${metaParts.join(' · ')}</div>
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
