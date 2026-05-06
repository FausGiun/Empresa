/**
 * TrendSight Co. — Decisor de Stock
 * Frontend JS — Consume data.json generado por Python
 */

// ─── ESTADO ───────────────────────────────────────────────────────────────────

let currentData = null;

// ─── UTILIDADES ───────────────────────────────────────────────────────────────
async function abrirFicha(nombre) {
    $('modalTitle').textContent = "Cargando: " + nombre;
    $('productModal').classList.remove('hidden');

    try {
        const res = await fetch(`http://localhost:5000/api/detalle?nombre=${encodeURIComponent(nombre)}`);
        const d = await res.json();

        // Llenamos los datos en el modal
        $('mMaterial').textContent = d.adn.materiales;
        $('mTalles').textContent = d.adn.talles_sugeridos;
        $('mEdad').textContent = d.target.edad;
        $('mCanal').textContent = d.target.canal;
        $('mComp').textContent = d.bi.competencia;
        $('mConf').textContent = d.bi.confianza_modelo;
        $('mSat').textContent = d.bi.satisfaccion;
        $('modalTitle').textContent = "Análisis: " + nombre;

    } catch (err) {
        alert("Error al cargar la ficha técnica");
    }
}

function cerrarModal() {
    $('productModal').classList.add('hidden');
}


let currentCurrency = localStorage.getItem('trendSight_currency') || 'USD';
const EXCHANGE_RATE = 1200; // Valor de referencia 2026

function changeCurrency() {
    currentCurrency = $('currencySelector').value;
    localStorage.setItem('trendSight_currency', currentCurrency);
    
    // Si hay datos cargados, refrescamos la vista sin pedir de nuevo al servidor
    if (currentData) {
        renderResults(currentData);
    }
}

// Reemplazamos formatUSD por una más genérica
function formatPrice(n) {
    if (!n || isNaN(n)) return '—';
    
    if (currentCurrency === 'ARS') {
        const valueARS = n * EXCHANGE_RATE;
        return 'ARS ' + valueARS.toLocaleString('es-AR', { minimumFractionDigits: 0 });
    }
    
    return 'USD ' + Number(n).toLocaleString('en-US', { minimumFractionDigits: 2 });
}


const $ = (id) => document.getElementById(id);

function showState(state) {
  ['stateEmpty', 'stateLoading', 'stateError', 'stateResults'].forEach(id => {
    $(id).classList.toggle('hidden', id !== state);
  });
}

function formatDate(isoString) {
  if (!isoString) return '';
  const d = new Date(isoString);
  return d.toLocaleString('es-AR', {
    day: '2-digit', month: 'short', year: 'numeric',
    hour: '2-digit', minute: '2-digit'
  });
}

function formatNumber(n, decimals = 0) {
  if (n === null || n === undefined || isNaN(n)) return '—';
  return Number(n).toLocaleString('es-AR', {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals
  });
}

function formatUSD(n) {
  if (!n || isNaN(n)) return '—';
  return 'USD ' + formatNumber(n, 2);
}

// ─── LOADING ANIMADO ──────────────────────────────────────────────────────────

function animateLoading() {
  const steps = ['step1', 'step2', 'step3'];
  let i = 0;
  steps.forEach(s => $(s).classList.remove('active', 'done'));
  
  const interval = setInterval(() => {
    if (i > 0) $(steps[i - 1]).classList.replace('active', 'done');
    if (i < steps.length) {
      $(steps[i]).classList.add('active');
      i++;
    } else {
      clearInterval(interval);
    }
  }, 800);
  
  return interval;
}

// ─── BÚSQUEDA PRINCIPAL ────────────────────────────────────────────────────────

