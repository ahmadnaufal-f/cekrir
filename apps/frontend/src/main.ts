import { createApp } from 'vue'
import App from './App.vue'
import './style.css'
import { createShipmentServices } from './features/api'

void createShipmentServices().then((services) =>
  createApp(App, { services }).mount('#app'),
)
