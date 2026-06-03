const data = window.DASHBOARD_DATA;

const state = {
  year: "全部年份",
  pathogen: "流感病毒",
  scene: "全部场景",
  city: "全部省市",
  trendMetric: "ili",
  startWeek: data.meta.minWeek,
  endWeek: data.meta.maxWeek,
  zoom: 100,
};

const els = {
  yearFilter: document.querySelector("#yearFilter"),
  pathogenFilter: document.querySelector("#pathogenFilter"),
  sceneFilter: document.querySelector("#sceneFilter"),
  cityFilter: document.querySelector("#cityFilter"),
  trendMetric: document.querySelector("#trendMetric"),
  startWeek: document.querySelector("#startWeek"),
  endWeek: document.querySelector("#endWeek"),
  zoomRange: document.querySelector("#zoomRange"),
  resetFilters: document.querySelector("#resetFilters"),
  scopeText: document.querySelector("#scopeText"),
  weekRange: document.querySelector("#weekRange"),
  latestRate: document.querySelector("#latestRate"),
  highRiskRows: document.querySelector("#highRiskRows"),
  anomalyCountKpi: document.querySelector("#anomalyCountKpi"),
  trendSubtitle: document.querySelector("#trendSubtitle"),
  metricLegend: document.querySelector("#metricLegend"),
  donutSubtitle: document.querySelector("#donutSubtitle"),
  sceneBarSubtitle: document.querySelector("#sceneBarSubtitle"),
  trendChart: document.querySelector("#trendChart"),
  donutChart: document.querySelector("#donutChart"),
  sceneBarChart: document.querySelector("#sceneBarChart"),
  scatterChart: document.querySelector("#scatterChart"),
  provinceMap: document.querySelector("#provinceMap"),
  correlationList: document.querySelector("#correlationList"),
  riskDistributionChart: document.querySelector("#riskDistributionChart"),
  monthlyDiseaseChart: document.querySelector("#monthlyDiseaseChart"),
  monthlyDiseaseTitle: document.querySelector("#monthlyDiseaseTitle"),
  monthlyDiseaseSubtitle: document.querySelector("#monthlyDiseaseSubtitle"),
  anomalyTimelineChart: document.querySelector("#anomalyTimelineChart"),
  keywordCloud: document.querySelector("#keywordCloud"),
  keywordSubtitle: document.querySelector("#keywordSubtitle"),
  anomalyTable: document.querySelector("#anomalyTable"),
  anomalyCount: document.querySelector("#anomalyCount"),
  tooltip: document.querySelector("#tooltip"),
};

const colors = ["#0f8f8c", "#d98a16", "#4169b2", "#7a5ea7", "#2f8b57", "#c84b42", "#6c7d87"];
const metricLabels = {
  pathogen: "病原体阳性率",
  ili: "ILI%",
  flu_positive: "流感实验室阳性率",
  outbreak: "流感样病例暴发数",
};

function weekCompare(a, b) {
  return data.filters.weeks.indexOf(a) - data.filters.weeks.indexOf(b);
}

function weekInRange(week) {
  return weekCompare(week, state.startWeek) >= 0 && weekCompare(week, state.endWeek) <= 0;
}

function selectedWeeks() {
  return data.filters.weeks.filter((week) => {
    const yearOk = state.year === "全部年份" || String(week).slice(0, 4) === String(state.year);
    return yearOk && weekInRange(week);
  });
}

function latestSelectedWeek() {
  return selectedWeeks().at(-1) || data.meta.maxWeek;
}

function rowYear(row) {
  return String(row.year_week).slice(0, 4);
}

function formatNumber(value, digits = 2) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) return "-";
  const numeric = Number(value);
  if (Math.abs(numeric) >= 10000) return numeric.toLocaleString("zh-CN", { maximumFractionDigits: 0 });
  return numeric.toFixed(digits);
}

function showTooltip(event, html) {
  els.tooltip.innerHTML = html;
  els.tooltip.style.display = "block";
  els.tooltip.style.left = `${event.clientX + 14}px`;
  els.tooltip.style.top = `${event.clientY + 12}px`;
}

function hideTooltip() {
  els.tooltip.style.display = "none";
}

