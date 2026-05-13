/* =====================================================================
   Plotly figures + Leaflet map for the GFD report.
   All chart data is loaded from website/figures/*.json
   ===================================================================== */

const PALETTE = {
  paper:   "#FDFBF7",
  cream:   "#F5F0E6",
  ink:     "#2E261F",
  muted:   "#6B6157",
  accent:  "#B8854F",
  bolt:    "#C9A24A",
  sage:    "#8FA38E",
  sageDeep:"#4F6450",
  rust:    "#A85638",
  ocean:   "#4A7A8C",
  line:    "rgba(46,38,31,0.10)",
};

const FONT = {
  family: '"Plus Jakarta Sans", system-ui, sans-serif',
  serif:  '"Fraunces", Georgia, serif',
};

const baseLayout = {
  paper_bgcolor: "rgba(0,0,0,0)",
  plot_bgcolor:  "rgba(0,0,0,0)",
  font: { family: FONT.family, size: 12, color: PALETTE.ink },
  margin: { l: 56, r: 24, t: 24, b: 48 },
  hoverlabel: {
    bgcolor: PALETTE.paper,
    bordercolor: PALETTE.accent,
    font: { family: FONT.family, size: 12, color: PALETTE.ink },
  },
  xaxis: {
    gridcolor: PALETTE.line,
    zerolinecolor: PALETTE.line,
    tickfont: { color: PALETTE.muted, size: 11 },
    title: { font: { color: PALETTE.muted, size: 11 } },
  },
  yaxis: {
    gridcolor: PALETTE.line,
    zerolinecolor: PALETTE.line,
    tickfont: { color: PALETTE.muted, size: 11 },
    title: { font: { color: PALETTE.muted, size: 11 } },
  },
  legend: {
    orientation: "h",
    y: -0.18, x: 0,
    bgcolor: "rgba(0,0,0,0)",
    font: { color: PALETTE.ink, size: 11 },
  },
};

const baseConfig = {
  displayModeBar: true,
  modeBarButtonsToRemove: [
    "lasso2d", "select2d", "autoScale2d", "hoverClosestCartesian",
    "hoverCompareCartesian", "toggleSpikelines",
  ],
  displaylogo: false,
  responsive: true,
  toImageButtonOptions: { format: "png", scale: 2 },
};

const fetchJSON = (name) =>
  fetch(`figures/${name}.json`).then(r => r.json());

/* ---------- Figure 1: Historical totals + ENSO/IOD ---------------- */
fetchJSON("hist_overview").then(d => {
  const traces = [
    {
      type: "bar",
      name: "Unique strikes",
      x: d.years,
      y: d.unique_strikes,
      marker: { color: PALETTE.accent, opacity: 0.85 },
      hovertemplate: "<b>%{x}</b><br>%{y:,} unique strikes<extra></extra>",
    },
    {
      type: "scatter", mode: "lines+markers",
      name: "Niño 3.4 (JJA)",
      x: d.years, y: d.nino34_jja,
      yaxis: "y2",
      line: { color: PALETTE.rust, width: 2.5 },
      marker: { size: 8, color: PALETTE.rust },
      hovertemplate: "<b>%{x}</b><br>Niño 3.4 = %{y:.2f} °C<extra></extra>",
    },
    {
      type: "scatter", mode: "lines+markers",
      name: "IOD DMI (JJA)",
      x: d.years, y: d.dmi_jja,
      yaxis: "y2",
      line: { color: PALETTE.ocean, width: 2.5, dash: "dot" },
      marker: { size: 7, color: PALETTE.ocean },
      hovertemplate: "<b>%{x}</b><br>IOD DMI = %{y:.2f} °C<extra></extra>",
    },
  ];
  const layout = {
    ...baseLayout,
    height: 420,
    yaxis: { ...baseLayout.yaxis, title: "Unique strikes (per year)" },
    yaxis2: {
      title: "Climate anomaly (°C)",
      overlaying: "y", side: "right",
      gridcolor: "rgba(0,0,0,0)",
      tickfont: { color: PALETTE.muted, size: 11 },
      titlefont: { color: PALETTE.muted, size: 11 },
      zerolinecolor: "rgba(46,38,31,0.18)",
      zerolinewidth: 1,
    },
    xaxis: { ...baseLayout.xaxis, dtick: 1 },
    legend: { ...baseLayout.legend, y: -0.22 },
  };
  Plotly.newPlot("fig-history", traces, layout, baseConfig);
});

