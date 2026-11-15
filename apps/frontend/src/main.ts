import { createApp } from 'vue'
import App from './App.vue'
import './style.css'
import { createServices } from './services'

void createServices().then((services) =>
  createApp(App, { services }).mount('#app'),
)
