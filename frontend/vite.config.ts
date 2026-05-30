import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@':          path.resolve(__dirname, './src'),
      '@app':       path.resolve(__dirname, './src/app'),
      '@design':    path.resolve(__dirname, './src/design'),
      '@features':  path.resolve(__dirname, './src/features'),
      '@shared':    path.resolve(__dirname, './src/shared'),
      '@services':  path.resolve(__dirname, './src/services'),
      '@assets':    path.resolve(__dirname, './src/assets'),
    },
  },
  server: {
    port: 5173,
    host: '0.0.0.0',
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8020',
        changeOrigin: true,
        secure: false,
        rewrite: (path) => path,
      },
    },
  },
})