function setupFilters() {
  els.yearFilter.innerHTML = ["全部年份", ...data.filters.years].map((year) => `<option value="${year}">${year}</option>`).join("");
  els.pathogenFilter.innerHTML = data.filters.pathogens
    .map((pathogen) => `<option value="${pathogen}">${pathogen}</option>`)
    .join("");
  if (!data.filters.pathogens.includes(state.pathogen)) state.pathogen = data.filters.pathogens[0];
  els.sceneFilter.innerHTML = ["全部场景", ...data.filters.scenes]
    .map((scene) => `<option value="${scene}">${scene}</option>`)
    .join("");
  els.cityFilter.innerHTML = ["全部省市", ...data.filters.cities].map((city) => `<option value="${city}">${city}</option>`).join("");
  els.startWeek.innerHTML = data.filters.weeks.map((week) => `<option value="${week}">${week}</option>`).join("");
  els.endWeek.innerHTML = data.filters.weeks.map((week) => `<option value="${week}">${week}</option>`).join("");
  syncControls();

  els.yearFilter.addEventListener("change", () => {
    state.year = els.yearFilter.value;
    render();
  });
  els.pathogenFilter.addEventListener("change", () => {
    state.pathogen = els.pathogenFilter.value;
    render();
  });
  els.sceneFilter.addEventListener("change", () => {
    state.scene = els.sceneFilter.value;
    render();
  });
  els.cityFilter.addEventListener("change", () => {
    state.city = els.cityFilter.value;
    render();
  });
  els.trendMetric.addEventListener("change", () => {
    state.trendMetric = els.trendMetric.value;
    render();
  });
  els.startWeek.addEventListener("change", () => {
    state.startWeek = els.startWeek.value;
    if (weekCompare(state.startWeek, state.endWeek) > 0) state.endWeek = state.startWeek;
    syncControls();
    render();
  });
  els.endWeek.addEventListener("change", () => {
    state.endWeek = els.endWeek.value;
    if (weekCompare(state.endWeek, state.startWeek) < 0) state.startWeek = state.endWeek;
    syncControls();
    render();
  });
  els.zoomRange.addEventListener("input", () => {
    state.zoom = Number(els.zoomRange.value);
    renderTrend();
  });
  els.resetFilters.addEventListener("click", () => {
    Object.assign(state, {
      year: "全部年份",
      pathogen: "流感病毒",
      scene: "全部场景",
      city: "全部省市",
      trendMetric: "ili",
      startWeek: data.meta.minWeek,
      endWeek: data.meta.maxWeek,
      zoom: 100,
    });
    if (!data.filters.pathogens.includes(state.pathogen)) state.pathogen = data.filters.pathogens[0];
    syncControls();
    render();
  });
}

function syncControls() {
  els.yearFilter.value = state.year;
  els.pathogenFilter.value = state.pathogen;
  els.sceneFilter.value = state.scene;
  els.cityFilter.value = state.city;
  els.trendMetric.value = state.trendMetric;
  els.startWeek.value = state.startWeek;
  els.endWeek.value = state.endWeek;
  els.zoomRange.value = state.zoom;
}

function filteredTrendRows() {
  return data.respiratoryTrends.filter((row) => {
    const yearOk = state.year === "全部年份" || rowYear(row) === String(state.year);
    const pathogenOk = row.pathogen === state.pathogen;
    const sceneOk = state.scene === "全部场景" || row.scene === state.scene;
    return yearOk && pathogenOk && sceneOk && weekInRange(row.year_week);
  });
}

function filteredRiskRows() {
  return data.riskRows.filter((row) => {
    const yearOk = state.year === "全部年份" || rowYear(row) === String(state.year);
    const cityOk = state.city === "全部省市" || row.city === state.city;
    return yearOk && cityOk && weekInRange(row.year_week);
  });
}

function filteredAnomalies() {
  return data.anomalies.filter((row) => {
    const yearOk = state.year === "全部年份" || String(row.period).slice(0, 4) === String(state.year);
    return yearOk && weekInRange(row.period);
  });
}

function aggregateByWeek(rows) {
  const groups = new Map();
  rows.forEach((row) => {
    if (!groups.has(row.year_week)) groups.set(row.year_week, []);
    groups.get(row.year_week).push(Number(row.value));
  });
  return [...groups.entries()]
    .map(([week, values]) => ({ week, value: values.reduce((sum, value) => sum + value, 0) / values.length }))
    .sort((a, b) => weekCompare(a.week, b.week));
}

function trendPoints() {
  if (state.trendMetric === "pathogen") {
    return aggregateByWeek(filteredTrendRows());
  }
  if (state.trendMetric === "ili") {
    const rows = data.iliSeries.filter((row) => {
      const yearOk = state.year === "全部年份" || rowYear(row) === String(state.year);
      return yearOk && weekInRange(row.year_week);
    });
    return aggregateByWeek(rows.map((row) => ({ year_week: row.year_week, value: row.value })));
  }
  if (state.trendMetric === "flu_positive") {
    const rows = data.fluPositiveSeries.filter((row) => {
      const yearOk = state.year === "全部年份" || rowYear(row) === String(state.year);
      return yearOk && weekInRange(row.year_week);
    });
    return aggregateByWeek(rows.map((row) => ({ year_week: row.year_week, value: row.value })));
  }
  const rows = data.outbreakSeries.filter((row) => {
    const yearOk = state.year === "全部年份" || rowYear(row) === String(state.year);
    return yearOk && weekInRange(row.year_week);
  });
  return rows.map((row) => ({ week: row.year_week, value: row.value })).sort((a, b) => weekCompare(a.week, b.week));
}

function applyZoom(points) {
  if (state.zoom >= 100) return points;
  const keep = Math.max(2, Math.round(points.length * (state.zoom / 100)));
  return points.slice(points.length - keep);
}

function scaleLinear(domainMin, domainMax, rangeMin, rangeMax) {
  const safeMax = domainMax === domainMin ? domainMin + 1 : domainMax;
  return (value) => rangeMin + ((value - domainMin) / (safeMax - domainMin)) * (rangeMax - rangeMin);
}