async function buscar(termino) {
  const inputEl = $('searchInput');
  const query = termino || inputEl.value.trim();
  
  if (!query) {
    inputEl.focus();
    inputEl.style.borderColor = 'var(--red)';
    setTimeout(() => inputEl.style.borderColor = '', 1500);
    return;
  }

  if (!termino) inputEl.value = query;

  showState('stateLoading');
  const loadInterval = animateLoading();

  // Simular tiempo de procesamiento (el JSON ya fue generado por Python)
  await new Promise(r => setTimeout(r, 2200));
  clearInterval(loadInterval);

  // Activar último step
  ['step1','step2','step3'].forEach(s => {
    $('step' + s.replace('step',''));
    $(s).classList.remove('active');
    $(s).classList.add('done');
  });

  await new Promise(r => setTimeout(r, 400));

  try {
    // Cargar data.json generado por Python
    const response = await fetch('http://localhost:5000/api/analizar?termino=' + encodeURIComponent(query));
    
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    
    currentData = await response.json();
    localStorage.setItem('trendSight_lastResult', JSON.stringify(currentData));
    renderResults(currentData);
    showState('stateResults');
    // Verificar que corresponde al término buscado
    const terminoJson = (currentData?.meta?.termino_buscado || '').toLowerCase();
    const terminoBuscado = query.toLowerCase();
    
    if (terminoJson && terminoJson !== terminoBuscado) {
      // Mostrar advertencia pero continuar con los datos disponibles
      console.warn(`Los datos son para "${terminoJson}", pero buscaste "${terminoBuscado}". Ejecutá el script Python con el término correcto.`);
    }

    renderResults(currentData);
    showState('stateResults');

  } catch (err) {
    $('errorMsg').textContent = `No se encontró data.json o hubo un error: ${err.message}`;
    showState('stateError');
  }
}

// ─── RENDER ───────────────────────────────────────────────────────────────────

function renderResults(data) {
  const { meta, resumen, excel, google_trends, predicciones, productos_muestra } = data;

  // META
  $('metaTermino').textContent = `Análisis: "${meta?.termino_buscado || '—'}"`;
  $('metaFecha').textContent = meta?.fecha_analisis ? formatDate(meta.fecha_analisis) : '';

  // DECISIÓN
  renderDecision(resumen);

  // MÉTRICAS EXCEL
  renderExcelMetrics(excel);

  // GOOGLE TRENDS
  renderTrendsMetrics(google_trends);

  // PREDICCIONES
  renderPredicciones(predicciones);

  // PRODUCTOS
  renderProductos(productos_muestra);

  // TAGS
  renderTags(excel);

  //CHART,GRAFICOO
  renderLystChart(productos_muestra);
}

// ── Decisión ──────────────────────────────────────────────────────────────────

function renderDecision(resumen) {
  if (!resumen) return;

  const badge = $('decisionBadge');
  badge.className = 'decision-badge ' + (resumen.color || 'blue');
  $('decisionIcon').textContent = resumen.icono || '⚡';
  $('decisionText').textContent = resumen.decision || '—';

  $('decisionDescription').textContent = resumen.descripcion || '';

  // Score bar
  const pct = Math.min(100, Math.max(0, resumen.puntaje || 0));
  $('scoreBar').style.width = pct + '%';
  $('scoreBar').className = 'score-bar ' + (resumen.color || 'blue');
  $('scoreValue').textContent = pct + '/100';

  // Razones
  const reasons = $('decisionReasons');
  reasons.innerHTML = '';
  (resumen.razones || []).forEach(r => {
    const div = document.createElement('div');
    div.className = 'reason-item';
    div.textContent = r;
    reasons.appendChild(div);
  });
}

// ── Métricas Excel ────────────────────────────────────────────────────────────

function renderExcelMetrics(excel) {
  if (!excel) return;

  const metrics = [
    {
      label: 'Productos encontrados',
      value: formatNumber(excel.total_productos_encontrados),
      cls: ''
    },
    {
      label: 'Lyst Score promedio',
      value: `${formatNumber(excel.lyst_score, 1)}/100`,
      cls: excel.lyst_score >= 70 ? 'good' : excel.lyst_score >= 45 ? '' : 'warn'
    },
    {
      label: 'Búsquedas semanales (est.)',
      value: formatNumber(excel.busquedas_semanales),
      cls: excel.busquedas_semanales > 50000 ? 'good' : ''
    },
    {
      label: 'Margen bruto promedio',
      value: `${formatNumber(excel.margen_bruto_pct, 1)}%`,
      cls: excel.margen_bruto_pct >= 55 ? 'good' : excel.margen_bruto_pct >= 40 ? '' : 'warn'
    },
    {
      label: 'Precio retail promedio',
      value: formatPrice(excel.precio_retail_prom),
      cls: ''
    },
    {
      label: 'Temporada dominante',
      value: excel.temporada_dominante || '—',
      cls: 'accent'
    },
    {
      label: 'Revenue histórico (cat.)',
      value: excel.revenue_historico > 0 ? 'USD ' + formatNumber(excel.revenue_historico) : '—',
      cls: ''
    },
    {
      label: 'Satisfacción cliente',
      value: excel.satisfaccion_cliente > 0 ? `${formatNumber(excel.satisfaccion_cliente, 1)}/5` : '—',
      cls: excel.satisfaccion_cliente >= 4 ? 'good' : ''
    },
  ];

  const container = $('excelMetrics');
  container.innerHTML = metrics.map(m => `
    <div class="metric-row">
      <span class="metric-label">${m.label}</span>
      <span class="metric-value ${m.cls}">${m.value}</span>
    </div>
  `).join('');
}

