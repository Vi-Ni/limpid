import { createChart } from "lightweight-charts";

export function initPerformanceCharts() {
  document.querySelectorAll("[data-chart='performance']").forEach((container) => {
    const rawData = container.dataset.chartData;
    if (!rawData) return;

    const data = JSON.parse(rawData);
    const chart = createChart(container, {
      width: container.clientWidth,
      height: 300,
      layout: {
        background: { color: "transparent" },
        textColor: "#64748b",
      },
      grid: {
        vertLines: { color: "#e2e8f0" },
        horzLines: { color: "#e2e8f0" },
      },
    });

    const lineSeries = chart.addLineSeries({
      color: "#3b82f6",
      lineWidth: 2,
    });

    lineSeries.setData(data);

    new ResizeObserver(() => {
      chart.applyOptions({ width: container.clientWidth });
    }).observe(container);
  });
}
