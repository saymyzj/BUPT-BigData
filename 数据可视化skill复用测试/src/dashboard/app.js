const state = {
  data: null,
  ticker: "ALL",
  industry: "ALL",
  metric: "avg_adj_close",
  startMonth: "",
  endMonth: "",
};

const initialParams = new URLSearchParams(window.location.search);

const metricLabels = {
  avg_adj_close: "月均调整收盘价",
  avg_return_pct: "月均收益率(%)",
  total_volume_b: "月成交量(十亿股)",
};

const colors = {
  high_attention: "#b84a4a",
  medium_attention: "#a47425",
  regular_monitoring: "#24745a",
  unclustered: "#69716d",
};

const tooltip = document.querySelector("#tooltip");

function $(selector) {
  return document.querySelector(selector);
}

function fmt(value, digits = 2) {
  return Number(value || 0).toLocaleString("zh-CN", {
    maximumFractionDigits: digits,
  });
}

function clearSvg(svg) {
  while (svg.firstChild) svg.removeChild(svg.firstChild);
}

function node(name, attrs = {}, text = "") {
  const el = document.createElementNS("http://www.w3.org/2000/svg", name);
  Object.entries(attrs).forEach(([key, value]) => el.setAttribute(key, value));
  if (text) el.textContent = text;
  return el;
}

function showTip(event, html) {
  tooltip.innerHTML = html;
  tooltip.style.display = "block";
  tooltip.style.left = `${event.clientX + 12}px`;
  tooltip.style.top = `${event.clientY + 12}px`;
}

function hideTip() {
  tooltip.style.display = "none";
}

function dims(svg) {
  const rect = svg.getBoundingClientRect();
  return { width: rect.width || 640, height: rect.height || 300 };
}

function scaleLinear(domainMin, domainMax, rangeMin, rangeMax) {
  const span = domainMax - domainMin || 1;
  return (value) => rangeMin + ((value - domainMin) / span) * (rangeMax - rangeMin);
}

function currentCompanies() {
  return state.data.companies.filter((row) => {
    const industryOk = state.industry === "ALL" || row.industry_group === state.industry;
    const tickerOk = state.ticker === "ALL" || row.ticker === state.ticker;
    return industryOk && tickerOk;
  });
}

function currentTrend() {
  const months = state.data.meta.months;
  const start = months.indexOf(state.startMonth);
  const end = months.indexOf(state.endMonth);
  const inRange = (row) => {
    const idx = months.indexOf(row.period);
    return idx >= start && idx <= end;
  };
  if (state.ticker !== "ALL") {
    const rows = state.data.company_trend[state.ticker] || [];
    return rows.filter(inRange);
  }
  return state.data.monthly_trend.filter(inRange);
}

function renderKpis() {
  const companies = currentCompanies();
  $("#kpiCompanies").textContent = companies.length;
  $("#kpiRows").textContent = fmt(state.data.meta.stock_rows, 0);
  $("#kpiRisk").textContent = companies.filter((c) => c.risk_level === "high_attention").length;
  $("#kpiAnomalies").textContent = state.data.anomalies.filter((a) => state.ticker === "ALL" || a.ticker === state.ticker).length;
}

function renderTrend() {
  const svg = $("#trendChart");
  clearSvg(svg);
  const { width, height } = dims(svg);
  const margin = { top: 18, right: 28, bottom: 34, left: 52 };
  const rows = currentTrend();
  const values = rows.map((r) => Number(r[state.metric] || 0));
  const min = Math.min(...values, 0);
  const max = Math.max(...values, 1);
  const x = scaleLinear(0, Math.max(rows.length - 1, 1), margin.left, width - margin.right);
  const y = scaleLinear(min, max, height - margin.bottom, margin.top);

  $("#trendSubtitle").textContent = `${state.ticker === "ALL" ? "全部公司" : state.ticker} · ${state.startMonth} 至 ${state.endMonth} · ${metricLabels[state.metric]}`;
  for (let i = 0; i < 4; i += 1) {
    const yy = margin.top + ((height - margin.top - margin.bottom) / 3) * i;
    svg.appendChild(node("line", { class: "gridline", x1: margin.left, x2: width - margin.right, y1: yy, y2: yy }));
  }
  svg.appendChild(node("line", { class: "axis", x1: margin.left, x2: width - margin.right, y1: height - margin.bottom, y2: height - margin.bottom }));
  svg.appendChild(node("line", { class: "axis", x1: margin.left, x2: margin.left, y1: margin.top, y2: height - margin.bottom }));

  const points = rows.map((row, index) => `${x(index)},${y(Number(row[state.metric] || 0))}`).join(" ");
  svg.appendChild(node("polyline", { points, fill: "none", stroke: "#356cae", "stroke-width": 3, "stroke-linejoin": "round" }));
  rows.forEach((row, index) => {
    const cx = x(index);
    const cy = y(Number(row[state.metric] || 0));
    const dot = node("circle", { cx, cy, r: 4, fill: "#356cae" });
    dot.addEventListener("mousemove", (event) => showTip(event, `${row.period}<br>${metricLabels[state.metric]}: ${fmt(row[state.metric], 3)}`));
    dot.addEventListener("mouseleave", hideTip);
    svg.appendChild(dot);
    if (index === 0 || index === rows.length - 1 || index % 3 === 0) {
      svg.appendChild(node("text", { class: "label", x: cx, y: height - 12, "text-anchor": "middle" }, row.period));
    }
  });
  svg.appendChild(node("text", { class: "label", x: 10, y: margin.top + 5 }, metricLabels[state.metric]));
}

