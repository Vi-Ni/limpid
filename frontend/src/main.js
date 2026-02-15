import "./styles/main.css";
import htmx from "htmx.org";
import Alpine from "alpinejs";

// Make HTMX available globally
window.htmx = htmx;

// Initialize Alpine.js
Alpine.start();
window.Alpine = Alpine;

// Chart auto-initialization after HTMX swaps
import { initCharts } from "./charts/allocation.js";

document.addEventListener("DOMContentLoaded", initCharts);
document.addEventListener("htmx:afterSwap", initCharts);