/* ---------- Figure 2: Monthly seasonality ------------------------- */
fetchJSON("seasonality").then(d => {
  const monthLabel = (m) => ["Jan","Feb","Mar","Apr","May","Jun",
                              "Jul","Aug","Sep","Oct","Nov","Dec"][m-1];
  const labels = d.month.map(monthLabel);
  const trace = {
    type: "bar",
    x: labels, y: d.mean,
    marker: {
      color: d.mean,
      colorscale: [
        [0, "rgba(143,163,142,0.55)"],
        [0.5, "rgba(184,133,79,0.7)"],
        [1, "rgba(168,86,56,0.9)"],
      ],
      line: { width: 0 },
    },
    error_y: {
      type: "data", array: d.sd,
      color: "rgba(46,38,31,0.35)", thickness: 1.2, width: 4,
    },
    hovertemplate: "<b>%{x}</b><br>Avg strikes/month: %{y:.0f}<br>± %{error_y.array:.0f}<extra></extra>",
  };
  const layout = {
    ...baseLayout, height: 320,
    showlegend: false,
    yaxis: { ...baseLayout.yaxis, title: "Avg strikes per month" },
    xaxis: { ...baseLayout.xaxis, title: "" },
  };
  Plotly.newPlot("fig-seasonality", [trace], layout, baseConfig);
});

/* ---------- Figure 3: Per-tower GFD profile — all years ----------- */
// Model D extension (v1.2): two profile datasets ("C" and optional "D")
// driven by a model-pill above the scenario tabs.
let profileData      = null;     // Model C profile (legacy)
let profileDataD     = null;     // Model D profile (may be null)
let activeScenario   = "Neutral";
let activeModel      = "C";       // "C" or "D"

const MODEL_C_COLOR = "#B8854F";
const MODEL_D_COLOR = "#4A7A8C";

// Historical year colors: warm spectrum sage → amber → rust, solid lines
const HIST_COLORS = {
  "2019": "rgba(133,166,143,0.72)",
  "2020": "rgba(107,158,147,0.72)",
  "2021": "rgba(157,184,112,0.78)",
  "2022": "rgba(212,174, 68,0.92)",   // peak year — brighter
  "2023": "rgba(196,130, 74,0.78)",
  "2024": "rgba(168,106, 64,0.78)",
  "2025": "rgba(168, 86, 56,0.78)",
};
const HIST_WIDTH = {
  "2019":1.5,"2020":1.5,"2021":1.5,
  "2022":2.5,                         // peak year — thicker
  "2023":1.5,"2024":1.5,"2025":1.5,
};

// Forecast year colors: ocean-blue spectrum, dashed lines
const FC_COLORS = {
  "2026": "rgba( 92,155,192,0.88)",
  "2027": "rgba( 74,135,171,0.88)",
  "2028": "rgba( 58,112,144,0.88)",
  "2029": "rgba( 46, 91,120,0.88)",
  "2030": "rgba( 34, 72, 96,0.88)",
};

const HIST_YEARS = ["2019","2020","2021","2022","2023","2024","2025"];
const FC_YEARS   = ["2026","2027","2028","2029","2030"];

