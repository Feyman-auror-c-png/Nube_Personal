# 📜 Changelog (Historial de Versiones)

Todos los cambios notables en el proyecto **Nimbus Cloud (Nube Personal Web)** se documentan en este archivo.

El formato está basado en [Keep a Changelog](https://keepachangelog.com/es-ES/1.0.0/), y este proyecto se adhiere al [Versionamiento Semántico (SemVer)](https://semver.org/lang/es/).

---

## [1.1.0] - 2026-10-31

### ✨ Añadido
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
