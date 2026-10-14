import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// 参考 DeepSeek Harness 桌面版的轻量前端：纯静态资源，无需后端即可演示。
// 平台后端地址：默认 8015（场景包平台化 web 实例，连平台 8001/8000），
// 可用环境变量覆盖：CHIYU_API_BASE=http://127.0.0.1:8011 npm run dev
// 运行期在「设置向导」里填写的平台地址（localStorage chiyu_api_base）优先于本代理。
const apiTarget = process.env.CHYU_API_BASE || 'http://127.0.0.1:8015'

export default defineConfig({
  plugins: [react()],
  server: {
    host: true,
    port: 5173,
    proxy: {
      // 开发期把 /api 代理到本地内核后端（默认 8013，可经 CHIYU_API_BASE 覆盖）
      '/api': {
        target: apiTarget,
        changeOrigin: true,
      },
    },
  },
})
