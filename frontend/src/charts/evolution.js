import {
  Chart,
  LineController,
  LineElement,
  PointElement,
  CategoryScale,
  LinearScale,
  Tooltip,
  Legend,
  Filler,
} from "chart.js";

Chart.register(
  LineController,
  LineElement,
  PointElement,
  CategoryScale,
  LinearScale,
  Tooltip,
  Legend,
  Filler,
);

const currentMonthPlugin = {
  id: "currentMonthLine",
  afterDraw(chart) {
    const idx = chart.config._currentMonthIndex;
    if (idx == null) return;
    const x = chart.scales.x.getPixelForValue(idx);
    const { top, bottom } = chart.chartArea;
    const ctx = chart.ctx;
    ctx.save();
    ctx.beginPath();
    ctx.moveTo(x, top);
    ctx.lineTo(x, bottom);
    ctx.lineWidth = 2;
    ctx.strokeStyle = "#ef4444";
    ctx.setLineDash([4, 4]);
    ctx.stroke();
    ctx.restore();
  },
};

Chart.register(currentMonthPlugin);

const evolutionInstances = new Map();

function downsample(labels, datasets, maxPoints = 120) {
  if (labels.length <= maxPoints) return { labels, datasets, step: 1 };
  const step = Math.ceil(labels.length / maxPoints);
  const sampledLabels = [];
  const sampledDatasets = datasets.map((ds) => ({ ...ds, data: [] }));
  for (let i = 0; i < labels.length; i += step) {
    sampledLabels.push(labels[i]);
    datasets.forEach((ds, idx) => {
      sampledDatasets[idx].data.push(ds.data[i]);
    });
  }
  if ((labels.length - 1) % step !== 0) {
    const last = labels.length - 1;
    sampledLabels.push(labels[last]);
    datasets.forEach((ds, idx) => {
      sampledDatasets[idx].data.push(ds.data[last]);
    });
  }
  return { labels: sampledLabels, datasets: sampledDatasets, step };
}

export function initEvolutionCharts() {
  document
    .querySelectorAll('canvas[data-chart="evolution"]')
    .forEach((canvas) => {
      const rawData = canvas.dataset.chartData;
      if (!rawData) return;

      if (evolutionInstances.has(canvas)) {
        evolutionInstances.get(canvas).destroy();
      }

      const data = JSON.parse(rawData);
      const datasets = [
        {
          label: data.principal_label || "Principal",
          data: data.principal_series,
          borderColor: "#10b981",
          backgroundColor: "rgba(16, 185, 129, 0.1)",
          fill: true,
          tension: 0.3,
          pointRadius: 0,
        },
        {
          label: data.interest_label || "Interest",
          data: data.interest_series,
          borderColor: "#f59e0b",
          backgroundColor: "rgba(245, 158, 11, 0.1)",
          fill: true,
          tension: 0.3,
          pointRadius: 0,
        },
        {
          label: data.balance_label || "Balance",
          data: data.balance_series,
          borderColor: "#6366f1",
          borderDash: [5, 5],
          fill: false,
          tension: 0.3,
          pointRadius: 0,
          yAxisID: "y1",
        },
      ];

      const sampled = downsample(data.labels, datasets);

      // Map raw current_month_index to sampled index
      let sampledIdx = null;
      if (data.current_month_index != null) {
        sampledIdx = Math.round(data.current_month_index / sampled.step);
      }

      const chart = new Chart(canvas, {
        type: "line",
        data: {
          labels: sampled.labels,
          datasets: sampled.datasets,
        },
        options: {
          responsive: true,
          interaction: { mode: "index", intersect: false },
          scales: {
            y: {
              position: "left",
              title: { display: true, text: data.payment_label || "Payment" },
            },
            y1: {
              position: "right",
              title: {
                display: true,
                text: data.balance_label || "Balance",
              },
              grid: { drawOnChartArea: false },
            },
          },
          plugins: {
            legend: { position: "bottom" },
          },
        },
      });

      chart.config._currentMonthIndex = sampledIdx;

      evolutionInstances.set(canvas, chart);
    });
}