function buildProfileTraces(scenario, model) {
  // Historical data is identical for both models — comes from observations
  const src = (model === "D" && profileDataD) ? profileDataD : profileData;
  const ids = src.tower_ids;
  const traces = [];

  // 7 historical solid lines
  HIST_YEARS.forEach(yr => {
    traces.push({
      type: "scatter", mode: "lines",
      name: yr,
      x: ids,
      y: src.historical[yr],
      line: { color: HIST_COLORS[yr], width: HIST_WIDTH[yr], dash: "solid" },
      hovertemplate: `<b>Tower %{x}</b><br>${yr} historical: %{y:.1f} fl/km²/yr<extra></extra>`,
      legendgroup: "historical",
      legendgrouptitle: yr === "2019" ? { text: "Historical" } : {},
    });
  });

  // 5 forecast dashed lines for selected (scenario, model)
  const fc_for_scenario = src.forecast[scenario] || {};
  const modelLabel = (model === "D") ? "Model D" : "Model C";
  FC_YEARS.forEach(yr => {
    const ys = fc_for_scenario[yr];
    if (!ys) return;
    traces.push({
      type: "scatter", mode: "lines",
      name: `${yr} (${modelLabel})`,
      x: ids,
      y: ys,
      line: { color: FC_COLORS[yr], width: 2, dash: "dash" },
      hovertemplate: `<b>Tower %{x}</b><br>${yr} forecast (${modelLabel}): %{y:.1f} fl/km²/yr<extra></extra>`,
      legendgroup: "forecast",
      legendgrouptitle: yr === "2026" ? { text: `Forecast — ${modelLabel}` } : {},
    });
  });

  return traces;
}

const profileLayout = () => ({
  ...baseLayout,
  height: 500,
  yaxis: {
    ...baseLayout.yaxis,
    title: "GFD (flashes/km²/yr, panel scale)",
    rangemode: "tozero",
  },
  xaxis: {
    ...baseLayout.xaxis,
    title: "Tower number",
    tickmode: "array",
    tickvals: [1, 50, 100, 150, 200, 250, 281],
    ticktext: ["1","50","100","150","200","250","281"],
  },
  legend: {
    orientation: "h",
    y: -0.28, x: 0,
    bgcolor: "rgba(0,0,0,0)",
    font: { color: PALETTE.ink, size: 11 },
    traceorder: "grouped",
    groupclick: "toggleitem",
  },
  showlegend: true,
  margin: { l: 64, r: 24, t: 24, b: 96 },
});

function renderProfile(scenario, model, isInitial) {
  if (!profileData) return;
  if (model === "D" && !profileDataD) {
    // Model D unavailable — silently keep Model C
    model = "C";
  }

  // Preserve per-trace visibility across both scenario AND model switches
  let savedVisible = null;
  if (!isInitial) {
    const gd = document.getElementById("fig-forecast");
    if (gd && gd.data && gd.data.length === 12) {
      savedVisible = gd.data.map(t =>
        t.visible === undefined ? true : t.visible
      );
    }
  }

  const traces = buildProfileTraces(scenario, model);

  if (savedVisible) {
    traces.forEach((t, i) => {
      if (savedVisible[i] !== undefined) t.visible = savedVisible[i];
    });
  }

  Plotly.react("fig-forecast", traces, profileLayout(), baseConfig);
}

// Load Model C profile (always)
fetchJSON("tower_gfd_profile").then(d => {
  profileData = d;
  renderProfile(activeScenario, activeModel, true);
  // Scenario-tab wiring (kept here so it survives even if D fails to load)
  document.querySelectorAll(".scenario-tabs .tab").forEach(btn => {
    btn.addEventListener("click", () => {
      document.querySelectorAll(".scenario-tabs .tab").forEach(b => b.classList.remove("active"));
      btn.classList.add("active");
      activeScenario = btn.dataset.scenario;
      renderProfile(activeScenario, activeModel, false);
    });
  });
});

// Try to load Model D profile (optional)
fetch("figures/tower_gfd_profile_d.json")
  .then(r => r.ok ? r.json() : null)
  .then(d => {
    if (!d) return;
    profileDataD = d;
    // Enable the Model D button now that data is loaded
    document.querySelectorAll('.model-btn[data-model="D"]').forEach(b => {
      b.disabled = false;
    });
  })
  .catch(() => { /* silent — Model D rendering simply falls back to C */ });

// Model-pill wiring (model toggle for Figure 3)
document.querySelectorAll(".model-pill .model-btn").forEach(btn => {
  btn.addEventListener("click", () => {
    const m = btn.dataset.model;
    document.querySelectorAll(".model-pill .model-btn").forEach(b => {
      b.classList.remove("active");
      b.setAttribute("aria-checked", "false");
    });
    btn.classList.add("active");
    btn.setAttribute("aria-checked", "true");
    activeModel = m;
    renderProfile(activeScenario, activeModel, false);
  });
});

