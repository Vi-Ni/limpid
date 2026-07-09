import "./styles/main.css";

// Reveal page once CSS is injected (prevents FOUC)
document.documentElement.style.visibility = "";

import htmx from "htmx.org";
import Alpine from "alpinejs";

// Make HTMX available globally
window.htmx = htmx;

// Initialize Alpine.js
Alpine.start();
window.Alpine = Alpine;

// Chart auto-initialization after HTMX swaps
import { initCharts } from "./charts/allocation.js";
import { initEvolutionCharts } from "./charts/evolution.js";

function initAllCharts() {
  initCharts();
  initEvolutionCharts();
}

document.addEventListener("DOMContentLoaded", initAllCharts);
document.addEventListener("htmx:afterSettle", (event) => {
  initAllCharts();
  // Re-initialize Alpine.js components in swapped content
  if (event.detail.elt) {
    Alpine.initTree(event.detail.elt);
  }
});
