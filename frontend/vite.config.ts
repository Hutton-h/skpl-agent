import path from "path";
import { fileURLToPath } from "url";

import tailwindcss from "@tailwindcss/vite";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";
import svgr from "vite-plugin-svgr";

const __dirname = path.dirname(fileURLToPath(import.meta.url));

// Shared proxy bypass — serve index.html for HTML requests, proxy everything else
const bypass = (req: any) => {
	if (req.headers.accept?.includes("text/html")) return "/index.html";
};

// All backend API route prefixes that need proxying
const BACKEND_TARGET = "http://127.0.0.1:8000";

const proxyPaths = [
	"/agent",
	"/chat",
	"/sessions",
	"/credential",
	"/knowledge_bases",
	"/contexts",
	"/schedule",
	"/model",
	"/workspace",
	"/api",
	// Routes that were missing from the original config
	"/skill-library",
	"/tts",
	"/tts-model",
	"/files",
	"/quota",
	"/update",
	"/web-intelligence",
	"/desktop-automation",
	"/desktop-node",
	"/code-generation",
	"/agent-templates",
	"/firecrawl",
	"/template",
];

// Build proxy config dynamically
const proxy: Record<string, any> = {};
for (const p of proxyPaths) {
	proxy[p] = {
		target: BACKEND_TARGET,
		changeOrigin: true,
		bypass,
	};
}

export default defineConfig({
	plugins: [
		svgr(),
		react(),
		tailwindcss(),
	],
	server: {
		host: "127.0.0.1",
		proxy,
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