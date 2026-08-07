import path from "path";
import { fileURLToPath } from "url";

import tailwindcss from "@tailwindcss/vite";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";
import svgr from "vite-plugin-svgr";

const __dirname = path.dirname(fileURLToPath(import.meta.url));

export default defineConfig({
	plugins: [
		svgr(),
		react(),
		tailwindcss(),
	],
	server: {
		host: "127.0.0.1",
		proxy: {
			"/agent": {
				target: "http://127.0.0.1:8001",
				changeOrigin: true,
				bypass: (req) => {
					if (req.headers.accept?.includes("text/html")) return "/index.html";
				},
			},
			"/chat": {
				target: "http://127.0.0.1:8001",
				changeOrigin: true,
				bypass: (req) => {
					if (req.headers.accept?.includes("text/html")) return "/index.html";
				},
			},
			"/sessions": {
				target: "http://127.0.0.1:8001",
				changeOrigin: true,
				bypass: (req) => {
					if (req.headers.accept?.includes("text/html")) return "/index.html";
				},
			},
			"/credential": {
				target: "http://127.0.0.1:8001",
				changeOrigin: true,
				bypass: (req) => {
					if (req.headers.accept?.includes("text/html")) return "/index.html";
				},
			},
			"/knowledge_bases": {
				target: "http://127.0.0.1:8001",
				changeOrigin: true,
				bypass: (req) => {
					if (req.headers.accept?.includes("text/html")) return "/index.html";
				},
			},
			"/contexts": {
				target: "http://127.0.0.1:8001",
				changeOrigin: true,
				bypass: (req) => {
					if (req.headers.accept?.includes("text/html")) return "/index.html";
				},
			},
			"/schedule": {
				target: "http://127.0.0.1:8001",
				changeOrigin: true,
				bypass: (req) => {
					if (req.headers.accept?.includes("text/html")) return "/index.html";
				},
			},
			"/model": {
				target: "http://127.0.0.1:8001",
				changeOrigin: true,
				bypass: (req) => {
					if (req.headers.accept?.includes("text/html")) return "/index.html";
				},
			},
			"/workspace": {
				target: "http://127.0.0.1:8001",
				changeOrigin: true,
				bypass: (req) => {
					if (req.headers.accept?.includes("text/html")) return "/index.html";
				},
			},
			"/api": {
				target: "http://127.0.0.1:8001",
				changeOrigin: true,
				bypass: (req) => {
					if (req.headers.accept?.includes("text/html")) return "/index.html";
				},
			},
		},
	},
	resolve: {
		alias: {
			"@": path.resolve(__dirname, "./src"),
		},
	},
	build: {
		minify: true,
		rollupOptions: {
			output: {
				inlineDynamicImports: true,
			},
		},
		chunkSizeWarningLimit: 500,
	},
});