function buildSvg(width, height, content) {
  return `<svg viewBox="0 0 ${width} ${height}" preserveAspectRatio="none" aria-hidden="true">${content}</svg>`;
}

function renderKpis() {
  const points = trendPoints();
  const latest = points.at(-1);
  const risks = filteredRiskRows();
  const highRisk = risks.filter((row) => row.risk_level === "高风险").length;
  const anomalies = filteredAnomalies();
  els.weekRange.textContent = `${state.startWeek} - ${state.endWeek}`;
  els.latestRate.textContent = latest ? `${formatNumber(latest.value, state.trendMetric === "outbreak" ? 0 : 2)}${state.trendMetric === "outbreak" ? "" : "%"}` : "-";
  els.highRiskRows.textContent = formatNumber(highRisk, 0);
  els.anomalyCountKpi.textContent = formatNumber(anomalies.length, 0);
  els.scopeText.textContent = `${state.year} · ${state.pathogen} · ${state.scene} · ${state.city}`;
}

function renderTrend() {
  const points = applyZoom(trendPoints());
  els.metricLegend.textContent = metricLabels[state.trendMetric];
  els.trendSubtitle.textContent = `${points.length} 个周度点 · ${state.zoom}% 时间窗口`;
  if (!points.length) {
    const hint =
      state.trendMetric === "pathogen"
        ? "当前年份没有急性呼吸道病原体阳性率记录，可切换到 ILI%、流感实验室阳性率或暴发数。"
        : "当前筛选条件下暂无可展示趋势数据。";
    els.trendChart.innerHTML = `<div class="empty">${hint}</div>`;
    return;
  }

  const width = 920;
  const height = 390;
  const margin = { top: 20, right: 24, bottom: 42, left: 58 };
  const values = points.map((point) => Number(point.value));
  const min = Math.min(...values);
  const max = Math.max(...values);
  const pad = (max - min || 1) * 0.1;
  const x = scaleLinear(0, Math.max(points.length - 1, 1), margin.left, width - margin.right);
  const y = scaleLinear(Math.max(0, min - pad), max + pad, height - margin.bottom, margin.top);
  const path = points.map((point, index) => `${index === 0 ? "M" : "L"}${x(index).toFixed(2)},${y(point.value).toFixed(2)}`).join(" ");
  const area = `${path} L${x(points.length - 1)},${height - margin.bottom} L${margin.left},${height - margin.bottom} Z`;
  const peak = points.reduce((best, point) => (point.value > best.value ? point : best), points[0]);
  const latest = points.at(-1);
  const peakIndex = points.indexOf(peak);
  const latestIndex = points.length - 1;
  const yTicks = Array.from({ length: 5 }, (_, index) => Math.max(0, min - pad) + ((max + pad - Math.max(0, min - pad)) * index) / 4);
  const grid = yTicks
    .map((tick) => {
      const yy = y(tick);
      return `<line class="grid-line" x1="${margin.left}" x2="${width - margin.right}" y1="${yy}" y2="${yy}"></line><text class="chart-label" x="8" y="${yy + 4}">${formatNumber(tick, 2)}</text>`;
    })
    .join("");
  const step = Math.max(1, Math.ceil(points.length / 80));
  const dots = points
    .filter((_, index) => index % step === 0)
    .map((point) => {
      const index = points.indexOf(point);
      return `<circle class="dot" cx="${x(index)}" cy="${y(point.value)}" r="3.3" fill="#0f8f8c" data-week="${point.week}" data-value="${formatNumber(point.value, 3)}"></circle>`;
    })
    .join("");

  els.trendChart.innerHTML = buildSvg(
    width,
    height,
    `${grid}
    <line class="axis-line" x1="${margin.left}" x2="${width - margin.right}" y1="${height - margin.bottom}" y2="${height - margin.bottom}"></line>
    <path class="area-fill" d="${area}"></path>
    <path class="trend-line" d="${path}"></path>
    <circle cx="${x(peakIndex)}" cy="${y(peak.value)}" r="5.5" fill="#d98a16" stroke="#fff" stroke-width="2"></circle>
    <text class="chart-label" x="${Math.min(width - 138, x(peakIndex) + 10)}" y="${Math.max(18, y(peak.value) - 10)}">峰值 ${formatNumber(peak.value, 2)}</text>
    <circle cx="${x(latestIndex)}" cy="${y(latest.value)}" r="5.5" fill="#0f8f8c" stroke="#fff" stroke-width="2"></circle>
    <text class="chart-label" x="${Math.max(margin.left, x(latestIndex) - 92)}" y="${Math.max(18, y(latest.value) - 12)}">最新 ${formatNumber(latest.value, 2)}</text>
    ${dots}
    <text class="chart-label" x="${margin.left}" y="${height - 14}">${points[0].week}</text>
    <text class="chart-label" x="${width - margin.right - 66}" y="${height - 14}">${points.at(-1).week}</text>`,
  );
  els.trendChart.querySelectorAll(".dot").forEach((dot) => {
    dot.addEventListener("mousemove", (event) => {
      showTooltip(event, `<b>${dot.dataset.week}</b><br>${metricLabels[state.trendMetric]}：${dot.dataset.value}`);
    });
    dot.addEventListener("mouseleave", hideTooltip);
  });
}

