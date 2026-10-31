# ☁️ Nimbus Cloud — Nube Personal Web Multiusuario (`v1.2.0`)

![Versión](https://img.shields.io/badge/version-1.2.0-38bdf8?style=for-the-badge)
![Python](https://img.shields.io/badge/Python-3.8%2B-3776AB?style=for-the-badge&logo=python&logoColor=white)
![Node.js](https://img.shields.io/badge/Node.js-18%2B-339933?style=for-the-badge&logo=nodedotjs&logoColor=white)
![Estado](https://img.shields.io/badge/estado-Estable-10b981?style=for-the-badge)

**Nimbus Cloud** es una plataforma web *full-stack* de **Nube Personal Multiusuario** diseñada para alojar, organizar, previsualizar antes de descargar, editar documentos **Markdown (`.md`)** en tiempo real y compartir archivos o carpetas tanto con otros usuarios de la nube como mediante enlaces públicos protegidos.

---

## 📋 Tabla de Contenidos

1. [Características Principales](#-características-principales)
2. [Requisitos Previos](#-requisitos-previos)
3. [Instalación y Ejecución Paso a Paso](#-instalación-y-ejecución-paso-a-paso)
4. [Estructura del Proyecto](#-estructura-del-proyecto)
5. [Atajos de Teclado](#-atajos-de-teclado)
6. [Referencia de la API REST](#-referencia-de-la-api-rest)
7. [Versionamiento y Changelog](#-versionamiento-y-changelog)

---

## ✨ Características Principales

- **🗂️ Explorador de Archivos y Carpetas Jerárquico**:
  - Subida de múltiples archivos mediante **Arrastrar y Soltar (*Drag & Drop*)** o selector de archivos.
  - Creación de carpetas anidadas, barra de ruta interactiva (*breadcrumbs*), renombrado, movimiento de archivos entre carpetas (arrastrando o desde menú), marcador de **Destacados (`⭐`)** y filtro de **Recientes**.
  - **Descarga de carpetas completas en `.ZIP`** generadas dinámicamente en el servidor.
  - **Papelera de reciclaje** con restauración en un clic o vaciado definitivo.

- **📝 Estudio y Visualizador de Markdown (`.md`) en Vivo**:
  - Creación directa de notas y documentos `.md` desde el botón **`+ Nuevo .md`**.
  - **3 Modos de Visualización**:
    1. **👁️ Vista Lectura**: Renderizado limpio con soporte para tablas GFM, listas de tareas (`- [x]`), citas, código resaltado e imágenes.
    2. **⚡ Vista Dividida**: Editor a la izquierda + vista previa sincronizada en tiempo real a la derecha.
    3. **✏️ Modo Editor**: Edición a pantalla completa con barra de herramientas de formato rápido y guardado directo en servidor (`Ctrl + S`).

- **🖼️ Vista Previa Multimedia y de Código (Antes de Descargar)**:
  - **Imágenes** (`.png`, `.jpg`, `.jpeg`, `.gif`, `.webp`, `.svg`): Controles de zoom (`+` / `-`), rotación de `90°` y restablecimiento.
  - **Video y Audio** (`.mp4`, `.webm`, `.mp3`, `.wav`, `.ogg`): Reproductor HTML5 nativo con soporte de *streaming* (`HTTP 206 Partial Content / Range`).
  - **Documentos PDF y CSV**: Visor PDF integrado y renderizador automático de tablas interactivas para archivos `.csv`.
  - **Código Fuente** (`.js`, `.ts`, `.py`, `.html`, `.css`, `.json`, `.txt`, `.sql`, etc.): Visor con formato de código y edición directa en la nube.

- **🔗 Sistema de Enlaces Públicos para Compartir (`?share=TOKEN`)**:
  - Genera enlaces públicos únicos para compartir cualquier archivo o carpeta.
  - Configuración opcional de **contraseña** (cifrada con `SHA-256`) y **fecha de expiración** (`1 hora`, `24 horas`, `7 días`, `30 días` o `Sin expiración`).
  - Contador de vistas en tiempo real y panel en la pestaña **Compartidos** para copiar o revocar accesos.

---

## 🔧 Requisitos Previos

El proyecto incluye **dos motores de servidor equivalentes** que comparten exactamente la misma base de datos y carpeta de archivos (`./storage`), por lo que solo necesitas **uno** de los siguientes:

- **Opción A (Recomendada, sin dependencias externas)**: Tener instalado **Python 3.8 o superior** (probado hasta Python 3.13).
- **Opción B (Alternativa Node.js)**: Tener instalado **Node.js 18+** y `npm`.

---

## 🚀 Instalación y Ejecución Paso a Paso

### 1. Clonar el repositorio

```bash
git clone https://github.com/Feyman-auror-c-png/Nube_Personal.git
cd Nube_Personal
```

### 2. Iniciar el servidor

#### 🐍 Método 1: Con Python (Cero instalación de paquetes)
No requiere `pip install`, ya que utiliza exclusivamente la librería estándar de Python:

```bash
python server.py
```
> En **Windows**, también puedes iniciar todo haciendo **doble clic** sobre el archivo `iniciar-nube.bat`.

#### 🟢 Método 2: Con Node.js + Express
Si prefieres ejecutar el backend con Node.js:

```bash
npm install
npm start
```

### 3. Abrir en el navegador

Una vez iniciado el servidor, abre tu navegador en:

```text
http://localhost:3000
```

> **Puerto personalizado**: Puedes cambiar el puerto definiendo la variable de entorno `PORT` (ejemplo: `PORT=8080 python server.py`).

---

## 📁 Estructura del Proyecto

```text
Nube_Personal/
├── public/                  # Frontend SPA (Cliente Web)
│   ├── index.html           # Estructura principal, modales y portal público
│   ├── styles.css           # Diseño visual, temas Oscuro/Claro y estilos Markdown
│   └── app.js               # Lógica del explorador, editor .md en vivo y previsualizador
├── storage/                 # Almacenamiento persistente en disco
│   ├── files/               # Archivos físicos guardados con UUID
│   └── metadata.json        # Índice jerárquico de carpetas, archivos y enlaces compartidos
├── server.py                # Servidor HTTP/REST multihilo en Python 3 (sin dependencias)
├── server.js                # Servidor HTTP/REST alternativo en Node.js + Express
├── iniciar-nube.bat         # Script de arranque rápido en un clic para Windows
├── package.json             # Configuración de versión (v1.1.0) y dependencias Node
├── CHANGELOG.md             # Historial detallado de versiones y cambios
└── README.md                # Documentación general e instrucciones de instalación
```

---

## ⌨️ Atajos de Teclado

| Atajo | Acción |
| :--- | :--- |
| `Ctrl + K` | Enfocar la barra de búsqueda instantánea |
| `Ctrl + S` | Guardar cambios al editar un archivo `.md`, `.csv` o de código |
| `Esc` | Cerrar el modal de vista previa, diálogo o menú contextual |
| `Clic Derecho` | Abrir el menú contextual sobre cualquier archivo o carpeta |

---

## 🔌 Referencia de la API REST

| Método | Ruta | Descripción |
| :---: | :--- | :--- |
| `GET` | `/api/items?parentId=` | Lista archivos, carpetas, ruta (*breadcrumbs*) y uso de almacenamiento |
| `POST` | `/api/upload` | Sube uno o múltiples archivos (`multipart/form-data`) |
| `POST` | `/api/folders` | Crea una nueva carpeta en el directorio indicado |
| `POST` | `/api/files/text` | Crea un nuevo documento `.md` o de texto directamente en la nube |
| `GET` | `/api/files/:id/content` | Obtiene el contenido en texto de un archivo `.md`, `.csv` o código |
| `PUT` | `/api/files/:id/content` | Guarda los cambios editados en vivo de un archivo `.md` o código |
| `GET` | `/api/files/:id/preview` | Sirve el archivo en línea para vista previa (con soporte `HTTP Range`) |
| `GET` | `/api/files/:id/download` | Descarga el archivo con su nombre original |
| `GET` | `/api/folders/:id/zip` | Comprime y descarga una carpeta completa en formato `.zip` |
| `PATCH` | `/api/items/:id` | Renombra, mueve de carpeta, destaca (`⭐`) o envía/restaura de la papelera |
| `DELETE` | `/api/items/:id` | Elimina permanentemente un archivo o carpeta del disco |
| `POST` | `/api/shares` | Genera un enlace público compartido (con contraseña y expiración opcional) |
| `GET` | `/api/public/:token` | Consulta metadatos y contenido del enlace compartido público |

---

## 📌 Versionamiento y Changelog

Este proyecto utiliza **Versionamiento Semántico (`SemVer`)**.
- **Versión actual**: `v1.1.0`
- Consulta el historial completo de cambios y novedades en el archivo [**CHANGELOG.md**](./CHANGELOG.md).
