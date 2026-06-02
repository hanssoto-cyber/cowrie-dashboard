// Auto-refresh cada 30 segundos
let refreshInterval = 30;
let countdown = refreshInterval;

function updateCountdown() {
    const el = document.getElementById('countdown');
    if (el) {
        el.textContent = countdown;
        countdown--;
        if (countdown < 0) {
            countdown = refreshInterval;
            fetchDashboardData();
        }
    }
}

// Fetch datos del dashboard via AJAX
function fetchDashboardData() {
    fetch('/api/stats/')
        .then(res => res.json())
        .then(data => {
            updateStats(data);
            updateTable(data.recent_attacks);
            if (window.attackMap) updateMap(data.geolocations);
            if (window.hourlyChart) updateChart(data.hourly);
        })
        .catch(err => console.log('Error fetching data:', err));
}

function updateStats(data) {
    const fields = {
        'total-connections': data.total_connections,
        'unique-ips': data.unique_ips,
        'login-success': data.login_success,
        'login-failed': data.login_failed,
    };
    for (const [id, val] of Object.entries(fields)) {
        const el = document.getElementById(id);
        if (el) el.textContent = val;
    }
}

function updateTable(attacks) {
    const tbody = document.getElementById('attacks-tbody');
    if (!tbody || !attacks) return;
    tbody.innerHTML = attacks.map(a => `
        <tr>
            <td><span class="accent">${a.src_ip}</span></td>
            <td>${a.username || '-'}</td>
            <td>${a.password || '-'}</td>
            <td>${a.country || 'Desconocido'}</td>
            <td><span class="badge ${a.success ? 'badge-red' : 'badge-green'}">
                ${a.success ? 'ÉXITO' : 'FALLIDO'}
            </span></td>
            <td style="color:var(--text-muted)">${a.timestamp}</td>
        </tr>
    `).join('');
}

function updateMap(geolocations) {
    if (!window.attackMap || !geolocations) return;
    window.markersLayer.clearLayers();
    geolocations.forEach(geo => {
        if (geo.lat && geo.lon) {
            L.circleMarker([geo.lat, geo.lon], {
                radius: 6,
                fillColor: '#00d9ff',
                color: '#00d9ff',
                weight: 1,
                opacity: 0.8,
                fillOpacity: 0.5
            }).bindPopup(`
                <div style="font-family:JetBrains Mono,monospace;font-size:12px">
                    <b style="color:#00d9ff">${geo.ip}</b><br>
                    ${geo.country || 'Desconocido'}<br>
                    ${geo.city || ''}
                </div>
            `).addTo(window.markersLayer);
        }
    });
}

function updateChart(hourly) {
    if (!window.hourlyChart || !hourly) return;
    window.hourlyChart.data.labels = hourly.map(h => h.hour);
    window.hourlyChart.data.datasets[0].data = hourly.map(h => h.count);
    window.hourlyChart.update();
}

// Iniciar countdown
setInterval(updateCountdown, 1000);