function renderDonut() {
  const latestWeek = latestSelectedWeek();
  const pathogenRows = data.respiratoryTrends
    .filter((row) => row.year_week === latestWeek && (state.scene === "全部场景" || row.scene === state.scene))
    .reduce((acc, row) => {
      if (!acc[row.pathogen]) acc[row.pathogen] = [];
      acc[row.pathogen].push(Number(row.value));
      return acc;
    }, {});
  let items = Object.entries(pathogenRows)
    .map(([name, values]) => ({ name, value: values.reduce((sum, value) => sum + value, 0) / values.length, unit: "%" }))
    .sort((a, b) => b.value - a.value)
    .slice(0, 6);
  let subtitle = "按最新周平均阳性率";
  let tooltipLabel = "平均阳性率";

  if (!items.length) {
    items = data.fluSubtypeSeries
      .filter((row) => row.year_week === latestWeek && row.value > 0)
      .sort((a, b) => b.value - a.value)
      .slice(0, 6)
      .map((row) => ({ name: row.subtype, value: row.value, unit: "%" }));
    subtitle = "该周无急性呼吸道阳性率，显示流感实验室分型比例";
    tooltipLabel = "分型比例";
  }

  els.donutSubtitle.textContent = subtitle;
  if (!items.length) {
    els.donutChart.innerHTML = `<div class="empty">当前筛选周暂无构成数据</div>`;
    return;
  }

  const total = items.reduce((sum, item) => sum + item.value, 0) || 1;
  let offset = 0;
  const segments = items
    .map((item, index) => {
      const fraction = item.value / total;
      const dash = `${(fraction * 100).toFixed(2)} ${(100 - fraction * 100).toFixed(2)}`;
      const segment = `<circle class="donut-segment" cx="90" cy="90" r="62" fill="none" stroke="${colors[index % colors.length]}" stroke-width="24" stroke-dasharray="${dash}" stroke-dashoffset="${(-offset * 100).toFixed(2)}" pathLength="100" transform="rotate(-90 90 90)" data-name="${item.name}" data-label="${tooltipLabel}" data-value="${formatNumber(item.value, 2)}${item.unit}"></circle>`;
      offset += fraction;
      return segment;
    })
    .join("");
  const legend = items
    .map(
      (item, index) => `<div class="donut-legend-item">
        <span class="legend-dot" style="background:${colors[index % colors.length]}"></span>
        <span>${item.name}</span>
        <b>${formatNumber(item.value, 1)}${item.unit}</b>
      </div>`,
    )
    .join("");
  els.donutChart.innerHTML = `${buildSvg(
    180,
    180,
    `<circle cx="90" cy="90" r="62" fill="none" stroke="#edf2f3" stroke-width="24"></circle>
     ${segments}
     <text class="donut-center" x="90" y="86" text-anchor="middle">${latestWeek}</text>
     <text class="donut-caption" x="90" y="106" text-anchor="middle">最新周</text>`,
  )}<div class="donut-legend">${legend}</div>`;
  els.donutChart.querySelectorAll(".donut-segment").forEach((seg) => {
    seg.addEventListener("mousemove", (event) => showTooltip(event, `<b>${seg.dataset.name}</b><br>${seg.dataset.label}：${seg.dataset.value}`));
    seg.addEventListener("mouseleave", hideTooltip);
  });
}

