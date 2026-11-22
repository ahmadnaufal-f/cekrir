import { createApp } from 'vue'
import { createWebHashHistory } from 'vue-router'
import App from './App.vue'
import './style.css'
import { createShipmentServices } from './features/api'
import { createAppRouter } from './router'

void createShipmentServices().then(async (services) => {
  const router = createAppRouter(services, createWebHashHistory())
  const app = createApp(App, { services }).use(router)
  await router.isReady()
  app.mount('#app')
})
