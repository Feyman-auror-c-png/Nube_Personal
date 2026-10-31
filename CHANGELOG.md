# 📜 Changelog (Historial de Versiones)

Todos los cambios notables en el proyecto **Nimbus Cloud (Nube Personal Web)** se documentan en este archivo.

El formato está basado en [Keep a Changelog](https://keepachangelog.com/es-ES/1.0.0/), y este proyecto se adhiere al [Versionamiento Semántico (SemVer)](https://semver.org/lang/es/).

---

## [1.2.0] - 2026-10-31

### ✨ Añadido
- **Sistema Multiusuario Completo (Login, Registro y Sesiones)**:
  - Pantalla de inicio de sesión y creación de cuentas nuevas (`/api/auth/login`, `/api/auth/register`, `/api/auth/me`, `/api/auth/logout`) con tokens de sesión (`Bearer Token`) y contraseñas cifradas con `SHA-256`.
  - Cuentas de prueba preconfiguradas (`admin` / `admin123` e `invitado` / `123456`) con migración automática de los archivos previos hacia la cuenta de administrador.
- **Espacio Privado Aislado por Usuario (`ownerId`)**:
  - Cada cuenta registrada posee su propia unidad privada (**Mi Unidad**), su cuota de almacenamiento independiente y su propia papelera.
- **Colaboración entre Usuarios ("👥 Compartido conmigo")**:
  - Permite compartir archivos o carpetas internamente con otros usuarios registrados de la nube asignando permisos de **👁️ Solo lectura** o **✏️ Edición** (permitiendo coeditar documentos `.md` y código en vivo).
  - Tarjeta de perfil de usuario activa en la barra lateral y modal de **Directorio de Usuarios** (`GET /api/users`).

---

## [1.1.0] - 2026-10-31

### ✨ Añadido
- **Subida de Carpetas Completas (Drag & Drop Recursivo y Selector)**:
  - Soporte para arrastrar y soltar carpetas enteras desde el sistema operativo usando la API `webkitGetAsEntry` / `FileSystemDirectoryReader`, conservando todas las subcarpetas y archivos internos.
  - Nuevo botón **`📁⬆️ Subir Carpeta`** en la barra lateral (`webkitdirectory`).
- **Selectores Personalizados Interactivos (`.custom-select`) y Mejoras Visuales**:
  - Reemplazo de los `<select>` nativos del navegador por menús desplegables personalizados con animaciones suaves, icono chevron rotatorio y marca de selección (`✓`).
- **Estudio Markdown (`.md`) Avanzado en Vista Dividida**:
  - Creación directa de documentos `.md` desde el botón rápido `+ Nuevo .md` en la barra lateral.
  - Barra de herramientas interactiva para insertar encabezados (`H1`, `H2`), negritas, cursivas, listas de tareas (`- [ ]`), bloques de código, citas, tablas GFM y enlaces.
  - Contador de palabras y caracteres en tiempo real y guardado directo mediante `Ctrl + S`.
- **Descarga de Carpetas Completas en `.ZIP`**:
  - Compresión al vuelo en el servidor (`GET /api/folders/:id/zip`) manteniendo toda la estructura de subcarpetas.
- **Visor de Tablas CSV y Editor de Código en Línea**:
  - Previsualización automática de archivos `.csv` como tablas HTML estilizadas con opción de conmutar al editor de texto.
- **Portal Público de Enlaces Compartidos (`?share=TOKEN`)**:
  - Soporte para contraseñas cifradas con `SHA-256`, tiempos de expiración configurables (`1h`, `24h`, `7d`, `30d` o permanente) y contador de vistas.
- **Arranque Rápido y Compatibilidad Multiplataforma**:
  - Script `iniciar-nube.bat` mejorado con detección automática de ruta de Python en Windows.
  - Documentación completa de instalación, arquitectura y tabla de endpoints REST en `README.md`.

### 🔧 Corregido
- Configuración automática de codificación `UTF-8` en la salida estándar de consola en `server.py` para evitar errores `UnicodeEncodeError` en terminales Windows (`cp1252`).
- Soporte de cabeceras `HTTP 206 Partial Content (Range)` para permitir adelantar y retroceder fluidamente en la vista previa de archivos de video y audio.

---

## [1.0.0] - 2026-10-31

### 🎉 Lanzamiento Inicial
- Estructura base del proyecto **Nimbus Cloud** con doble motor de servidor compatible (`server.py` en Python 3 y `server.js` en Node.js + Express).
- Almacenamiento persistente en disco (`./storage/files/`) e indexación jerárquica en `./storage/metadata.json`.
- Subida múltiple de archivos mediante *Drag & Drop*, creación de carpetas, navegación por *breadcrumbs*, favoritos (`⭐`), buscador instantáneo (`Ctrl + K`), papelera de reciclaje y selector de tema Oscuro/Claro.
- Vista previa integrada para imágenes (con zoom y rotación), video, audio, PDF y documentos Markdown.