function renderIndustry() {
  const svg = $("#industryChart");
  clearSvg(svg);
  const { width, height } = dims(svg);
  const margin = { top: 16, right: 18, bottom: 76, left: 44 };
  const rows = state.data.industry_summary.filter((r) => state.industry === "ALL" || r.industry === state.industry);
  const max = Math.max(...rows.map((r) => r.avg_rd_busd), 1);
  const barW = (width - margin.left - margin.right) / rows.length - 10;
  const y = scaleLinear(0, max, height - margin.bottom, margin.top);
  rows.forEach((row, index) => {
    const x = margin.left + index * (barW + 10);
    const barH = height - margin.bottom - y(row.avg_rd_busd);
    const rect = node("rect", { x, y: y(row.avg_rd_busd), width: Math.max(barW, 10), height: barH, rx: 5, fill: "#24745a" });
    rect.addEventListener("mousemove", (event) => showTip(event, `${row.industry}<br>公司数: ${row.companies}<br>平均研发投入: ${fmt(row.avg_rd_busd, 3)} 十亿美元<br>平均波动率: ${fmt(row.avg_volatility, 4)}`));
    rect.addEventListener("mouseleave", hideTip);
    svg.appendChild(rect);
    svg.appendChild(node("text", { class: "label", x: x + barW / 2, y: height - 45, "text-anchor": "middle", transform: `rotate(-25 ${x + barW / 2} ${height - 45})` }, row.industry));
    svg.appendChild(node("text", { class: "label", x: x + barW / 2, y: y(row.avg_rd_busd) - 5, "text-anchor": "middle" }, fmt(row.avg_rd_busd, 1)));
  });
  svg.appendChild(node("text", { class: "label", x: 6, y: margin.top + 5 }, "十亿美元"));
}

function renderDonut() {
  const svg = $("#donutChart");
  clearSvg(svg);
  const { width, height } = dims(svg);
  const companies = currentCompanies();
  const counts = companies.reduce((acc, row) => {
    acc[row.risk_level] = (acc[row.risk_level] || 0) + 1;
    return acc;
  }, {});
  const entries = Object.entries(counts);
  const total = Math.max(companies.length, 1);
  const cx = width / 2;
  const cy = height / 2 - 10;
  const radius = Math.min(width, height) * 0.28;
  let angle = -Math.PI / 2;
  entries.forEach(([level, count]) => {
    const next = angle + (count / total) * Math.PI * 2;
    const large = next - angle > Math.PI ? 1 : 0;
    const x1 = cx + radius * Math.cos(angle);
    const y1 = cy + radius * Math.sin(angle);
    const x2 = cx + radius * Math.cos(next);
    const y2 = cy + radius * Math.sin(next);
    const path = node("path", {
      d: `M ${cx} ${cy} L ${x1} ${y1} A ${radius} ${radius} 0 ${large} 1 ${x2} ${y2} Z`,
      fill: colors[level] || colors.unclustered,
    });
    path.addEventListener("mousemove", (event) => showTip(event, `${level}<br>${count} 家，占比 ${fmt((count / total) * 100, 1)}%`));
    path.addEventListener("mouseleave", hideTip);
    svg.appendChild(path);
    angle = next;
  });
  svg.appendChild(node("circle", { cx, cy, r: radius * 0.55, fill: "#fff" }));
  svg.appendChild(node("text", { x: cx, y: cy + 5, "text-anchor": "middle", fill: "#18211f", "font-size": 22, "font-weight": 700 }, total));
  entries.forEach(([level, count], index) => {
    const y = height - 44 + index * 18;
    svg.appendChild(node("rect", { x: 20, y: y - 10, width: 10, height: 10, fill: colors[level] || colors.unclustered }));
    svg.appendChild(node("text", { class: "label", x: 36, y }, `${level}: ${count}`));
  });
}