function renderSceneBars() {
  let rows = [];
  if (state.trendMetric === "pathogen") {
    rows = filteredTrendRows().map((row) => ({ group: row.scene, value: row.value, label: "平均阳性率" }));
  }
  if (state.trendMetric === "ili") {
    rows = data.iliSeries
      .filter((row) => {
        const yearOk = state.year === "全部年份" || rowYear(row) === String(state.year);
        return yearOk && weekInRange(row.year_week);
      })
      .map((row) => ({ group: row.region_group, value: row.value, label: "ILI%" }));
  }
  if (state.trendMetric === "flu_positive") {
    rows = data.fluPositiveSeries
      .filter((row) => {
        const yearOk = state.year === "全部年份" || rowYear(row) === String(state.year);
        return yearOk && weekInRange(row.year_week);
      })
      .map((row) => ({ group: row.region_group, value: row.value, label: "流感实验室阳性率" }));
  }
  if (state.trendMetric === "outbreak") {
    rows = data.outbreakSeries
      .filter((row) => {
        const yearOk = state.year === "全部年份" || rowYear(row) === String(state.year);
        return yearOk && weekInRange(row.year_week);
      })
      .map((row) => ({ group: "全国", value: row.value, label: "流感样病例暴发数" }));
  }
  const groups = new Map();
  let valueLabel = "平均阳性率";
  rows.forEach((row) => {
    valueLabel = row.label || valueLabel;
    if (!groups.has(row.group)) groups.set(row.group, []);
    groups.get(row.group).push(Number(row.value));
  });
  const items = [...groups.entries()].map(([scene, values]) => ({ scene, value: values.reduce((sum, v) => sum + v, 0) / values.length }));
  els.sceneBarSubtitle.textContent =
    valueLabel === "平均阳性率"
      ? "门急诊与住院严重病例阳性率"
      : valueLabel === "流感样病例暴发数"
        ? "全国周度暴发数"
        : `${valueLabel}区域对比`;
  if (!items.length) {
    els.sceneBarChart.innerHTML = `<div class="empty">暂无场景对比数据</div>`;
    return;
  }
  const width = 560;
  const height = 290;
  const margin = { top: 20, right: 24, bottom: 52, left: 58 };
  const max = Math.max(...items.map((item) => item.value), 1);
  const y = scaleLinear(0, max * 1.12, height - margin.bottom, margin.top);
  const barW = Math.min(120, (width - margin.left - margin.right) / items.length - 28);
  const bars = items
    .map((item, index) => {
      const x = margin.left + index * ((width - margin.left - margin.right) / items.length) + 18;
      const barH = height - margin.bottom - y(item.value);
      return `<rect class="bar" x="${x}" y="${y(item.value)}" width="${barW}" height="${barH}" rx="5" fill="${colors[index % colors.length]}" data-scene="${item.scene}" data-value="${formatNumber(item.value, 2)}%"></rect>
      <text class="chart-label" x="${x + barW / 2}" y="${height - 28}" text-anchor="middle">${item.scene.slice(0, 8)}</text>
      <text class="chart-label" x="${x + barW / 2}" y="${y(item.value) - 8}" text-anchor="middle">${formatNumber(item.value, 1)}%</text>`;
    })
    .join("");
  els.sceneBarChart.innerHTML = buildSvg(
    width,
    height,
    `<line class="grid-line" x1="${margin.left}" x2="${width - margin.right}" y1="${y(max * 0.5)}" y2="${y(max * 0.5)}"></line>
    <line class="grid-line" x1="${margin.left}" x2="${width - margin.right}" y1="${y(max)}" y2="${y(max)}"></line>
    <text class="chart-label" x="10" y="${y(max * 0.5) + 4}">${formatNumber(max * 0.5, 1)}%</text>
    <text class="chart-label" x="10" y="${y(max) + 4}">${formatNumber(max, 1)}%</text>
    <line class="axis-line" x1="${margin.left}" x2="${width - margin.right}" y1="${height - margin.bottom}" y2="${height - margin.bottom}"></line>${bars}`,
  );
  els.sceneBarChart.querySelectorAll(".bar").forEach((bar) => {
    bar.addEventListener("mousemove", (event) => showTooltip(event, `<b>${bar.dataset.scene}</b><br>平均阳性率：${bar.dataset.value}`));
    bar.addEventListener("mouseleave", hideTooltip);
  });
}

function renderScatter() {
  const rows = filteredRiskRows().filter((row) => Number.isFinite(row.avg_temperature) && Number.isFinite(row.risk_score));
  if (!rows.length) {
    els.scatterChart.innerHTML = `<div class="empty">暂无气象风险数据</div>`;
    return;
  }
  const width = 560;
  const height = 290;
  const margin = { top: 18, right: 24, bottom: 46, left: 58 };
  const xMin = Math.min(...rows.map((row) => row.avg_temperature));
  const xMax = Math.max(...rows.map((row) => row.avg_temperature));
  const yMax = Math.max(...rows.map((row) => row.risk_score), 1);
  const humidityMax = Math.max(...rows.map((row) => row.avg_humidity || 0), 1);
  const x = scaleLinear(xMin, xMax, margin.left, width - margin.right);
  const y = scaleLinear(0, yMax * 1.08, height - margin.bottom, margin.top);
  const r = scaleLinear(0, humidityMax, 3, 13);
  const dots = rows
    .filter((_, index) => index % Math.max(1, Math.ceil(rows.length / 260)) === 0)
    .map((row) => {
      const color = row.risk_level === "高风险" ? "#c84b42" : row.risk_level === "中风险" ? "#d98a16" : "#2f8b57";
      return `<circle class="scatter-dot" cx="${x(row.avg_temperature)}" cy="${y(row.risk_score)}" r="${r(row.avg_humidity || 0)}" fill="${color}" fill-opacity="0.72" data-label="${row.city} ${row.year_week}" data-temp="${formatNumber(row.avg_temperature, 1)}℃" data-risk="${formatNumber(row.risk_score, 2)}" data-humidity="${formatNumber(row.avg_humidity, 1)}%"></circle>`;
    })
    .join("");
  els.scatterChart.innerHTML = buildSvg(
    width,
    height,
    `<line class="axis-line" x1="${margin.left}" x2="${width - margin.right}" y1="${height - margin.bottom}" y2="${height - margin.bottom}"></line>
     <line class="axis-line" x1="${margin.left}" x2="${margin.left}" y1="${margin.top}" y2="${height - margin.bottom}"></line>
     <line class="grid-line" x1="${margin.left}" x2="${width - margin.right}" y1="${y(yMax * 0.5)}" y2="${y(yMax * 0.5)}"></line>
     <text class="chart-label" x="${width / 2 - 34}" y="${height - 10}">平均气温</text>
     <text class="chart-label" x="8" y="16">风险得分</text>
     ${dots}
     <circle cx="${width - 148}" cy="22" r="5" fill="#c84b42"></circle><text class="chart-label" x="${width - 138}" y="26">高风险</text>
     <circle cx="${width - 92}" cy="22" r="5" fill="#d98a16"></circle><text class="chart-label" x="${width - 82}" y="26">中风险</text>
     <circle cx="${width - 36}" cy="22" r="5" fill="#2f8b57"></circle><text class="chart-label" x="${width - 26}" y="26">低</text>`,
  );
  els.scatterChart.querySelectorAll(".scatter-dot").forEach((dot) => {
    dot.addEventListener("mousemove", (event) => {
      showTooltip(event, `<b>${dot.dataset.label}</b><br>气温：${dot.dataset.temp}<br>风险得分：${dot.dataset.risk}<br>湿度：${dot.dataset.humidity}`);
    });
    dot.addEventListener("mouseleave", hideTooltip);
  });
}

