import { resolve } from "path";
import { defineConfig } from "vite";
import tailwindcss from "@tailwindcss/vite";

export default defineConfig({
  plugins: [tailwindcss()],
  base: "/static/",
  build: {
    outDir: resolve(__dirname, "../static/dist"),
    emptyOutDir: true,
    manifest: true,
    rollupOptions: {
      input: {
        main: resolve(__dirname, "src/main.js"),
      },
    },
  },
  server: {
    host: "localhost",
    port: 5173,
    origin: "http://localhost:5173",
  },
});