/* ---------- Figure 4: Top-20 ranking ------------------------------ */
fetchJSON("top20").then(d => {
  const trace = {
    type: "bar",
    orientation: "h",
    x: d.p50,
    y: d.tower_id.map(t => `Tower ${t}`),
    marker: { color: PALETTE.accent, opacity: 0.9, line: { width: 0 } },
    error_x: {
      type: "data",
      array:    d.hi80.map((h, i) => h - d.p50[i]),
      arrayminus: d.p50.map((p, i) => p - d.lo80[i]),
      color: "rgba(46,38,31,0.4)",
      thickness: 1.2, width: 6,
    },
    text: d.p50.map(v => v.toFixed(2)),
    textposition: "outside",
    textfont: { color: PALETTE.ink, size: 11 },
    hovertemplate: "<b>%{y}</b><br>GFD = %{x:.2f} flashes/km²/yr<br>80%% PI: [%{customdata[0]:.2f}, %{customdata[1]:.2f}]<extra></extra>",
    customdata: d.tower_id.map((_, i) => [d.lo80[i], d.hi80[i]]),
  };
  const layout = {
    ...baseLayout,
    height: 560,
    margin: { l: 96, r: 64, t: 24, b: 48 },
    xaxis: { ...baseLayout.xaxis, title: "5-yr mean GFD (Neutral, flashes/km²/yr)" },
    yaxis: {
      ...baseLayout.yaxis,
      autorange: "reversed",
      tickfont: { size: 11, color: PALETTE.ink },
    },
    showlegend: false,
  };
  Plotly.newPlot("fig-top20", [trace], layout, baseConfig);
});

/* ---------- Leaflet map ------------------------------------------- */
function waitForLeaflet(cb) {
  if (typeof L !== "undefined") return cb();
  setTimeout(() => waitForLeaflet(cb), 80);
}

