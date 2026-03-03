import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

// https://vite.dev/config/
export default defineConfig({
  plugins: [vue()],
  server: {
    proxy: {
      // 代理配置，用于访问本地后端服务
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        rewrite: (path) => path,
        configure: (proxy, options) => {
          // 对于OPTIONS请求返回200，避免CORS预检错误
          proxy.on('proxyRes', (proxyRes, req, res) => {
            // 添加CORS头信息
            proxyRes.headers['Access-Control-Allow-Origin'] = '*';
            proxyRes.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS';
            proxyRes.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization';
            
            if (req.method === 'OPTIONS') {
              res.statusCode = 200;
              res.end();
              return true;
            }
          });
        }
      },
      // 健康检查接口代理
      '/health': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        rewrite: (path) => path
      }
    }
  }
})
