# Directrices del Proyecto & Guía de Optimización para el Agente CLI

> **Instrucción para el Agente:** Lee este documento al inicio de cada sesión para entender el contexto global del proyecto, la ubicación de sus módulos y las restricciones de ejecución. No leas otros archivos de documentación a menos que sea explícitamente necesario para la tarea asignada.

---

## 🗺️ Mapa de Arquitectura del Proyecto (Context Index)

Usar este índice para localizar rápidamente el archivo o módulo reelevante según la consulta del usuario, evitando escaneos completos del repositorio.

| Módulo / Dominio | Archivos Clave | Descripción / Responsabilidad |
| :--- | :--- | :--- |
| **Autenticación** | `src/auth/*`, `src/middleware/auth.ts` | Manejo de sesiones, JWT, roles y permisos. |
| **API & Rutas** | `src/routes/*`, `src/controllers/*` | Endpoints HTTP, controladores de entrada y validaciones. |
| **Lógica de Negocio** | `src/services/*` | Reglas de negocio principales e integraciones de servicios. |
| **Base de Datos** | `src/db/schema.ts`, `src/db/queries/*` | Modelos ORM, esquemas de tablas y queries principales. |
| **UI / Componentes** | `src/components/*` | Componentes reutilizables, vistas y hooks de cliente. |
| **Configuración** | `.env.example`, `config/*` | Variables de entorno y configuración global del sistema. |

*Nota para el usuario: Actualiza las rutas de la tabla anterior según la estructura de tu repositorio.*

---

## 📋 Reglas de Código & Estilo (Project Taste)

1. **Arquitectura:** Mantén la separación estricta de responsabilidades entre rutas, controladores y servicios.
2. **Manejo de Errores:** Retorna errores tipados y evita bloques `try/catch` vacíos o genéricos sin logging.
3. **Librerías:** No agregues nuevas dependencias externas sin confirmación previa del usuario.
4. **Patrones Preferidos:** *(Ejemplo: Usar funciones puras / Priorizar composición sobre herencia / Manejo explícito de tipos).*

---

## ⚡ Reglas de Eficiencia & Consumo de Tokens (Para el Agente)

Para minimizar el consumo innecesario de créditos y optimizar el tiempo de respuesta:

1. **Lectura Selectiva:** Consulta **únicamente** los archivos directamente relacionados con la tarea solicitada. Apóyate en el *Mapa de Arquitectura*.
2. **Ignorar Archivos Pesados:** Nunca analices archivos dentro de `node_modules/`, `dist/`, `.next/`, `build/`, `package-lock.json`, o archivos de log masivos.
3. **Pausar tras Intentos Fallidos:** Si un comando de prueba, build o refactorización falla **2 veces consecutivas**, detente, explica brevemente el bloqueo y pide confirmación al usuario antes de reintentar.
4. **Respuestas Concisas:** Limítate a aplicar los cambios requeridos en el código y dar una explicación breve. Evita resúmenes largos innecesarios si no han sido solicitados.

---

## 💡 Consejos de Uso para el Usuario

* **Inicio de Sesión:** Ejecuta el comando de inicio solicitando explícitamente:  
  `Lee PROJECT_GUIDELINES.md y ayuda a [descripción precisa del problema]`.
* **Continuidad:** Mantén la misma sesión activa mientras trabajes en un mismo flujo para aprovechar el **Prompt Caching**.
* **Prompts Específicos:** Indica la ruta del archivo cuando sea posible en lugar de hacer preguntas abiertas sobre el código.