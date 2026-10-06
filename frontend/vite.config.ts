import react from '@vitejs/plugin-react';
import { defineConfig } from 'vitest/config';

export default defineConfig({
  plugins: [react()],
  // One .env at the repository root serves backend and frontend. Vite only
  // exposes VITE_-prefixed variables to the browser bundle, so the database
  // URL, JWT secret and Gemini keys in the same file never reach the client.
  envDir: '..',
  server: {
    host: true,
  },
  test: {
    environment: 'jsdom',
    globals: true,
    include: ['src/**/*.test.{ts,tsx}'],
  },
});
