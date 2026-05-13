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
let profileData   = null;
let activeScenario = "Neutral";

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

function buildProfileTraces(scenario) {
  const ids = profileData.tower_ids;
  const traces = [];

  // 7 historical solid lines
  HIST_YEARS.forEach(yr => {
    traces.push({
      type: "scatter", mode: "lines",
      name: yr,
      x: ids,
      y: profileData.historical[yr],
      line: { color: HIST_COLORS[yr], width: HIST_WIDTH[yr], dash: "solid" },
      hovertemplate: `<b>Tower %{x}</b><br>${yr} historical: %{y:.1f} fl/km²/yr<extra></extra>`,
      legendgroup: "historical",
      legendgrouptitle: yr === "2019" ? { text: "Historical" } : {},
    });
  });

  // 5 forecast dashed lines for selected scenario
  FC_YEARS.forEach(yr => {
    traces.push({
      type: "scatter", mode: "lines",
      name: yr + " (fcst)",
      x: ids,
      y: profileData.forecast[scenario][yr],
      line: { color: FC_COLORS[yr], width: 2, dash: "dash" },
      hovertemplate: `<b>Tower %{x}</b><br>${yr} forecast: %{y:.1f} fl/km²/yr<extra></extra>`,
      legendgroup: "forecast",
      legendgrouptitle: yr === "2026" ? { text: "Forecast" } : {},
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

function renderProfile(scenario, isInitial) {
  if (!profileData) return;

  // Preserve per-trace visibility when switching scenario (not initial render)
  let savedVisible = null;
  if (!isInitial) {
    const gd = document.getElementById("fig-forecast");
    if (gd && gd.data && gd.data.length === 12) {
      savedVisible = gd.data.map(t =>
        t.visible === undefined ? true : t.visible
      );
    }
  }

  const traces = buildProfileTraces(scenario);

  // Re-apply saved visibility — all traces so legend toggles survive a scenario switch
  if (savedVisible) {
    traces.forEach((t, i) => {
      if (savedVisible[i] !== undefined) t.visible = savedVisible[i];
    });
  }

  Plotly.react("fig-forecast", traces, profileLayout(), baseConfig);
}

fetchJSON("tower_gfd_profile").then(d => {
  profileData = d;
  renderProfile(activeScenario, true);
  // Scenario-tab wiring
  document.querySelectorAll(".scenario-tabs .tab").forEach(btn => {
    btn.addEventListener("click", () => {
      document.querySelectorAll(".scenario-tabs .tab").forEach(b => b.classList.remove("active"));
      btn.classList.add("active");
      activeScenario = btn.dataset.scenario;
      renderProfile(activeScenario, false);
    });
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