// ── Google Trends ─────────────────────────────────────────────────────────────

function renderTrendsMetrics(trends) {
  if (!trends) return;

  const container = $('trendsMetrics');

  if (!trends.disponible) {
    const msg = trends.error || 'No disponible';
    container.innerHTML = `
      <div class="metric-row">
        <span class="metric-label">Estado</span>
        <span class="metric-value warn">Sin datos de Trends</span>
      </div>
      <div class="metric-row">
        <span class="metric-label">Motivo</span>
        <span class="metric-value" style="font-size:11px;color:var(--text-dim)">${msg.substring(0,80)}</span>
      </div>
      <div style="margin-top:12px;padding:12px;background:var(--bg3);border-radius:8px;font-size:12px;color:var(--text-muted)">
        💡 Verificá tu conexión a internet y que pytrends esté instalado.<br>
        Ejecutá: <code style="color:var(--accent)">pip install pytrends</code>
      </div>
    `;
    return;
  }

  const dir = trends.tendencia_direccion || 'estable';
  const dirClass = dir === 'subiendo' ? 'up' : dir === 'bajando' ? 'down' : 'stable';
  const dirIcon = dir === 'subiendo' ? '↑' : dir === 'bajando' ? '↓' : '→';
  const varPct = trends.variacion_pct || 0;
  const varCls = varPct > 5 ? 'good' : varPct < -5 ? 'bad' : '';

  const metrics = [
    {
      label: 'Keywords usadas',
      value: (trends.keywords_usadas || []).join(', ') || '—',
      cls: 'accent'
    },
    {
      label: 'Interés actual (ult. 4 sem.)',
      value: `${trends.interes_actual}/100`,
      cls: trends.interes_actual >= 60 ? 'good' : trends.interes_actual >= 30 ? '' : 'warn'
    },
    {
      label: 'Momentum',
      value: trends.momentum || '—',
      cls: trends.tendencia_direccion === 'subiendo' ? 'good' : trends.tendencia_direccion === 'bajando' ? 'bad' : ''
    },
    {
      label: 'Variación últimas 4 sem.',
      value: (varPct > 0 ? '+' : '') + formatNumber(varPct, 1) + '%',
      cls: varCls
    },
    {
      label: 'Promedio reciente',
      value: `${formatNumber(trends.interes_promedio_reciente, 1)}/100`,
      cls: ''
    },
    {
      label: 'Promedio período anterior',
      value: `${formatNumber(trends.interes_promedio_anterior, 1)}/100`,
      cls: ''
    },
    {
      label: 'Dirección',
      value: `${dirIcon} ${dir}`,
      cls: dirClass === 'up' ? 'good' : dirClass === 'down' ? 'bad' : ''
    },
  ];

  container.innerHTML = metrics.map(m => `
    <div class="metric-row">
      <span class="metric-label">${m.label}</span>
      <span class="metric-value ${m.cls}">${m.value}</span>
    </div>
  `).join('');
}

// ── Predicciones ──────────────────────────────────────────────────────────────

function renderPredicciones(predicciones) {
  const section = $('predSection');
  const grid = $('predGrid');

  if (!predicciones || predicciones.length === 0) {
    section.classList.add('hidden');
    return;
  }

  section.classList.remove('hidden');
  grid.innerHTML = '';

  predicciones.forEach(p => {
    const rec = (p.recomendacion_inversion || '').toLowerCase();
    let recClass = 'monitorear';
    if (rec.includes('prioritaria')) recClass = 'prioritaria';
    else if (rec.includes('moderada')) recClass = 'moderada';
    else if (rec.includes('test') || rec.includes('pequeña')) recClass = 'test';
    else if (rec.includes('evitar')) recClass = 'evitar';

    const card = document.createElement('div');
    card.className = 'pred-card';
    card.innerHTML = `
      <div class="pred-temporada">${p.temporada_objetivo}</div>
      <div class="pred-categoria">${p.categoria} · ${p.subcategoria}</div>
      <div class="pred-tendencia">${p.tendencia}</div>
      <div class="pred-meta">
        <span>🎨 Color: ${p.color_recomendado}</span>
        <span>💰 Precio: ${p.rango_precio}</span>
        <span>🎯 Prob. éxito: ${p.probabilidad_exito}</span>
        <span>⚠️ Riesgo: ${p.nivel_riesgo}</span>
      </div>
      <div class="pred-rec ${recClass}">${p.recomendacion_inversion}</div>
    `;
    grid.appendChild(card);
  });
}