function renderProvinceMap() {
  const rows = filteredRiskRows();
  const grouped = new Map();
  rows.forEach((row) => {
    if (!grouped.has(row.city)) grouped.set(row.city, []);
    grouped.get(row.city).push(row);
  });
  const items = [...grouped.entries()]
    .map(([city, values]) => ({
      city,
      score: values.reduce((sum, row) => sum + row.risk_score, 0) / values.length,
      high: values.filter((row) => row.risk_level === "高风险").length,
    }))
    .sort((a, b) => b.score - a.score);
  const max = Math.max(...items.map((item) => item.score), 1);
  els.provinceMap.innerHTML = items
    .map((item) => {
      const intensity = item.score / max;
      const color = intensity > 0.78 ? "#c84b42" : intensity > 0.52 ? "#d98a16" : "#0f8f8c";
      return `<div class="province-tile" style="background:${color}; opacity:${0.72 + intensity * 0.28}" data-city="${item.city}" data-score="${formatNumber(item.score, 2)}" data-high="${item.high}">
        <b>${item.city}</b><span>均分 ${formatNumber(item.score, 1)} · 高风险 ${item.high}</span>
      </div>`;
    })
    .join("");
  els.provinceMap.querySelectorAll(".province-tile").forEach((tile) => {
    tile.addEventListener("mousemove", (event) => {
      showTooltip(event, `<b>${tile.dataset.city}</b><br>平均风险得分：${tile.dataset.score}<br>高风险周记录：${tile.dataset.high}`);
    });
    tile.addEventListener("mouseleave", hideTooltip);
  });
}

function renderRiskDistribution() {
  const rows = filteredRiskRows();
  const levels = ["高风险", "中风险", "低风险"];
  const counts = levels.map((level) => ({ level, value: rows.filter((row) => row.risk_level === level).length }));
  const width = 430;
  const height = 238;
  const margin = { top: 18, right: 20, bottom: 34, left: 54 };
  const max = Math.max(...counts.map((item) => item.value), 1);
  const y = scaleLinear(0, max * 1.12, height - margin.bottom, margin.top);
  const colorMap = { 高风险: "#c84b42", 中风险: "#d98a16", 低风险: "#2f8b57" };
  const barW = 62;
  const bars = counts
    .map((item, index) => {
      const x = margin.left + index * 108;
      const barH = height - margin.bottom - y(item.value);
      return `<rect class="bar" x="${x}" y="${y(item.value)}" width="${barW}" height="${barH}" rx="6" fill="${colorMap[item.level]}" data-level="${item.level}" data-value="${item.value}"></rect>
      <text class="chart-label" x="${x + barW / 2}" y="${height - 12}" text-anchor="middle">${item.level}</text>
      <text class="chart-label" x="${x + barW / 2}" y="${y(item.value) - 8}" text-anchor="middle">${item.value}</text>`;
    })
    .join("");
  els.riskDistributionChart.innerHTML = buildSvg(
    width,
    height,
    `<line class="axis-line" x1="${margin.left}" x2="${width - margin.right}" y1="${height - margin.bottom}" y2="${height - margin.bottom}"></line>${bars}`,
  );
  els.riskDistributionChart.querySelectorAll(".bar").forEach((bar) => {
    bar.addEventListener("mousemove", (event) => showTooltip(event, `<b>${bar.dataset.level}</b><br>城市周度记录：${bar.dataset.value}`));
    bar.addEventListener("mouseleave", hideTooltip);
  });
}