waitForLeaflet(() => {
  fetchJSON("map_towers").then(d => {
    const map = L.map("map", {
      scrollWheelZoom: false,
      zoomControl: true,
      attributionControl: true,
    });

    // Subtle muted basemap
    L.tileLayer(
      "https://{s}.basemaps.cartocdn.com/light_nolabels/{z}/{x}/{y}{r}.png",
      {
        attribution: '© <a href="https://www.openstreetmap.org/copyright">OSM</a> · CARTO',
        subdomains: "abcd",
        maxZoom: 18,
      }
    ).addTo(map);

    // Line polyline
    L.polyline(d.line_path, {
      color: "#2E261F",
      weight: 2,
      opacity: 0.55,
      smoothFactor: 1.5,
    }).addTo(map);

    // Color scale based on GFD value
    const vals = d.towers.map(t => t.neutral);
    const vmin = Math.min(...vals);
    const vmax = Math.max(...vals);
    const lerp = (v) => Math.min(1, Math.max(0, (v - vmin) / (vmax - vmin)));
    const colorAt = (v) => {
      const t = lerp(v);
      // sage → bronze → rust
      const stops = [
        [0,   [143, 163, 142]],
        [0.5, [184, 133,  79]],
        [1,   [168,  86,  56]],
      ];
      for (let i = 0; i < stops.length - 1; i++) {
        const [a, ac] = stops[i], [b, bc] = stops[i + 1];
        if (t <= b) {
          const u = (t - a) / (b - a);
          const c = ac.map((ch, k) => Math.round(ch + (bc[k] - ch) * u));
          return `rgb(${c.join(",")})`;
        }
      }
      return "rgb(168,86,56)";
    };

    const layerGroups = {
      LaNina:  L.layerGroup(),
      Neutral: L.layerGroup(),
      ElNino:  L.layerGroup(),
    };

    d.towers.forEach(t => {
      ["LaNina", "Neutral", "ElNino"].forEach(sc => {
        const val = t[sc.toLowerCase().replace("la","la").replace("el","el")];
        const v = sc === "LaNina" ? t.lanina : sc === "Neutral" ? t.neutral : t.elnino;
        const radius = 4 + 8 * lerp(v);
        const popup = `
          <div style="font-family: 'Plus Jakarta Sans', sans-serif; font-size: 13px; color: #2E261F; min-width: 200px;">
            <div style="font-family: 'Fraunces', serif; font-size: 17px; font-weight: 500; margin-bottom: 6px;">Tower ${t.id}</div>
            <div style="font-size: 11px; color: #6B6157; letter-spacing: 0.1em; text-transform: uppercase; margin-bottom: 10px;">${sc} · 5-yr mean</div>
            <div style="display: flex; justify-content: space-between; gap: 16px; margin-bottom: 4px;">
              <span style="color: #6B6157;">GFD (median):</span>
              <strong style="color: #B8854F; font-size: 15px;">${v.toFixed(2)}</strong>
            </div>
            <div style="display: flex; justify-content: space-between; gap: 16px; margin-bottom: 4px; font-size: 12px; color: #6B6157;">
              <span>80% interval:</span>
              <span>[${t.lo80.toFixed(2)}, ${t.hi80.toFixed(2)}]</span>
            </div>
            <div style="display: flex; justify-content: space-between; gap: 16px; font-size: 12px; color: #6B6157;">
              <span>Elevation:</span>
              <span>${t.elev} m</span>
            </div>
            <div style="margin-top: 10px; padding-top: 10px; border-top: 1px solid rgba(46,38,31,0.1); font-size: 11px; color: #6B6157;">
              Units: flashes/km²/yr · panel scale
            </div>
          </div>
        `;
        L.circleMarker([t.lat, t.lng], {
          radius,
          color: colorAt(v),
          weight: 1.2,
          opacity: 0.85,
          fillColor: colorAt(v),
          fillOpacity: 0.72,
        }).bindPopup(popup).addTo(layerGroups[sc]);
      });
    });

    layerGroups.Neutral.addTo(map);

    L.control.layers(null, {
      "Neutral scenario":  layerGroups.Neutral,
      "La Niña scenario":  layerGroups.LaNina,
      "El Niño scenario":  layerGroups.ElNino,
    }, { collapsed: false }).addTo(map);

    // Fit to data
    const bounds = L.latLngBounds(d.line_path);
    map.fitBounds(bounds.pad(0.04));

    // Legend
    const legend = L.control({ position: "bottomright" });
    legend.onAdd = () => {
      const div = L.DomUtil.create("div", "map-legend");
      div.innerHTML = `
        <div style="background: rgba(253,251,247,0.95); padding: 10px 14px; border-radius: 12px;
                    border: 1px solid rgba(46,38,31,0.08); box-shadow: 0 4px 16px rgba(46,38,31,0.06);
                    font-family: 'Plus Jakarta Sans', sans-serif; font-size: 11px; color: #2E261F; min-width: 160px;">
          <div style="font-weight: 600; letter-spacing: 0.12em; text-transform: uppercase; font-size: 10px; color: #6B6157; margin-bottom: 8px;">5-yr mean GFD</div>
          <div style="height: 8px; border-radius: 4px; background: linear-gradient(90deg, rgb(143,163,142), rgb(184,133,79), rgb(168,86,56)); margin-bottom: 6px;"></div>
          <div style="display: flex; justify-content: space-between; font-size: 10px; color: #6B6157;">
            <span>${vmin.toFixed(1)}</span>
            <span>${((vmin+vmax)/2).toFixed(1)}</span>
            <span>${vmax.toFixed(1)}</span>
          </div>
          <div style="font-size: 10px; color: #6B6157; margin-top: 6px;">flashes/km²/yr (panel scale)</div>
        </div>
      `;
      return div;
    };
    legend.addTo(map);
  });
});

/* ===================================================================== */
/* Model D extension (v1.2) — Section 06 comparison charts               */
/* ===================================================================== */

// Helper: tolerate optional comparison JSONs (Model D may be absent)
function tryFetchJSON(name) {
  return fetch(`figures/${name}.json`)
    .then(r => r.ok ? r.json() : null)
    .catch(() => null);
}

