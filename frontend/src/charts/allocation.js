import { Chart, DoughnutController, ArcElement, Tooltip, Legend } from "chart.js";

// Tree-shake: register only what we need
Chart.register(DoughnutController, ArcElement, Tooltip, Legend);

const chartInstances = new Map();

export function initCharts() {
  document.querySelectorAll("canvas[data-chart]").forEach((canvas) => {
    const chartType = canvas.dataset.chart;
    const rawData = canvas.dataset.chartData;

    if (!rawData) return;

    // Destroy existing chart on this canvas if any
    if (chartInstances.has(canvas)) {
      chartInstances.get(canvas).destroy();
    }

    const data = JSON.parse(rawData);

    if (chartType === "allocation") {
      const chart = new Chart(canvas, {
        type: "doughnut",
        data: {
          labels: data.labels,
          datasets: [
            {
              data: data.values,
              backgroundColor: data.colors || [
                "#3b82f6",
                "#10b981",
                "#f59e0b",
                "#ef4444",
                "#8b5cf6",
                "#ec4899",
                "#06b6d4",
                "#84cc16",
              ],
            },
          ],
        },
        options: {
          responsive: true,
          plugins: {
            legend: { position: "bottom" },
          },
        },
      });
      chartInstances.set(canvas, chart);
    }
  });
}
