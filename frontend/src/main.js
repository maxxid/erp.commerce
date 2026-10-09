import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import router from './router'
// Fuentes e iconos self-hosted: los CDN externos (Google Fonts / cdnjs) son
// cross-origin y el service worker no puede cachearlos (respuesta opaca), así
// que offline la app se quedaba sin tipografía ni un solo icono.
import '@fontsource/inter/latin-300.css'
import '@fontsource/inter/latin-400.css'
import '@fontsource/inter/latin-500.css'
import '@fontsource/inter/latin-600.css'
import '@fontsource/inter/latin-700.css'
import '@fontsource/plus-jakarta-sans/latin-500.css'
import '@fontsource/plus-jakarta-sans/latin-600.css'
import '@fontsource/plus-jakarta-sans/latin-700.css'
import '@fontsource/plus-jakarta-sans/latin-800.css'
import '@fontsource/jetbrains-mono/latin-400.css'
import '@fontsource/jetbrains-mono/latin-500.css'
// FA7: all.min.css trae el catálogo de glifos + hooks de estilo + webfonts.
// solid.min.css/regular.min.css/brands.min.css por separado ya NO traen los
// iconos (solo los selectores de peso), quedaban huecos.
import '@fortawesome/fontawesome-free/css/all.min.css'
import './assets/main.css'

const app = createApp(App)
app.use(createPinia())
app.use(router)
app.mount('#app')