function renderScatter() {
  const svg = $("#scatterChart");
  clearSvg(svg);
  const { width, height } = dims(svg);
  const margin = { top: 18, right: 22, bottom: 38, left: 54 };
  const rows = currentCompanies();
  const xMax = Math.max(...rows.map((r) => r.latest_rd_expense_busd), 1);
  const yMax = Math.max(...rows.map((r) => r.daily_return_volatility), 0.01);
  const vMax = Math.max(...rows.map((r) => r.total_volume_b), 1);
  const x = scaleLinear(0, xMax, margin.left, width - margin.right);
  const y = scaleLinear(0, yMax, height - margin.bottom, margin.top);
  svg.appendChild(node("line", { class: "axis", x1: margin.left, x2: width - margin.right, y1: height - margin.bottom, y2: height - margin.bottom }));
  svg.appendChild(node("line", { class: "axis", x1: margin.left, x2: margin.left, y1: margin.top, y2: height - margin.bottom }));
  rows.forEach((row) => {
    const radius = 4 + (row.total_volume_b / vMax) * 12;
    const dot = node("circle", {
      cx: x(row.latest_rd_expense_busd),
      cy: y(row.daily_return_volatility),
      r: radius,
      fill: colors[row.risk_level] || colors.unclustered,
      opacity: 0.78,
    });
    dot.addEventListener("mousemove", (event) => showTip(event, `${row.ticker} ${row.company_name}<br>行业: ${row.industry_group}<br>研发投入: ${fmt(row.latest_rd_expense_busd, 3)} 十亿美元<br>波动率: ${fmt(row.daily_return_volatility, 4)}<br>风险: ${row.risk_level}`));
    dot.addEventListener("mouseleave", hideTip);
    svg.appendChild(dot);
  });
  svg.appendChild(node("text", { class: "label", x: width / 2, y: height - 8, "text-anchor": "middle" }, "最新年度研发投入(十亿美元)"));
  svg.appendChild(node("text", { class: "label", x: 8, y: 18 }, "波动率"));
}

function renderHeatmap() {
  const svg = $("#heatmapChart");
  clearSvg(svg);
  const { width, height } = dims(svg);
  const vars = [...new Set(state.data.correlations.flatMap((r) => [r.x, r.y]))].slice(0, 6);
  const cell = Math.min((width - 120) / vars.length, (height - 60) / vars.length);
  const startX = 100;
  const startY = 20;
  vars.forEach((xVar, xi) => {
    vars.forEach((yVar, yi) => {
      const found = state.data.correlations.find((r) => (r.x === xVar && r.y === yVar) || (r.x === yVar && r.y === xVar));
      const value = xVar === yVar ? 1 : found ? found.value : 0;
      const color = value >= 0 ? `rgba(36,116,90,${Math.abs(value)})` : `rgba(184,74,74,${Math.abs(value)})`;
      const rect = node("rect", { x: startX + xi * cell, y: startY + yi * cell, width: cell - 2, height: cell - 2, fill: color || "#edf0ed" });
      rect.addEventListener("mousemove", (event) => showTip(event, `${xVar}<br>${yVar}<br>相关系数: ${fmt(value, 3)}`));
      rect.addEventListener("mouseleave", hideTip);
      svg.appendChild(rect);
      svg.appendChild(node("text", { class: "label", x: startX + xi * cell + cell / 2, y: startY + yi * cell + cell / 2 + 4, "text-anchor": "middle" }, fmt(value, 2)));
    });
    svg.appendChild(node("text", { class: "label", x: startX + xi * cell + cell / 2, y: startY + vars.length * cell + 14, "text-anchor": "middle", transform: `rotate(-25 ${startX + xi * cell + cell / 2} ${startY + vars.length * cell + 14})` }, xVar));
    svg.appendChild(node("text", { class: "label", x: 4, y: startY + xi * cell + cell / 2 + 4 }, xVar));
  });
}

function renderTable() {
  const rows = state.data.anomalies.filter((row) => state.ticker === "ALL" || row.ticker === state.ticker).slice(0, 16);
  $("#anomalyTable").innerHTML = rows.map((row) => `<tr><td>${row.ticker}</td><td>${row.period}</td><td>${fmt(row.value, 3)}%</td><td>${fmt(row.z_score, 3)}</td><td>${row.anomaly_type}</td></tr>`).join("");
}

function renderAll() {
  renderKpis();
  renderTrend();
  renderIndustry();
  renderDonut();
  renderScatter();
  renderHeatmap();
  renderTable();
}