// ---------- Skill tiles (A / C / D, LOYO mean) ----------
tryFetchJSON("comparison_skill").then(d => {
  if (!d) return;
  const grid = document.getElementById("skill-grid");
  if (!grid) return;

  // Pivot: rows = target × metric, columns = model
  const targets = ["count", "density"];
  const metrics = [
    { key: "RMSE", label: "RMSE (count)", lowerBetter: true,  target: "count" },
    { key: "RMSE", label: "RMSE (density)", lowerBetter: true, target: "density" },
    { key: "MAE",  label: "MAE (count)",  lowerBetter: true,  target: "count" },
    { key: "CRPS", label: "CRPS (density)", lowerBetter: true, target: "density" },
  ];

  const html = metrics.map(m => {
    const cell = mdl =>
      d.rows.find(r => r.scheme === "loyo" && r.target === m.target && r.model === mdl);
    const ra = cell("A"), rc = cell("C"), rd = cell("D");
    const va = ra && ra[m.key] != null ? ra[m.key].toFixed(2) : "—";
    const vc = rc && rc[m.key] != null ? rc[m.key].toFixed(2) : "—";
    const vd = rd && rd[m.key] != null ? rd[m.key].toFixed(2) : "—";
    return `
      <div class="skill-tile">
        <span class="lbl">${m.label}</span>
        <div class="vals">
          <span class="v-a" title="Model A — climatology">${va}</span>
          <span class="v-c" title="Model C — benchmark">${vc}</span>
          <span class="v-d" title="Model D — forecast-informed">${vd}</span>
        </div>
        <span class="sub">A · C · D &nbsp;·&nbsp; lower is better</span>
      </div>
    `;
  }).join("");
  grid.innerHTML = html;
});

// ---------- Model D meta (fallback banner + provider info) ----------
tryFetchJSON("model_d_meta").then(d => {
  if (!d) return;
  const banner = document.getElementById("fallback-banner");
  if (!banner) return;

  if (d.is_reverted_to_c) {
    document.getElementById("fallback-banner-msg").innerHTML =
      "On the current 7-year sample, recency weighting added no out-of-sample skill — Model D collapsed to a climatology-equivalent fit. Outputs are flagged with <code>notes='reverted_to_C_no_recency_skill'</code> and the C and D forecasts will look essentially identical.";
    banner.classList.remove("hidden");
  } else if (d.all_fallback) {
    // Already correct default banner; just unhide
    banner.classList.remove("hidden");
  }
});

// ---------- Comparison line ribbon (C vs D, Neutral, 2026–2030) ----------
tryFetchJSON("comparison_line").then(d => {
  if (!d) return;
  const mount = document.getElementById("fig-compare-line");
  if (!mount) return;

  const cNeutral = (d.C && d.C.Neutral) ? d.C.Neutral : null;
  const dNeutral = (d.D && d.D.Neutral) ? d.D.Neutral : null;
  if (!cNeutral || !dNeutral) return;

  const traces = [];
  // Model C ribbon
  traces.push({
    type: "scatter", mode: "lines",
    x: [...cNeutral.year, ...cNeutral.year.slice().reverse()],
    y: [...cNeutral.hi80, ...cNeutral.lo80.slice().reverse()],
    fill: "toself",
    fillcolor: "rgba(184,133,79,0.18)",
    line: { color: "rgba(0,0,0,0)" },
    name: "Model C 80% PI",
    hoverinfo: "skip",
  });
  // Model D ribbon
  traces.push({
    type: "scatter", mode: "lines",
    x: [...dNeutral.year, ...dNeutral.year.slice().reverse()],
    y: [...dNeutral.hi80, ...dNeutral.lo80.slice().reverse()],
    fill: "toself",
    fillcolor: "rgba(74,122,140,0.20)",
    line: { color: "rgba(0,0,0,0)" },
    name: "Model D 80% PI",
    hoverinfo: "skip",
  });
  // Median lines
  traces.push({
    type: "scatter", mode: "lines+markers",
    x: cNeutral.year, y: cNeutral.p50,
    line: { color: MODEL_C_COLOR, width: 3 },
    marker: { size: 9, color: MODEL_C_COLOR, line: { color: PALETTE.paper, width: 2 } },
    name: "Model C median",
    hovertemplate: "<b>%{x}</b><br>Model C GFD: %{y:.2f}<extra></extra>",
  });
  traces.push({
    type: "scatter", mode: "lines+markers",
    x: dNeutral.year, y: dNeutral.p50,
    line: { color: MODEL_D_COLOR, width: 3, dash: "dot" },
    marker: { size: 9, color: MODEL_D_COLOR, line: { color: PALETTE.paper, width: 2 } },
    name: "Model D median",
    hovertemplate: "<b>%{x}</b><br>Model D GFD: %{y:.2f}<extra></extra>",
  });

  const layout = {
    ...baseLayout, height: 400,
    yaxis: { ...baseLayout.yaxis, title: "Mean GFD (flashes/km²/yr)" },
    xaxis: { ...baseLayout.xaxis, dtick: 1, title: "Year" },
    legend: { ...baseLayout.legend, y: -0.22 },
  };
  Plotly.newPlot("fig-compare-line", traces, layout, baseConfig);
});

