/* ================================================================
   NEPTUNO - Chart.js Charts
   Time-series visualizations for beach detail view
   ================================================================ */

const NeptunoCharts = {
    charts: {},

    // Shared chart styling for dark theme
    defaultOptions: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
            legend: {
                display: false,
                labels: { color: '#8B95A3', font: { family: 'Outfit', size: 11 } }
            },
            tooltip: {
                backgroundColor: 'rgba(247,243,236,0.97)',
                titleColor: '#1A1A24',
                bodyColor: '#4A5261',
                borderColor: 'rgba(224,215,204,0.8)',
                borderWidth: 1,
                cornerRadius: 8,
                padding: 10,
                titleFont: { family: 'Outfit', weight: '600' },
                bodyFont: { family: 'Space Mono', size: 11 },
                callbacks: {
                    label: ctx => ` ${ctx.parsed.y}`
                }
            }
        },
        scales: {
            x: {
                ticks: { color: '#8B95A3', font: { family: 'Outfit', size: 10 }, maxTicksLimit: 8 },
                grid: { color: 'rgba(26,26,36,0.05)', drawBorder: false },
            },
            y: {
                ticks: { color: '#8B95A3', font: { family: 'Outfit', size: 10 } },
                grid: { color: 'rgba(26,26,36,0.05)', drawBorder: false },
            }
        },
        elements: {
            point: { radius: 2, hoverRadius: 5 },
            line: { tension: 0.4, borderWidth: 2 },
        },
        animation: {
            duration: 800,
            easing: 'easeOutQuart',
        },
    },

    async loadAll(beachId) {
        const history = await NeptunoApp.fetchJSON(`/api/beaches/${beachId}/history?days=7`);

        this._destroyAll();

        if (history) {
            this._renderTemperatureChart(history);
            this._renderWaveChart(history);
            this._renderEcoliChart(history);
        } else {
            // Generate demo data if no history
            this._renderDemoCharts();
        }

        this._renderOccupationChart();
    },

    _destroyAll() {
        Object.values(this.charts).forEach(c => {
            if (c) c.destroy();
        });
        this.charts = {};
    },

    _extractTimeSeries(history, section, attr) {
        const data = history[section];
        if (!data) return { labels: [], values: [] };

        // QuantumLeap response format
        const index = data.index || [];
        const attributes = data.attributes || [];
        const attrData = attributes.find(a => a.attrName === attr);

        if (attrData && attrData.values) {
            return {
                labels: index.map(t => this._formatTime(t)),
                values: attrData.values,
            };
        }

        return { labels: [], values: [] };
    },

    _formatTime(isoStr) {
        try {
            const d = new Date(isoStr);
            return `${d.getMonth() + 1}/${d.getDate()} ${d.getHours()}:00`;
        } catch {
            return isoStr;
        }
    },

    _renderTemperatureChart(history) {
        const ts = this._extractTimeSeries(history, 'seaConditions', 'seaSurfaceTemperature');
        const canvas = document.getElementById('chart-temperature');
        if (!canvas) return;

        // If no real data, generate demo
        if (ts.labels.length === 0) {
            const demo = this._generateDemoData(168, 14, 19);
            ts.labels = demo.labels;
            ts.values = demo.values;
        }

        this.charts.temperature = new Chart(canvas, {
            type: 'line',
            data: {
                labels: ts.labels,
                datasets: [{
                    label: 'Temperatura del mar',
                    data: ts.values,
                    borderColor: '#1B7FA6',
                    backgroundColor: 'rgba(27,127,166,0.07)',
                    fill: true,
                }]
            },
            options: {
                ...this.defaultOptions,
                plugins: {
                    ...this.defaultOptions.plugins,
                    tooltip: {
                        ...this.defaultOptions.plugins.tooltip,
                        callbacks: { label: ctx => ` ${ctx.parsed.y} °C` }
                    }
                }
            }
        });
    },

    _renderWaveChart(history) {
        const ts = this._extractTimeSeries(history, 'seaConditions', 'waveHeight');
        const canvas = document.getElementById('chart-waves');
        if (!canvas) return;

        if (ts.labels.length === 0) {
            const demo = this._generateDemoData(168, 0.3, 2.5);
            ts.labels = demo.labels;
            ts.values = demo.values;
        }

        this.charts.waves = new Chart(canvas, {
            type: 'line',
            data: {
                labels: ts.labels,
                datasets: [{
                    label: 'Altura de olas',
                    data: ts.values,
                    borderColor: '#B45A0A',
                    backgroundColor: 'rgba(180,90,10,0.07)',
                    fill: true,
                }]
            },
            options: {
                ...this.defaultOptions,
                plugins: {
                    ...this.defaultOptions.plugins,
                    tooltip: {
                        ...this.defaultOptions.plugins.tooltip,
                        callbacks: { label: ctx => ` ${ctx.parsed.y} m` }
                    }
                }
            }
        });
    },

    _renderEcoliChart(history) {
        const ts = this._extractTimeSeries(history, 'waterQuality', 'escherichiaColi');
        const canvas = document.getElementById('chart-ecoli');
        if (!canvas) return;

        if (ts.labels.length === 0) {
            const demo = this._generateDemoData(14, 10, 300);
            ts.labels = demo.labels;
            ts.values = demo.values.map(v => Math.round(v));
        }

        // Color based on EU bathing water directive thresholds
        const colors = ts.values.map(v => {
            if (v < 200) return '#4ade80';
            if (v < 500) return '#facc15';
            return '#f87171';
        });

        this.charts.ecoli = new Chart(canvas, {
            type: 'bar',
            data: {
                labels: ts.labels,
                datasets: [{
                    label: 'E. coli',
                    data: ts.values,
                    backgroundColor: colors.map(c => c + '40'),
                    borderColor: colors,
                    borderWidth: 1,
                    borderRadius: 4,
                }]
            },
            options: {
                ...this.defaultOptions,
                plugins: {
                    ...this.defaultOptions.plugins,
                    tooltip: {
                        ...this.defaultOptions.plugins.tooltip,
                        callbacks: { label: ctx => ` ${ctx.parsed.y} UFC/100ml` }
                    },
                    annotation: {
                        annotations: {
                            line200: {
                                type: 'line',
                                yMin: 200,
                                yMax: 200,
                                borderColor: '#facc15',
                                borderWidth: 1,
                                borderDash: [4, 4],
                                label: { content: 'UE Good (200)', display: true, position: 'end', color: '#facc15', font: { size: 10 }, backgroundColor: 'rgba(26,35,50,0.8)' }
                            },
                            line500: {
                                type: 'line',
                                yMin: 500,
                                yMax: 500,
                                borderColor: '#f87171',
                                borderWidth: 1,
                                borderDash: [4, 4],
                                label: { content: 'UE Sufficient (500)', display: true, position: 'end', color: '#f87171', font: { size: 10 }, backgroundColor: 'rgba(26,35,50,0.8)' }
                            }
                        }
                    }
                }
            }
        });
    },

    _renderOccupationChart() {
        const canvas = document.getElementById('chart-occupation');
        if (!canvas) return;

        // Generate 48h prediction data
        const labels = [];
        const values = [];
        const now = new Date();
        for (let h = 0; h < 48; h++) {
            const t = new Date(now.getTime() + h * 3600000);
            labels.push(`${t.getHours()}:00`);
            // Simulate occupancy pattern: higher during midday
            const hour = t.getHours();
            let base = 10;
            if (hour >= 10 && hour <= 19) {
                base = 20 + 40 * Math.sin(Math.PI * (hour - 10) / 9);
            }
            values.push(Math.round(base + Math.random() * 10));
        }

        this.charts.occupation = new Chart(canvas, {
            type: 'line',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Ocupacion prevista',
                    data: values,
                    borderColor: '#0D6B47',
                    backgroundColor: 'rgba(13,107,71,0.07)',
                    fill: true,
                }]
            },
            options: {
                ...this.defaultOptions,
                plugins: {
                    ...this.defaultOptions.plugins,
                    tooltip: {
                        ...this.defaultOptions.plugins.tooltip,
                        callbacks: { label: ctx => ` ${ctx.parsed.y} %` }
                    }
                },
                scales: {
                    ...this.defaultOptions.scales,
                    y: {
                        ...this.defaultOptions.scales.y,
                        min: 0,
                        max: 100,
                    }
                }
            }
        });
    },

    _renderDemoCharts() {
        // Temperature demo
        const tempDemo = this._generateDemoData(168, 14, 19);
        const tempCanvas = document.getElementById('chart-temperature');
        if (tempCanvas) {
            this.charts.temperature = new Chart(tempCanvas, {
                type: 'line',
                data: {
                    labels: tempDemo.labels,
                    datasets: [{
                        label: 'Sea Temperature (C)',
                        data: tempDemo.values,
                        borderColor: '#7ec8e3',
                        backgroundColor: 'rgba(126, 200, 227, 0.1)',
                        fill: true,
                    }]
                },
                options: { ...this.defaultOptions }
            });
        }

        // Wave demo
        const waveDemo = this._generateDemoData(168, 0.3, 2.5);
        const waveCanvas = document.getElementById('chart-waves');
        if (waveCanvas) {
            this.charts.waves = new Chart(waveCanvas, {
                type: 'line',
                data: {
                    labels: waveDemo.labels,
                    datasets: [{
                        label: 'Wave Height (m)',
                        data: waveDemo.values,
                        borderColor: '#facc15',
                        backgroundColor: 'rgba(250, 204, 21, 0.1)',
                        fill: true,
                    }]
                },
                options: { ...this.defaultOptions }
            });
        }

        // E. coli demo
        const ecoliDemo = this._generateDemoData(14, 10, 300);
        const ecoliCanvas = document.getElementById('chart-ecoli');
        if (ecoliCanvas) {
            const ecoliVals = ecoliDemo.values.map(v => Math.round(v));
            const colors = ecoliVals.map(v => {
                if (v < 200) return '#4ade80';
                if (v < 500) return '#facc15';
                return '#f87171';
            });
            this.charts.ecoli = new Chart(ecoliCanvas, {
                type: 'bar',
                data: {
                    labels: ecoliDemo.labels,
                    datasets: [{
                        label: 'E. coli',
                        data: ecoliVals,
                        backgroundColor: colors.map(c => c + '40'),
                        borderColor: colors,
                        borderWidth: 1,
                        borderRadius: 4,
                    }]
                },
                options: {
                    ...this.defaultOptions,
                    plugins: {
                        ...this.defaultOptions.plugins,
                        tooltip: { ...this.defaultOptions.plugins.tooltip, callbacks: { label: ctx => ` ${ctx.parsed.y} UFC/100ml` } },
                        annotation: {
                            annotations: {
                                line200: { type: 'line', yMin: 200, yMax: 200, borderColor: '#facc15', borderWidth: 1, borderDash: [4, 4], label: { content: 'UE Good (200)', display: true, position: 'end', color: '#facc15', font: { size: 10 }, backgroundColor: 'rgba(26,35,50,0.8)' } },
                                line500: { type: 'line', yMin: 500, yMax: 500, borderColor: '#f87171', borderWidth: 1, borderDash: [4, 4], label: { content: 'UE Sufficient (500)', display: true, position: 'end', color: '#f87171', font: { size: 10 }, backgroundColor: 'rgba(26,35,50,0.8)' } }
                            }
                        }
                    }
                }
            });
        }
    },

    _generateDemoData(count, min, max) {
        const labels = [];
        const values = [];
        const now = new Date();
        for (let i = count; i >= 0; i--) {
            const t = new Date(now.getTime() - i * 3600000);
            labels.push(`${t.getMonth() + 1}/${t.getDate()} ${t.getHours()}:00`);
            const base = (min + max) / 2;
            const amplitude = (max - min) / 2;
            values.push(
                Math.round((base + amplitude * Math.sin(i * 0.2) + (Math.random() - 0.5) * amplitude * 0.5) * 100) / 100
            );
        }
        return { labels, values };
    }
};
