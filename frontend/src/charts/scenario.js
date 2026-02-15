import {
  Chart,
  BarController,
  BarElement,
  CategoryScale,
  LinearScale,
  Tooltip,
  Legend,
} from "chart.js";

Chart.register(BarController, BarElement, CategoryScale, LinearScale, Tooltip, Legend);

export function initScenarioCharts() {
  document.querySelectorAll("canvas[data-chart='scenario']").forEach((canvas) => {
    const rawData = canvas.dataset.chartData;
    if (!rawData) return;

    const data = JSON.parse(rawData);

    new Chart(canvas, {
      type: "bar",
      data: {
        labels: data.labels,
        datasets: [
          {
            label: data.beforeLabel || "Before",
            data: data.before,
            backgroundColor: "#3b82f6",
          },
          {
            label: data.afterLabel || "After",
            data: data.after,
            backgroundColor: "#f59e0b",
          },
        ],
      },
      options: {
        responsive: true,
        plugins: {
          legend: { position: "bottom" },
        },
        scales: {
          y: { beginAtZero: true },
        },
      },
    });
  });
}