function renderMonthlyDisease() {
  if (state.city !== "全部省市") {
    renderCityRiskSummary();
    return;
  }
  els.monthlyDiseaseTitle.textContent = "重点病种月度发病数";
  const months = [...new Set(data.monthlyDisease.map((row) => row.period_month))].sort();
  const selectedMonth = state.year === "全部年份" ? months.at(-1) : months.filter((month) => month.startsWith(String(state.year))).at(-1);
  const rows = data.monthlyDisease
    .filter((row) => row.period_month === selectedMonth)
    .sort((a, b) => b.cases - a.cases)
    .slice(0, 6);
  if (!rows.length) {
    els.monthlyDiseaseChart.innerHTML = `<div class="empty">当前年份暂无月度病种数据</div>`;
    return;
  }
  els.monthlyDiseaseSubtitle.textContent = `${selectedMonth} 全国主要呼吸道相关病种`;
  const width = 430;
  const height = 238;
  const margin = { top: 12, right: 22, bottom: 18, left: 94 };
  const max = Math.max(...rows.map((row) => row.cases), 1);
  const x = scaleLinear(0, max, margin.left, width - margin.right);
  const rowH = 30;
  const bars = rows
    .map((row, index) => {
      const y = margin.top + index * rowH;
      const barW = x(row.cases) - margin.left;
      return `<text class="chart-label" x="8" y="${y + 18}">${row.disease}</text>
      <rect class="bar" x="${margin.left}" y="${y + 5}" width="${barW}" height="16" rx="5" fill="${colors[index % colors.length]}" data-name="${row.disease}" data-cases="${formatNumber(row.cases, 0)}" data-month="${row.period_month}"></rect>
      <text class="chart-label" x="${Math.min(width - 72, margin.left + barW + 8)}" y="${y + 18}">${formatNumber(row.cases, 0)}</text>`;
    })
    .join("");
  els.monthlyDiseaseChart.innerHTML = buildSvg(width, height, bars);
  els.monthlyDiseaseChart.querySelectorAll(".bar").forEach((bar) => {
    bar.addEventListener("mousemove", (event) => showTooltip(event, `<b>${bar.dataset.name}</b><br>${bar.dataset.month} 发病数：${bar.dataset.cases}`));
    bar.addEventListener("mouseleave", hideTooltip);
  });
}

function renderCityRiskSummary() {
  const rows = filteredRiskRows();
  els.monthlyDiseaseTitle.textContent = "城市周度风险指标";
  if (!rows.length) {
    els.monthlyDiseaseSubtitle.textContent = `${state.city} 城市周度风险指标`;
    els.monthlyDiseaseChart.innerHTML = `<div class="empty">当前城市和周范围暂无风险数据</div>`;
    return;
  }
  const avg = (field) => {
    const values = rows.map((row) => Number(row[field])).filter((value) => Number.isFinite(value));
    return values.length ? values.reduce((sum, value) => sum + value, 0) / values.length : 0;
  };
  const items = [
    { name: "风险得分", value: avg("risk_score"), unit: "" },
    { name: "平均气温", value: avg("avg_temperature"), unit: "℃" },
    { name: "平均湿度", value: avg("avg_humidity"), unit: "%" },
    { name: "累计降水", value: avg("precipitation_total"), unit: "mm" },
    { name: "平均风速", value: avg("wind_speed"), unit: "m/s" },
    { name: "暴发数", value: avg("influenza_outbreak_count"), unit: "" },
  ].filter((item) => Number.isFinite(item.value));
  els.monthlyDiseaseSubtitle.textContent = `${state.city} 城市周度风险指标均值`;
  const width = 430;
  const height = 238;
  const margin = { top: 12, right: 22, bottom: 18, left: 94 };
  const max = Math.max(...items.map((item) => item.value), 1);
  const x = scaleLinear(0, max, margin.left, width - margin.right);
  const rowH = 30;
  const bars = items
    .map((item, index) => {
      const y = margin.top + index * rowH;
      const barW = x(item.value) - margin.left;
      return `<text class="chart-label" x="8" y="${y + 18}">${item.name}</text>
      <rect class="bar" x="${margin.left}" y="${y + 5}" width="${barW}" height="16" rx="5" fill="${colors[index % colors.length]}" data-name="${item.name}" data-value="${formatNumber(item.value, 2)}${item.unit}"></rect>
      <text class="chart-label" x="${Math.min(width - 76, margin.left + barW + 8)}" y="${y + 18}">${formatNumber(item.value, 2)}${item.unit}</text>`;
    })
    .join("");
  els.monthlyDiseaseChart.innerHTML = buildSvg(width, height, bars);
  els.monthlyDiseaseChart.querySelectorAll(".bar").forEach((bar) => {
    bar.addEventListener("mousemove", (event) => showTooltip(event, `<b>${state.city}</b><br>${bar.dataset.name}：${bar.dataset.value}`));
    bar.addEventListener("mouseleave", hideTooltip);
  });
}

