import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
  },
  define: {
    // Fix for Node.js packages that expect 'global' to be defined
    global: 'globalThis',
  },
  optimizeDeps: {
    // Pre-bundle these dependencies to avoid issues
    include: ['amazon-cognito-identity-js'],
  },
});
