# ☁️ Nimbus Cloud — Proyecto de Nube Personal Web

Aplicación web de **Nube Personal** con almacenamiento local real en disco, gestión de carpetas, estudio interactivo de **Markdown (`.md`)** con edición en vista dividida, vista previa multimedia y enlaces públicos para compartir.

## 🚀 Cómo iniciar el proyecto

### Opción 1: Un clic en Windows / Python (Sin instalar nada extra)
Haz doble clic en `iniciar-nube.bat` o ejecuta en la terminal:
```bash
python server.py
```

### Opción 2: Con Node.js + Express
Si instalas Node.js, puedes usar el servidor Express incluido (`server.js`):
```bash
npm install
npm start
```

Luego abre en tu navegador: **http://localhost:3000**

---

## ✨ Funcionalidades incluidas

1. **Gestión de Archivos y Carpetas**:
   - Subida múltiple arrastrando y soltando archivos (`Drag & Drop`) o con el botón **Subir Archivos**.
   - Creación de carpetas anidadas, ruta de navegación (*breadcrumbs*), mover archivos arrastrándolos sobre carpetas o desde el menú contextual, renombrar y destacar (`⭐`).
   - Descarga individual de archivos y **descarga de carpetas completas en `.ZIP`**.
   - **Papelera de reciclaje** con restauración o eliminación definitiva.

2. **Visualizador y Editor de Markdown (`.md`) en Vivo**:
   - Renderizado completo de **Markdown**: encabezados, tablas, listas de tareas (`- [x]`), bloques de código, citas e imágenes.
   - **3 Modos**: *Vista Lectura*, *Vista Dividida (Editor + Vista Previa en tiempo real)* y *Solo Editor*.
   - Barra de herramientas de formato rápido, contador de palabras/caracteres y guardado directo en la nube (`Ctrl + S`).
   - Botón **+ Nuevo .md** para crear documentos Markdown desde cero directamente en la nube.

3. **Vista Previa Antes de Descargar**:
   - **Imágenes** (`.png`, `.jpg`, `.svg`, `.webp`, `.gif`) con controles de zoom y rotación de 90°.
   - **Video y Audio** (`.mp4`, `.webm`, `.mp3`, `.wav`) con reproductor nativo y soporte de *streaming* (`HTTP Range`).
   - **PDF** incrustado y visor de tablas para archivos **`.csv`**.
   - **Código fuente** (`.js`, `.py`, `.html`, `.css`, `.json`, `.txt`, etc.) con visualización y edición en línea.

4. **Enlaces Públicos para Compartir (`?share=TOKEN`)**:
   - Genera enlaces para compartir cualquier archivo o carpeta.
   - Opción de **proteger con contraseña** y definir **tiempo de expiración** (1 hora, 24 horas, 7 días, 30 días o sin expiración).
   - Contador de vistas y panel de administración en la sección **Compartidos** para copiar o revocar accesos.