function renderAnomalyTimeline() {
  const groups = new Map();
  filteredAnomalies().forEach((row) => {
    if (!groups.has(row.period)) groups.set(row.period, 0);
    groups.set(row.period, groups.get(row.period) + 1);
  });
  const rows = [...groups.entries()].map(([week, value]) => ({ week, value })).sort((a, b) => weekCompare(a.week, b.week));
  if (!rows.length) {
    els.anomalyTimelineChart.innerHTML = `<div class="empty">当前范围暂无异常点</div>`;
    return;
  }
  const width = 430;
  const height = 238;
  const margin = { top: 18, right: 18, bottom: 36, left: 44 };
  const max = Math.max(...rows.map((row) => row.value), 1);
  const xStep = (width - margin.left - margin.right) / Math.max(rows.length, 1);
  const y = scaleLinear(0, max * 1.15, height - margin.bottom, margin.top);
  const bars = rows
    .map((row, index) => {
      const x = margin.left + index * xStep + 1;
      const barW = Math.max(3, xStep - 2);
      const barH = height - margin.bottom - y(row.value);
      return `<rect class="bar" x="${x}" y="${y(row.value)}" width="${barW}" height="${barH}" rx="3" fill="#c84b42" data-week="${row.week}" data-value="${row.value}"></rect>`;
    })
    .join("");
  els.anomalyTimelineChart.innerHTML = buildSvg(
    width,
    height,
    `<line class="axis-line" x1="${margin.left}" x2="${width - margin.right}" y1="${height - margin.bottom}" y2="${height - margin.bottom}"></line>
    <line class="grid-line" x1="${margin.left}" x2="${width - margin.right}" y1="${y(max)}" y2="${y(max)}"></line>
    <text class="chart-label" x="8" y="${y(max) + 4}">${max}</text>
    ${bars}
    <text class="chart-label" x="${margin.left}" y="${height - 12}">${rows[0].week}</text>
    <text class="chart-label" x="${width - margin.right - 64}" y="${height - 12}">${rows.at(-1).week}</text>`,
  );
  els.anomalyTimelineChart.querySelectorAll(".bar").forEach((bar) => {
    bar.addEventListener("mousemove", (event) => showTooltip(event, `<b>${bar.dataset.week}</b><br>异常点：${bar.dataset.value}`));
    bar.addEventListener("mouseleave", hideTooltip);
  });
}

function renderKeywordCloud() {
  const events = data.keywordEvents.filter((row) => {
    const yearOk = state.year === "全部年份" || String(row.year) === String(state.year);
    const pathogenOk =
      state.pathogen === "全部病原体" ||
      !state.pathogen ||
      !row.pathogen ||
      row.pathogen === state.pathogen ||
      row.keyword === state.pathogen;
    const sceneOk = state.scene === "全部场景" || !row.scene || row.scene === state.scene;
    return yearOk && pathogenOk && sceneOk;
  });
  const counts = new Map();
  events.forEach((row) => {
    counts.set(row.keyword, (counts.get(row.keyword) || 0) + 1);
  });
  let rows = [...counts.entries()].map(([keyword, occurrences]) => ({ keyword, occurrences }));
  if (!rows.length) {
    rows = data.keywords.map((row) => ({ keyword: row.keyword, occurrences: row.occurrences }));
  }
  const max = Math.max(...rows.map((row) => row.occurrences), 1);
  els.keywordSubtitle.textContent = `${state.year} · ${state.pathogen} · ${state.scene} · ${events.length || "全局"} 条字段记录`;
  els.keywordCloud.innerHTML = rows
    .sort((a, b) => b.occurrences - a.occurrences)
    .slice(0, 18)
    .map((row, index) => {
      const size = 13 + (row.occurrences / max) * 10;
      const color = ["疫情", "暴发疫情", "阳性率"].includes(row.keyword) ? "#c84b42" : colors[index % colors.length];
      return `<div class="keyword-chip" style="font-size:${size.toFixed(1)}px;border-color:${color}33" data-keyword="${row.keyword}" data-count="${row.occurrences}" data-label="当前筛选统计">
        ${row.keyword}<span>${row.occurrences}</span>
      </div>`;
    })
    .join("");
  els.keywordCloud.querySelectorAll(".keyword-chip").forEach((chip) => {
    chip.addEventListener("mousemove", (event) => showTooltip(event, `<b>${chip.dataset.keyword}</b><br>出现次数：${chip.dataset.count}<br>${chip.dataset.label}`));
    chip.addEventListener("mouseleave", hideTooltip);
  });
}

function renderCorrelations() {
  const rows = data.correlations.slice().sort((a, b) => b.abs_correlation - a.abs_correlation).slice(0, 10);
  els.correlationList.innerHTML = rows
    .map(
      (row) => `<div class="correlation-item">
        <b>${row.x_variable} × ${row.y_variable}</b>
        <span>${row.direction} · ${row.strength} · r=${formatNumber(row.pearson_correlation, 3)} · n=${row.sample_size}</span>
        <div class="corr-bar"><div style="width:${Math.max(6, row.abs_correlation * 100)}%"></div></div>
      </div>`,
    )
    .join("");
}

function renderAnomalies() {
  const rows = filteredAnomalies().sort((a, b) => Math.abs(b.z_score) - Math.abs(a.z_score)).slice(0, 80);
  els.anomalyCount.textContent = `展示 ${rows.length} 条`;
  els.anomalyTable.innerHTML = rows
    .map((row) => {
      const high = String(row.anomaly_type).includes("高");
      return `<tr>
        <td>${row.series_name}</td>
        <td>${row.period}</td>
        <td>${formatNumber(row.value, 2)}</td>
        <td>${formatNumber(row.mean, 2)}</td>
        <td>${formatNumber(row.z_score, 2)}</td>
        <td class="${high ? "type-high" : "type-low"}">${row.anomaly_type}</td>
      </tr>`;
    })
    .join("");
}

function render() {
  renderKpis();
  renderTrend();
  renderDonut();
  renderSceneBars();
  renderScatter();
  renderProvinceMap();
  renderRiskDistribution();
  renderMonthlyDisease();
  renderAnomalyTimeline();
  renderKeywordCloud();
  renderCorrelations();
  renderAnomalies();
}

setupFilters();
render();