// ── Productos ─────────────────────────────────────────────────────────────────

function renderProductos(productos) {
  const section = $('productsSection');
  const tbody = $('productsBody');

  if (!productos || productos.length === 0) {
    section.classList.add('hidden');
    return;
  }

  section.classList.remove('hidden');
  tbody.innerHTML = '';

  productos.forEach(p => {
    const lyst = p.lyst_score || 0;
    const lystClass = lyst >= 75 ? 'high' : lyst >= 50 ? 'mid' : 'low';

    const tr = document.createElement('tr');
    tr.style.cursor = 'pointer';
    tr.onclick = () => {
      abrirFicha(p.nombre);
    };
    tr.innerHTML = `
      <td style="font-weight:500;max-width:200px">${truncate(p.nombre, 40)}</td>
      <td>${p.marca || '—'}</td>
      <td>
        <span style="font-size:11px;padding:2px 8px;border-radius:100px;
          background:rgba(167,139,250,0.08);color:var(--accent)">
          ${p.tendencia || '—'}
        </span>
      </td>
      <td>
        <div class="lyst-badge ${lystClass}">${lyst}</div>
      </td>
      <td>${formatPrice(p.precio_retail)}</td>
      <td style="color:var(--text-muted)">${p.color || '—'}</td>
    `;
    tbody.appendChild(tr);
  });
}

// ── Tags ──────────────────────────────────────────────────────────────────────

function renderTags(excel) {
  renderTagList('marcasTags', excel?.marcas_top || []);
  renderTagList('coloresTags', excel?.colores_top || []);
  renderTagList('tendenciasTags', excel?.tendencias_top || []);
}

function renderTagList(containerId, items) {
  const container = $(containerId);
  if (!container) return;
  container.innerHTML = '';
  if (!items || items.length === 0) {
    container.innerHTML = '<span style="font-size:12px;color:var(--text-dim)">Sin datos</span>';
    return;
  }
  items.forEach((item, i) => {
    const span = document.createElement('span');
    span.className = 'tag';
    span.textContent = item;
    container.appendChild(span);
  });
}

// ─── HELPERS ──────────────────────────────────────────────────────────────────

function truncate(str, max) {
  if (!str) return '—';
  return str.length > max ? str.slice(0, max) + '…' : str;
}

// ─── EVENTOS ──────────────────────────────────────────────────────────────────

document.addEventListener('DOMContentLoaded', () => {
  const input = $('searchInput');

  // 1. Mantenemos el listener del Enter
  input.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') buscar();
  });

  // 2. RECUPERAR DATOS GUARDADOS
  const savedData = localStorage.getItem('trendSight_lastResult');
  
  if (savedData) {
    try {
      currentData = JSON.parse(savedData);
      
      // Si hay datos, los ponemos en el input y renderizamos
      input.value = currentData.meta.termino_buscado || '';
      renderResults(currentData);
      showState('stateResults');
      
      console.log("🚀 Estado recuperado con éxito");
    } catch (e) {
      console.error("Error al parsear datos guardados", e);
      localStorage.removeItem('trendSight_lastResult'); // Limpiamos si está corrupto
    }
  }
});
function renderLystChart(productos) {
  const canvas = document.getElementById('lystChart');
  if (!canvas || !productos || productos.length === 0) return;

  const ctx = canvas.getContext('2d');
  
  // Destruir gráfico previo para evitar solapamientos
  if (window.myChart instanceof Chart) { 
    window.myChart.destroy(); 
  }

  const labels = productos.map(p => p.nombre.length > 15 ? p.nombre.substring(0, 15) + '...' : p.nombre);
  const scores = productos.map(p => p.lyst_score);

  window.myChart = new Chart(ctx, {
    type: 'bar',
    data: {
      labels: labels,
      datasets: [{
        label: 'Lyst Score',
        data: scores,
        backgroundColor: 'rgba(167, 139, 250, 0.5)',
        borderColor: '#a78bfa',
        borderWidth: 1,
        borderRadius: 5
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { display: false } },
      scales: {
        y: { beginAtZero: true, max: 100, grid: { color: 'rgba(255,255,255,0.05)' } },
        x: { grid: { display: false } }
      }
    }
  });
}