// ---------- Top-20 paired bars + Jaccard pill ----------
tryFetchJSON("comparison_top20").then(d => {
  if (!d) return;
  const mount = document.getElementById("fig-compare-top20");
  const pill = document.getElementById("top20-jaccard-pill");
  if (!mount) return;

  // Jaccard
  if (pill) {
    pill.querySelector(".jp-num").textContent = (d.jaccard ?? 0).toFixed(2);
  }

  // Paired bars on the union of top-20s
  const union = d.union_ids;
  const labels = union.map(t => `Tower ${t}`);
  const cVals = union.map(t => d.C_values[String(t)] ?? null);
  const dVals = union.map(t => d.D_values[String(t)] ?? null);

  const traces = [
    {
      type: "bar", orientation: "h",
      x: cVals, y: labels,
      marker: { color: MODEL_C_COLOR, opacity: 0.85 },
      name: "Model C",
      hovertemplate: "<b>%{y}</b><br>Model C: %{x:.2f} fl/km²/yr<extra></extra>",
    },
    {
      type: "bar", orientation: "h",
      x: dVals, y: labels,
      marker: { color: MODEL_D_COLOR, opacity: 0.85 },
      name: "Model D",
      hovertemplate: "<b>%{y}</b><br>Model D: %{x:.2f} fl/km²/yr<extra></extra>",
    },
  ];
  const layout = {
    ...baseLayout,
    height: Math.max(360, 22 * union.length + 80),
    barmode: "group",
    margin: { l: 96, r: 32, t: 16, b: 56 },
    xaxis: { ...baseLayout.xaxis, title: "5-yr mean GFD (Neutral, flashes/km²/yr)" },
    yaxis: { ...baseLayout.yaxis, autorange: "reversed",
             tickfont: { size: 10, color: PALETTE.ink } },
    legend: { ...baseLayout.legend, y: -0.18 },
  };
  Plotly.newPlot("fig-compare-top20", traces, layout, baseConfig);
});

// ---------- Per-tower delta scatter (D - C vs elevation) ----------
tryFetchJSON("comparison_delta").then(d => {
  if (!d || !d.rows) return;
  const mount = document.getElementById("fig-compare-delta");
  if (!mount) return;

  const xs = d.rows.map(r => r.elev);
  const ys = d.rows.map(r => r.delta);
  const ids = d.rows.map(r => r.id);
  const colors = ys.map(v => v >= 0 ? MODEL_D_COLOR : "rgba(168,86,56,0.85)");

  const trace = {
    type: "scatter", mode: "markers",
    x: xs, y: ys,
    marker: {
      size: 7,
      color: colors,
      line: { color: "rgba(46,38,31,0.18)", width: 0.5 },
    },
    text: ids.map(i => `Tower ${i}`),
    hovertemplate: "%{text}<br>Elev: %{x} m<br>Δ (D − C): %{y:.2f}<extra></extra>",
  };
  // Zero line
  const zero = {
    type: "scatter", mode: "lines",
    x: [Math.min(...xs), Math.max(...xs)], y: [0, 0],
    line: { color: "rgba(46,38,31,0.2)", width: 1, dash: "dot" },
    hoverinfo: "skip", showlegend: false,
  };
  const layout = {
    ...baseLayout, height: 380,
    xaxis: { ...baseLayout.xaxis, title: "Tower elevation (m)" },
    yaxis: { ...baseLayout.yaxis, title: "ΔGFD: Model D − Model C (flashes/km²/yr)" },
    showlegend: false,
  };
  Plotly.newPlot("fig-compare-delta", [zero, trace], layout, baseConfig);
});
