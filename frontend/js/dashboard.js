/* dashboard.js — Charts and statistics */

let categoryChartInst = null;
let activityChartInst = null;

document.getElementById('refreshDashBtn').addEventListener('click', loadDashboard);

async function loadDashboard() {
  try {
    const res = await fetch(`${API_BASE}/api/stats`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    renderStats(data);
    renderActivityChart(data.hourly_trend);
    renderRecentThreats(data.recent_threats);
    updateTopCountries(data.top_countries);
    updateMapHeatmap(data.country_blocks);
  } catch (err) {
    showToast('Could not load dashboard data. Is the API running?', 'error');
  }
}

// ── Stat Counters ────────────────────────────────────────────
function renderStats(data) {
  animateCount('statTotal',     data.total_scans);
  animateCount('statBlocked',   data.blocked_count);
  document.getElementById('statBlockRate').textContent = `${data.block_rate}%`;
  animateCount('statSafe',      data.safe_count);
}

function animateCount(id, target) {
  const el = document.getElementById(id);
  if (!el) return;
  const start = parseInt(el.textContent) || 0;
  const duration = 800;
  const startTime = performance.now();
  function step(now) {
    const p = Math.min((now - startTime) / duration, 1);
    el.textContent = Math.round(start + (target - start) * easeOut(p));
    if (p < 1) requestAnimationFrame(step);
  }
  requestAnimationFrame(step);
}
function easeOut(t) { return 1 - Math.pow(1 - t, 3); }

// ── Donut Chart ───────────────────────────────────────────────
function renderCategoryChart(categories) {
  const ctx = document.getElementById('categoryChart').getContext('2d');
  const labels = categories.map(c => c.category.replace(/_/g,' '));
  const counts  = categories.map(c => c.count);
  const colors  = categories.map(c => c.color);

  if (categoryChartInst) categoryChartInst.destroy();

  categoryChartInst = new Chart(ctx, {
    type: 'doughnut',
    data: { labels, datasets: [{ data: counts, backgroundColor: colors.map(c => c + '99'), borderColor: colors, borderWidth: 2, hoverOffset: 8 }] },
    options: {
      responsive: true, maintainAspectRatio: false,
      cutout: '70%',
      plugins: {
        legend: { display: false },
        tooltip: {
          backgroundColor: 'rgba(14,20,38,0.95)',
          borderColor: 'rgba(77,159,255,0.2)',
          borderWidth: 1,
          titleColor: '#e8edf5',
          bodyColor: '#8896b3',
          callbacks: {
            label: ctx => ` ${ctx.parsed} scan${ctx.parsed !== 1 ? 's' : ''}`
          }
        }
      },
      animation: { animateRotate: true, duration: 800 }
    }
  });

  // Custom legend
  const legendEl = document.getElementById('categoryLegend');
  legendEl.innerHTML = categories.map(c => `
    <div class="legend-item">
      <div class="legend-dot" style="background:${c.color}"></div>
      <span>${c.category.replace(/_/g,' ')} (${c.count})</span>
    </div>
  `).join('');
}

// ── Line/Bar Activity Chart ────────────────────────────────────
function renderActivityChart(hourly) {
  const ctx = document.getElementById('activityChart').getContext('2d');
  const labels  = hourly.map(h => h.hour);
  const safeArr = hourly.map(h => h.safe);
  const blocArr = hourly.map(h => h.blocked);

  if (activityChartInst) activityChartInst.destroy();

  activityChartInst = new Chart(ctx, {
    type: 'line',
    data: {
      labels,
      datasets: [
        {
          label: 'Safe',
          data: safeArr,
          borderColor: '#00ff88',
          backgroundColor: 'rgba(0,255,136,0.08)',
          borderWidth: 2,
          fill: true,
          tension: 0.4,
          pointRadius: 3,
          pointBackgroundColor: '#00ff88',
        },
        {
          label: 'Blocked',
          data: blocArr,
          borderColor: '#ff3366',
          backgroundColor: 'rgba(255,51,102,0.08)',
          borderWidth: 2,
          fill: true,
          tension: 0.4,
          pointRadius: 3,
          pointBackgroundColor: '#ff3366',
        }
      ]
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      interaction: { mode: 'index', intersect: false },
      plugins: {
        legend: {
          labels: { color: '#8896b3', font: { size: 12 }, boxWidth: 12, boxHeight: 12 }
        },
        tooltip: {
          backgroundColor: 'rgba(14,20,38,0.95)',
          borderColor: 'rgba(77,159,255,0.2)',
          borderWidth: 1,
          titleColor: '#e8edf5',
          bodyColor: '#8896b3',
        }
      },
      scales: {
        x: {
          grid: { color: 'rgba(255,255,255,0.04)' },
          ticks: { color: '#4a5568', maxTicksLimit: 12, font: { size: 10 } }
        },
        y: {
          grid: { color: 'rgba(255,255,255,0.04)' },
          ticks: { color: '#4a5568', precision: 0, font: { size: 10 } },
          beginAtZero: true
        }
      }
    }
  });
}

// ── Recent Threats Table ──────────────────────────────────────
function renderRecentThreats(threats) {
  const tbody = document.getElementById('recentThreatsBody');
  if (!threats || !threats.length) {
    tbody.innerHTML = '<tr><td colspan="6" class="empty-state">No threats blocked yet.</td></tr>';
    return;
  }
  tbody.innerHTML = threats.map(t => `
    <tr>
      <td style="font-family:var(--font-mono);color:var(--text-muted)">#${t.id}</td>
      <td style="max-width:300px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;font-family:var(--font-mono);font-size:12px">${t.prompt_preview}</td>
      <td>${getCategoryTag(t.category)}</td>
      <td style="font-family:var(--font-mono)">${t.confidence}%</td>
      <td>${getRiskBadge(t.risk_score)}</td>
      <td style="font-size:12px;color:var(--text-muted)">${formatDateTime(t.timestamp)}</td>
    </tr>
  `).join('');
}

// Auto-refresh every 30s when dashboard is visible
setInterval(() => {
  const dash = document.getElementById('view-dashboard');
  if (dash && dash.classList.contains('active')) loadDashboard();
}, 30000);

// ── Live Threat Map (World Map) ──────────────────────────────
let mapProjection;
let mapPath;
let mapSvgGroup;
let mapTooltip;

async function initWorldMap() {
  if (typeof d3 === 'undefined') return;
  const svg = d3.select("#worldMapSvg");
  const width = svg.node().getBoundingClientRect().width || 800;
  const height = svg.node().getBoundingClientRect().height || 360;
  
  svg.selectAll("*").remove();
  
  mapProjection = d3.geoNaturalEarth1()
    .scale(width / 5.5)
    .translate([width / 2, height / 2]);
    
  mapPath = d3.geoPath().projection(mapProjection);
  mapSvgGroup = svg.append("g");

  // Create tooltip div
  if (!mapTooltip) {
      mapTooltip = d3.select("body").append("div")
        .attr("class", "map-tooltip")
        .style("opacity", 0)
        .style("position", "absolute")
        .style("background", "rgba(14,20,38,0.95)")
        .style("border", "1px solid rgba(255, 51, 102, 0.4)")
        .style("padding", "8px 12px")
        .style("border-radius", "4px")
        .style("color", "#e8edf5")
        .style("font-size", "12px")
        .style("pointer-events", "none")
        .style("z-index", "9999");
  }

  try {
    const world = await d3.json("https://unpkg.com/world-atlas@2.0.2/countries-110m.json");
    const countries = topojson.feature(world, world.objects.countries).features;
    
    mapSvgGroup.selectAll("path")
      .data(countries)
      .enter()
      .append("path")
      .attr("d", mapPath)
      .attr("fill", "rgba(77, 159, 255, 0.05)")
      .attr("stroke", "rgba(77, 159, 255, 0.2)")
      .attr("stroke-width", 1);
  } catch(e) {
    console.error("Failed to load world map data", e);
  }
}

setTimeout(initWorldMap, 500);
window.addEventListener('resize', initWorldMap);

let currentCountryBlocks = {};

function updateMapHeatmap(country_blocks) {
  if (!country_blocks) return;
  currentCountryBlocks = country_blocks;
  if (!mapSvgGroup) return;
  
  mapSvgGroup.selectAll("path")
    .attr("fill", d => {
        const name = d.properties.name;
        // In reality, geojs might return "United States" while topojson uses "United States of America".
        // A robust app maps these, but for our local demo we'll just do a direct lookup.
        const blocks = currentCountryBlocks[name] || currentCountryBlocks[name.replace(" of America", "")] || 0;
        return blocks > 0 ? `rgba(255, 51, 102, ${Math.min(0.2 + blocks * 0.1, 0.9)})` : "rgba(77, 159, 255, 0.05)";
    })
    .on("mouseover", function(event, d) {
        const name = d.properties.name;
        const blocks = currentCountryBlocks[name] || currentCountryBlocks[name.replace(" of America", "")] || 0;
        if (blocks > 0) {
            d3.select(this).attr("stroke", "#ff3366").attr("stroke-width", 2);
            mapTooltip.transition().duration(200).style("opacity", 1);
            mapTooltip.html(`<strong style="color:var(--danger)">${name}</strong><br/>Blocked Attacks: ${blocks}`)
                .style("left", (event.pageX + 15) + "px")
                .style("top", (event.pageY - 30) + "px");
        }
    })
    .on("mouseout", function(event, d) {
        d3.select(this).attr("stroke", "rgba(77, 159, 255, 0.2)").attr("stroke-width", 1);
        mapTooltip.transition().duration(200).style("opacity", 0);
    });
}

function updateTopCountries(top_countries) {
  const feedList = document.getElementById('feedList');
  const overlayTitle = document.querySelector('.map-overlay .section-title');
  if (overlayTitle) overlayTitle.textContent = "TOP 5 ATTACKING COUNTRIES";
  
  if (!feedList) return;
  if (!top_countries || !top_countries.length) {
    feedList.innerHTML = '<div class="feed-item" style="color:var(--text-muted)">No threats detected yet...</div>';
    return;
  }
  
  feedList.innerHTML = top_countries.map((t, idx) => `
      <div class="feed-item" style="display:flex; justify-content: space-between; align-items: center;">
        <div>
          <span style="color:var(--danger); font-weight: bold; margin-right: 5px;">#${idx + 1}</span> 
          ${t.country} 
        </div>
        <span style="color:var(--text-muted); font-size: 11px;">${t.count} Blocks</span>
      </div>
  `).join('');
}