function populateControls() {
  const tickerSelect = $("#tickerSelect");
  const industrySelect = $("#industrySelect");
  const startMonth = $("#startMonth");
  const endMonth = $("#endMonth");
  tickerSelect.innerHTML = '<option value="ALL">全部股票</option>' + state.data.companies.map((row) => `<option value="${row.ticker}">${row.ticker} · ${row.company_name}</option>`).join("");
  industrySelect.innerHTML = '<option value="ALL">全部行业</option>' + state.data.meta.industries.map((industry) => `<option value="${industry}">${industry}</option>`).join("");
  startMonth.innerHTML = state.data.meta.months.map((month) => `<option value="${month}">${month}</option>`).join("");
  endMonth.innerHTML = state.data.meta.months.map((month) => `<option value="${month}">${month}</option>`).join("");
  state.startMonth = state.data.meta.months[0];
  state.endMonth = state.data.meta.months[state.data.meta.months.length - 1];
  if (initialParams.get("ticker")) state.ticker = initialParams.get("ticker");
  if (initialParams.get("industry")) state.industry = initialParams.get("industry");
  if (initialParams.get("metric")) state.metric = initialParams.get("metric");
  if (initialParams.get("start")) state.startMonth = initialParams.get("start");
  if (initialParams.get("end")) state.endMonth = initialParams.get("end");
  if (initialParams.get("window")) {
    const win = initialParams.get("window");
    state.endMonth = state.data.meta.months[state.data.meta.months.length - 1];
    state.startMonth = win === "all" ? state.data.meta.months[0] : state.data.meta.months[Math.max(0, state.data.meta.months.length - Number(win))];
  }
  tickerSelect.value = state.ticker;
  industrySelect.value = state.industry;
  $("#metricSelect").value = state.metric;
  startMonth.value = state.startMonth;
  endMonth.value = state.endMonth;
  document.querySelectorAll("[data-window]").forEach((button) => {
    button.classList.toggle("active", button.dataset.window === (initialParams.get("window") || "all"));
  });
}

function bindEvents() {
  $("#tickerSelect").addEventListener("change", (event) => {
    state.ticker = event.target.value;
    renderAll();
  });
  $("#industrySelect").addEventListener("change", (event) => {
    state.industry = event.target.value;
    renderAll();
  });
  $("#metricSelect").addEventListener("change", (event) => {
    state.metric = event.target.value;
    renderAll();
  });
  $("#startMonth").addEventListener("change", (event) => {
    state.startMonth = event.target.value;
    renderAll();
  });
  $("#endMonth").addEventListener("change", (event) => {
    state.endMonth = event.target.value;
    renderAll();
  });
  document.querySelectorAll("[data-window]").forEach((button) => {
    button.addEventListener("click", () => {
      document.querySelectorAll("[data-window]").forEach((b) => b.classList.remove("active"));
      button.classList.add("active");
      const months = state.data.meta.months;
      const win = button.dataset.window;
      state.endMonth = months[months.length - 1];
      state.startMonth = win === "all" ? months[0] : months[Math.max(0, months.length - Number(win))];
      $("#startMonth").value = state.startMonth;
      $("#endMonth").value = state.endMonth;
      renderAll();
    });
  });
  $("#resetBtn").addEventListener("click", () => {
    state.ticker = "ALL";
    state.industry = "ALL";
    state.metric = "avg_adj_close";
    state.startMonth = state.data.meta.months[0];
    state.endMonth = state.data.meta.months[state.data.meta.months.length - 1];
    $("#tickerSelect").value = state.ticker;
    $("#industrySelect").value = state.industry;
    $("#metricSelect").value = state.metric;
    $("#startMonth").value = state.startMonth;
    $("#endMonth").value = state.endMonth;
    document.querySelectorAll("[data-window]").forEach((b) => b.classList.toggle("active", b.dataset.window === "all"));
    renderAll();
  });
  window.addEventListener("resize", renderAll);
}

fetch("../../data/dashboard-data.json")
  .then((res) => res.json())
  .then((data) => {
    state.data = data;
    populateControls();
    bindEvents();
    renderAll();
    if (initialParams.get("demoTip") === "1") {
      const first = currentCompanies()[0];
      tooltip.innerHTML = `${first.ticker} ${first.company_name}<br>研发投入: ${fmt(first.latest_rd_expense_busd, 3)} 十亿美元<br>风险: ${first.risk_level}`;
      tooltip.style.display = "block";
      tooltip.style.left = "68%";
      tooltip.style.top = "54%";
    }
  })
  .catch((error) => {
    document.body.insertAdjacentHTML("beforeend", `<p class="load-error">数据加载失败: ${error.message}</p>`);
  });
