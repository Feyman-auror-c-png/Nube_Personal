#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Servidor Local para Nube Personal (Nimbus Cloud)
Compatible con el mismo almacenamiento en disco (./storage) y API REST que server.js
"""

import os
import sys
import json
import uuid
import time
import shutil
import zipfile
import hashlib
import mimetypes
import urllib.parse
from io import BytesIO
from datetime import datetime, timezone
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from email.parser import BytesParser
from email.policy import default as default_policy

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PUBLIC_DIR = os.path.join(BASE_DIR, "public")
STORAGE_DIR = os.path.join(BASE_DIR, "storage")
FILES_DIR = os.path.join(STORAGE_DIR, "files")
META_PATH = os.path.join(STORAGE_DIR, "metadata.json")
PORT = int(os.environ.get("PORT", 3000))

# Asegurar tipos MIME comunes
mimetypes.add_type("text/markdown", ".md")
mimetypes.add_type("text/markdown", ".markdown")
mimetypes.add_type("application/javascript", ".js")
mimetypes.add_type("text/css", ".css")
mimetypes.add_type("image/svg+xml", ".svg")
mimetypes.add_type("image/webp", ".webp")
mimetypes.add_type("application/json", ".json")


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def hash_password(password: str) -> str:
    if not password:
        return ""
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def ensure_storage():
    os.makedirs(PUBLIC_DIR, exist_ok=True)
    os.makedirs(FILES_DIR, exist_ok=True)
    if not os.path.exists(META_PATH):
        seed_initial_data()


def load_meta():
    ensure_storage()
    try:
        with open(META_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
            if "items" not in data:
                data["items"] = []
            if "shares" not in data:
                data["shares"] = []
            if "settings" not in data:
                data["settings"] = {"quotaBytes": 5 * 1024 * 1024 * 1024, "pinHash": ""}
            return data
    except Exception:
        return {
            "items": [],
            "shares": [],
            "settings": {"quotaBytes": 5 * 1024 * 1024 * 1024, "pinHash": ""},
        }


def save_meta(data):
    os.makedirs(STORAGE_DIR, exist_ok=True)
    temp_path = META_PATH + ".tmp"
    with open(temp_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(temp_path, META_PATH)


def seed_initial_data():
    """Crea carpetas y archivos de demostración en el primer inicio."""
    os.makedirs(FILES_DIR, exist_ok=True)
    created = now_iso()

    folder_docs_id = str(uuid.uuid4())
    folder_proj_id = str(uuid.uuid4())

    welcome_md_id = str(uuid.uuid4())
    welcome_md_disk = f"{welcome_md_id}.md"
    welcome_content = """# ☁️ ¡Bienvenido a tu Nube Personal (Nimbus Cloud)!

Esta es tu **nube personal local**, diseñada para gestionar tus archivos, carpetas, código, multimedia y documentos **Markdown (`.md`)** con vista previa instantánea y edición en vivo.

---

## ✨ Características Principales

- 📁 **Gestión de Carpetas**: Crea carpetas anidadas, mueve archivos entre ellas, renombra o descarga carpetas enteras en `.zip`.
- 📝 **Estudio Markdown (`.md`) en Vivo**:
  - Visualización limpia con soporte para **tablas**, **listas de tareas**, **bloques de código** con resaltado de sintaxis y citas.
  - **Editor en vista dividida**: Edita tus archivos `.md` y mira los cambios en tiempo real. Presiona `Ctrl + S` o el botón **Guardar** para actualizar el archivo directamente en el servidor.
- 🖼️ **Vista Previa Multimedia y de Código**:
  - **Imágenes** (`.png`, `.jpg`, `.svg`, `.webp`, `.gif`) con zoom y rotación.
  - **Video y Audio** (`.mp4`, `.webm`, `.mp3`, `.wav`) con reproductor integrado y soporte de streaming.
  - **Documentos PDF** y tablas **CSV** interactivas.
  - **Archivos de código** (`.js`, `.py`, `.html`, `.css`, `.json`) con resaltado de sintaxis y edición directa.
- 🔗 **Enlaces para Compartir**:
  - Genera enlaces públicos para cualquier archivo o carpeta.
  - Configura **contraseña opcional** y **fecha de expiración**.

---

## 📊 Ejemplo de Tabla Markdown

| Función | Estado | Atajo / Acción |
| :--- | :---: | :--- |
| Subir archivos | ✅ Activo | Arrastrar y soltar (Drag & Drop) |
| Buscar archivos | ✅ Activo | `Ctrl + K` en la barra superior |
| Editar Markdown | ✅ Activo | Clic en archivo `.md` → **Vista Dividida** |
| Compartir con clave | ✅ Activo | Menú del archivo → **Compartir** |
| Descargar carpeta ZIP | ✅ Activo | Menú de carpeta → **Descargar ZIP** |

---

## 💻 Ejemplo de Código con Resaltado

```javascript
// Ejemplo rápido de uso de la API de tu Nube Personal
async function obtenerArchivos(parentId = null) {
  const res = await fetch(`/api/items?parentId=${parentId || ''}`);
  const data = await res.json();
  console.log(`Archivos cargados: ${data.items.length}`);
  return data.items;
}
```

> 💡 **Tip:** Prueba cambiar a **Vista Dividida** arriba a la derecha en esta ventana para editar este documento en tiempo real.
"""
    with open(os.path.join(FILES_DIR, welcome_md_disk), "w", encoding="utf-8") as f:
        f.write(welcome_content)

    notes_md_id = str(uuid.uuid4())
    notes_md_disk = f"{notes_md_id}.md"
    notes_content = """# 📋 Notas del Proyecto y Tareas

Aquí puedes organizar tus ideas y apuntes dentro de la carpeta **Documentos**.

## Lista de Pendientes
- [x] Configurar servidor local de la nube personal
- [x] Probar el visualizador y editor de archivos `.md`
- [ ] Subir mis primeros archivos arrastrándolos a la pantalla
- [ ] Crear un enlace compartido de prueba

## Comandos Útiles
```bash
# Iniciar con Python (sin dependencias externas)
python server.py

# O iniciar con Node.js + Express
npm install && npm start
```
"""
    with open(os.path.join(FILES_DIR, notes_md_disk), "w", encoding="utf-8") as f:
        f.write(notes_content)

    code_id = str(uuid.uuid4())
    code_disk = f"{code_id}.js"
    code_content = """/**
 * Script de demostración en la carpeta Proyectos
 * Puedes previsualizar y editar este código directamente desde la nube.
 */

const configuracionNube = {
  nombre: "Nimbus Personal Cloud",
  version: "1.0.0",
  formatosSoportados: ["md", "png", "jpg", "svg", "mp4", "mp3", "pdf", "csv", "js", "py", "json"],
  almacenamientoLocal: true,
};

function saludarUsuario(usuario = "Creador") {
  return `¡Hola, ${usuario}! Tu nube personal está funcionando al 100%.`;
}

console.log(saludarUsuario());
"""
    with open(os.path.join(FILES_DIR, code_disk), "w", encoding="utf-8") as f:
        f.write(code_content)

    csv_id = str(uuid.uuid4())
    csv_disk = f"{csv_id}.csv"
    csv_content = """Proyecto,Categoria,Estado,Prioridad,Progreso
Nube Personal Web,Full-Stack,Completado,Alta,100%
Visualizador Markdown,Frontend,Completado,Alta,100%
Enlaces Compartidos,Seguridad,Activo,Media,95%
App Movil Futura,Ideas,Planificado,Baja,20%
"""
    with open(os.path.join(FILES_DIR, csv_disk), "w", encoding="utf-8") as f:
        f.write(csv_content)

    svg_id = str(uuid.uuid4())
    svg_disk = f"{svg_id}.svg"
    svg_content = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 600 360" width="600" height="360">
  <defs>
    <linearGradient id="bg" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#0f172a"/>
      <stop offset="50%" stop-color="#1e1b4b"/>
      <stop offset="100%" stop-color="#0f172a"/>
    </linearGradient>
    <linearGradient id="cloudGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#38bdf8"/>
      <stop offset="100%" stop-color="#6366f1"/>
    </linearGradient>
  </defs>
  <rect width="600" height="360" rx="24" fill="url(#bg)"/>
  <circle cx="480" cy="80" r="90" fill="#6366f1" opacity="0.15"/>
  <circle cx="120" cy="280" r="110" fill="#38bdf8" opacity="0.12"/>
  <path d="M210 215 H395 A45 45 0 0 0 405 127 A65 65 0 0 0 280 105 A55 55 0 0 0 185 150 A40 40 0 0 0 210 215 Z" fill="url(#cloudGrad)"/>
  <text x="300" y="275" font-family="system-ui, sans-serif" font-size="26" font-weight="bold" fill="#f8fafc" text-anchor="middle">Nimbus Personal Cloud</text>
  <text x="300" y="308" font-family="system-ui, sans-serif" font-size="15" fill="#94a3b8" text-anchor="middle">Vista previa de gráficos vectoriales e imágenes</text>
</svg>"""
    with open(os.path.join(FILES_DIR, svg_disk), "w", encoding="utf-8") as f:
        f.write(svg_content)

    items = [
        {
            "id": folder_docs_id,
            "name": "Documentos",
            "type": "folder",
            "parentId": None,
            "size": 0,
            "mimeType": "inode/directory",
            "starred": True,
            "trashed": False,
            "createdAt": created,
            "updatedAt": created,
        },
        {
            "id": folder_proj_id,
            "name": "Proyectos",
            "type": "folder",
            "parentId": None,
            "size": 0,
            "mimeType": "inode/directory",
            "starred": False,
            "trashed": False,
            "createdAt": created,
            "updatedAt": created,
        },
        {
            "id": welcome_md_id,
            "name": "Bienvenida a tu Nube.md",
            "type": "file",
            "parentId": None,
            "size": len(welcome_content.encode("utf-8")),
            "mimeType": "text/markdown",
            "diskName": welcome_md_disk,
            "starred": True,
            "trashed": False,
            "createdAt": created,
            "updatedAt": created,
        },
        {
            "id": svg_id,
            "name": "Portada Nimbus Cloud.svg",
            "type": "file",
            "parentId": None,
            "size": len(svg_content.encode("utf-8")),
            "mimeType": "image/svg+xml",
            "diskName": svg_disk,
            "starred": False,
            "trashed": False,
            "createdAt": created,
            "updatedAt": created,
        },
        {
            "id": csv_id,
            "name": "Roadmap Nube.csv",
            "type": "file",
            "parentId": None,
            "size": len(csv_content.encode("utf-8")),
            "mimeType": "text/csv",
            "diskName": csv_disk,
            "starred": False,
            "trashed": False,
            "createdAt": created,
            "updatedAt": created,
        },
        {
            "id": notes_md_id,
            "name": "Notas y Tareas.md",
            "type": "file",
            "parentId": folder_docs_id,
            "size": len(notes_content.encode("utf-8")),
            "mimeType": "text/markdown",
            "diskName": notes_md_disk,
            "starred": False,
            "trashed": False,
            "createdAt": created,
            "updatedAt": created,
        },
        {
            "id": code_id,
            "name": "demo-nube.js",
            "type": "file",
            "parentId": folder_proj_id,
            "size": len(code_content.encode("utf-8")),
            "mimeType": "application/javascript",
            "diskName": code_disk,
            "starred": False,
            "trashed": False,
            "createdAt": created,
            "updatedAt": created,
        },
    ]

    save_meta({
        "items": items,
        "shares": [],
        "settings": {"quotaBytes": 5 * 1024 * 1024 * 1024, "pinHash": ""},
    })


def get_descendant_ids(items, root_id):
    """Obtiene todos los IDs hijos recursivamente para una carpeta."""
    result = set()
    stack = [root_id]
    while stack:
        current = stack.pop()
        for it in items:
            if it.get("parentId") == current and it["id"] not in result:
                result.add(it["id"])
                if it["type"] == "folder":
                    stack.append(it["id"])
    return result


def compute_folder_size(items, folder_id):
    desc = get_descendant_ids(items, folder_id)
    return sum(
        it.get("size", 0)
        for it in items
        if it["id"] in desc and it["type"] == "file" and not it.get("trashed", False)
    )


def build_breadcrumbs(items, folder_id):
    crumbs = []
    curr_id = folder_id
    visited = set()
    item_map = {it["id"]: it for it in items}
    while curr_id and curr_id in item_map and curr_id not in visited:
        visited.add(curr_id)
        folder = item_map[curr_id]
        crumbs.append({"id": folder["id"], "name": folder["name"]})
        curr_id = folder.get("parentId")
    crumbs.reverse()
    return crumbs


def ensure_folder_path(meta, root_parent_id, folder_parts, now_str, folder_cache):
    """Crea o reutiliza una jerarquía de carpetas (ej. ['Proyecto', 'src']) bajo root_parent_id."""
    curr_parent = root_parent_id
    created_folders = []
    for part in folder_parts:
        clean_part = part.strip()
        if not clean_part:
            continue
        cache_key = (curr_parent or "ROOT", clean_part.lower())
        if cache_key in folder_cache:
            curr_parent = folder_cache[cache_key]
            continue
        existing = next(
            (
                it
                for it in meta["items"]
                if it["type"] == "folder"
                and not it.get("trashed", False)
                and (it.get("parentId") or None) == curr_parent
                and it["name"].lower() == clean_part.lower()
            ),
            None,
        )
        if existing:
            curr_parent = existing["id"]
            folder_cache[cache_key] = curr_parent
        else:
            new_folder = {
                "id": str(uuid.uuid4()),
                "name": clean_part,
                "type": "folder",
                "parentId": curr_parent,
                "size": 0,
                "mimeType": "inode/directory",
                "starred": False,
                "trashed": False,
                "createdAt": now_str,
                "updatedAt": now_str,
            }
            meta["items"].append(new_folder)
            created_folders.append(new_folder)
            curr_parent = new_folder["id"]
            folder_cache[cache_key] = curr_parent
    return curr_parent, created_folders


def parse_multipart_form_data(headers, body: bytes):
    """Parsea multipart/form-data usando la librería estándar email de Python 3."""
    content_type = headers.get("Content-Type", "")
    raw_msg = (
        f"Content-Type: {content_type}\r\nMIME-Version: 1.0\r\n\r\n".encode("utf-8")
        + body
    )
    msg = BytesParser(policy=default_policy).parsebytes(raw_msg)
    fields = {}
    files = []
    if msg.is_multipart():
        for part in msg.iter_parts():
            cd = part.get("Content-Disposition", "")
            if not cd:
                continue
            params = {}
            for seg in cd.split(";")[1:]:
                if "=" in seg:
                    k, v = seg.strip().split("=", 1)
                    params[k.strip()] = v.strip().strip('"')
            field_name = params.get("name", "")
            filename = part.get_filename()
            payload = part.get_payload(decode=True) or b""
            if filename is not None:
                files.append({
                    "field": field_name,
                    "filename": filename,
                    "contentType": part.get_content_type() or "application/octet-stream",
                    "data": payload,
                })
            else:
                fields[field_name] = payload.decode("utf-8", errors="replace")
    return fields, files


def is_share_expired(share):
    exp = share.get("expiresAt")
    if not exp:
        return False
    try:
        exp_dt = datetime.fromisoformat(exp.replace("Z", "+00:00"))
        return datetime.now(timezone.utc) > exp_dt
    except Exception:
        return False


class CloudRequestHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, fmt, *args):
        # Registro limpio en consola
        sys.stdout.write(f"[Nube] {self.address_string()} - {fmt % args}\n")

    def send_json(self, status_code, payload):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def read_json_body(self):
        length = int(self.headers.get("Content-Length", 0))
        if length <= 0:
            return {}
        raw = self.rfile.read(length)
        try:
            return json.loads(raw.decode("utf-8"))
        except Exception:
            return {}

    def serve_file_bytes(self, file_path, mime_type, download_name=None):
        if not os.path.exists(file_path):
            self.send_json(404, {"error": "Archivo físico no encontrado en disco"})
            return

        file_size = os.path.getsize(file_path)
        range_header = self.headers.get("Range")

        if range_header and range_header.startswith("bytes="):
            try:
                byte_range = range_header.replace("bytes=", "").split("-")
                start = int(byte_range[0]) if byte_range[0] else 0
                end = int(byte_range[1]) if len(byte_range) > 1 and byte_range[1] else file_size - 1
                end = min(end, file_size - 1)
                if start > end or start >= file_size:
                    self.send_response(416)
                    self.send_header("Content-Range", f"bytes */{file_size}")
                    self.end_headers()
                    return
                chunk_len = end - start + 1
                self.send_response(206)
                self.send_header("Content-Type", mime_type)
                self.send_header("Accept-Ranges", "bytes")
                self.send_header("Content-Range", f"bytes {start}-{end}/{file_size}")
                self.send_header("Content-Length", str(chunk_len))
                self.end_headers()
                with open(file_path, "rb") as f:
                    f.seek(start)
                    self.wfile.write(f.read(chunk_len))
                return
            except Exception:
                pass

        self.send_response(200)
        self.send_header("Content-Type", mime_type)
        self.send_header("Content-Length", str(file_size))
        self.send_header("Accept-Ranges", "bytes")
        if download_name:
            encoded_name = urllib.parse.quote(download_name)
            self.send_header(
                "Content-Disposition",
                f"attachment; filename=\"{download_name.encode('ascii', 'ignore').decode('ascii') or 'archivo'}\"; filename*=UTF-8''{encoded_name}",
            )
        else:
            self.send_header("Content-Disposition", "inline")
        self.end_headers()
        with open(file_path, "rb") as f:
            shutil.copyfileobj(f, self.wfile)

    def serve_folder_zip(self, meta, folder_item):
        items = meta["items"]
        buf = BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
            def add_folder_to_zip(parent_id, rel_prefix):
                children = [
                    it for it in items
                    if it.get("parentId") == parent_id and not it.get("trashed", False)
                ]
                for child in children:
                    if child["type"] == "folder":
                        sub_prefix = f"{rel_prefix}{child['name']}/"
                        zf.writestr(sub_prefix, b"")
                        add_folder_to_zip(child["id"], sub_prefix)
                    else:
                        disk_path = os.path.join(FILES_DIR, child.get("diskName", ""))
                        if os.path.exists(disk_path):
                            zf.write(disk_path, arcname=f"{rel_prefix}{child['name']}")

            add_folder_to_zip(folder_item["id"], "")

        zip_bytes = buf.getvalue()
        zip_name = f"{folder_item['name']}.zip"
        encoded_name = urllib.parse.quote(zip_name)
        self.send_response(200)
        self.send_header("Content-Type", "application/zip")
        self.send_header("Content-Length", str(len(zip_bytes)))
        self.send_header(
            "Content-Disposition",
            f"attachment; filename=\"carpeta.zip\"; filename*=UTF-8''{encoded_name}",
        )
        self.end_headers()
        self.wfile.write(zip_bytes)

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        query = urllib.parse.parse_qs(parsed.query)

        # --- API: Listar elementos y estadísticas ---
        if path == "/api/items":
            meta = load_meta()
            items = meta["items"]
            shares = meta["shares"]
            active_share_ids = {
                s["itemId"] for s in shares if not is_share_expired(s)
            }

            enriched = []
            for it in items:
                copy_it = dict(it)
                if copy_it["type"] == "folder":
                    copy_it["size"] = compute_folder_size(items, copy_it["id"])
                    copy_it["childrenCount"] = sum(
                        1
                        for c in items
                        if c.get("parentId") == copy_it["id"] and not c.get("trashed", False)
                    )
                copy_it["isShared"] = copy_it["id"] in active_share_ids
                enriched.append(copy_it)

            parent_id = query.get("parentId", [None])[0]
            if parent_id in ("", "null", "root"):
                parent_id = None

            total_used = sum(
                it.get("size", 0)
                for it in items
                if it["type"] == "file" and not it.get("trashed", False)
            )
            trash_used = sum(
                it.get("size", 0)
                for it in items
                if it["type"] == "file" and it.get("trashed", False)
            )

            self.send_json(200, {
                "items": enriched,
                "breadcrumbs": build_breadcrumbs(items, parent_id),
                "stats": {
                    "usedBytes": total_used,
                    "trashBytes": trash_used,
                    "quotaBytes": meta.get("settings", {}).get("quotaBytes", 5 * 1024 * 1024 * 1024),
                    "totalFiles": sum(1 for it in items if it["type"] == "file" and not it.get("trashed", False)),
                    "totalFolders": sum(1 for it in items if it["type"] == "folder" and not it.get("trashed", False)),
                },
            })
            return

        # --- API: Obtener contenido de texto / Markdown o preview ---
        if path.startswith("/api/files/") and path.endswith("/content"):
            file_id = path.split("/")[3]
            meta = load_meta()
            item = next((it for it in meta["items"] if it["id"] == file_id and it["type"] == "file"), None)
            if not item:
                self.send_json(404, {"error": "Archivo no encontrado"})
                return
            disk_path = os.path.join(FILES_DIR, item.get("diskName", ""))
            if not os.path.exists(disk_path):
                self.send_json(404, {"error": "Archivo no existe en disco"})
                return
            try:
                with open(disk_path, "r", encoding="utf-8") as f:
                    text = f.read()
            except UnicodeDecodeError:
                with open(disk_path, "r", encoding="latin-1", errors="replace") as f:
                    text = f.read()
            self.send_json(200, {"id": item["id"], "name": item["name"], "content": text, "updatedAt": item["updatedAt"]})
            return

        if path.startswith("/api/files/") and path.endswith("/preview"):
            file_id = path.split("/")[3]
            meta = load_meta()
            item = next((it for it in meta["items"] if it["id"] == file_id and it["type"] == "file"), None)
            if not item:
                self.send_json(404, {"error": "Archivo no encontrado"})
                return
            disk_path = os.path.join(FILES_DIR, item.get("diskName", ""))
            mime = item.get("mimeType") or mimetypes.guess_type(item["name"])[0] or "application/octet-stream"
            self.serve_file_bytes(disk_path, mime, download_name=None)
            return

        if path.startswith("/api/files/") and path.endswith("/download"):
            file_id = path.split("/")[3]
            meta = load_meta()
            item = next((it for it in meta["items"] if it["id"] == file_id and it["type"] == "file"), None)
            if not item:
                self.send_json(404, {"error": "Archivo no encontrado"})
                return
            disk_path = os.path.join(FILES_DIR, item.get("diskName", ""))
            mime = item.get("mimeType") or mimetypes.guess_type(item["name"])[0] or "application/octet-stream"
            self.serve_file_bytes(disk_path, mime, download_name=item["name"])
            return

        if path.startswith("/api/folders/") and path.endswith("/zip"):
            folder_id = path.split("/")[3]
            meta = load_meta()
            folder = next((it for it in meta["items"] if it["id"] == folder_id and it["type"] == "folder"), None)
            if not folder:
                self.send_json(404, {"error": "Carpeta no encontrada"})
                return
            self.serve_folder_zip(meta, folder)
            return

        # --- API: Listar enlaces compartidos ---
        if path == "/api/shares":
            meta = load_meta()
            item_map = {it["id"]: it for it in meta["items"]}
            result = []
            for s in meta["shares"]:
                it = item_map.get(s["itemId"])
                if not it or it.get("trashed", False):
                    continue
                result.append({
                    "token": s["token"],
                    "itemId": s["itemId"],
                    "itemName": it["name"],
                    "itemType": it["type"],
                    "mimeType": it.get("mimeType", ""),
                    "size": compute_folder_size(meta["items"], it["id"]) if it["type"] == "folder" else it.get("size", 0),
                    "hasPassword": bool(s.get("passwordHash")),
                    "expiresAt": s.get("expiresAt"),
                    "expired": is_share_expired(s),
                    "views": s.get("views", 0),
                    "createdAt": s.get("createdAt"),
                })
            self.send_json(200, {"shares": result})
            return

        # --- API: Vista pública de enlace compartido ---
        if path.startswith("/api/public/"):
            parts = path.strip("/").split("/")
            # /api/public/:token  o /api/public/:token/raw
            token = parts[2] if len(parts) >= 3 else ""
            action = parts[3] if len(parts) >= 4 else "info"

            meta = load_meta()
            share = next((s for s in meta["shares"] if s["token"] == token), None)
            if not share:
                self.send_json(404, {"error": "Este enlace compartido no existe o fue revocado."})
                return
            if is_share_expired(share):
                self.send_json(410, {"error": "Este enlace compartido ha expirado."})
                return

            root_item = next((it for it in meta["items"] if it["id"] == share["itemId"] and not it.get("trashed", False)), None)
            if not root_item:
                self.send_json(404, {"error": "El elemento compartido ya no está disponible."})
                return

            provided_pwd = query.get("password", [""])[0] or self.headers.get("X-Share-Password", "")
            if share.get("passwordHash"):
                if not provided_pwd or hash_password(provided_pwd) != share["passwordHash"]:
                    self.send_json(401, {
                        "requiresPassword": True,
                        "itemName": root_item["name"],
                        "itemType": root_item["type"],
                    })
                    return

            if action == "info":
                share["views"] = share.get("views", 0) + 1
                save_meta(meta)

                response_data = {
                    "token": token,
                    "item": {
                        "id": root_item["id"],
                        "name": root_item["name"],
                        "type": root_item["type"],
                        "mimeType": root_item.get("mimeType", ""),
                        "size": compute_folder_size(meta["items"], root_item["id"]) if root_item["type"] == "folder" else root_item.get("size", 0),
                        "updatedAt": root_item.get("updatedAt"),
                    },
                    "expiresAt": share.get("expiresAt"),
                    "views": share["views"],
                }

                if root_item["type"] == "folder":
                    desc_ids = get_descendant_ids(meta["items"], root_item["id"])
                    sub_items = [
                        {
                            "id": it["id"],
                            "name": it["name"],
                            "type": it["type"],
                            "parentId": it["parentId"],
                            "mimeType": it.get("mimeType", ""),
                            "size": compute_folder_size(meta["items"], it["id"]) if it["type"] == "folder" else it.get("size", 0),
                            "updatedAt": it.get("updatedAt"),
                        }
                        for it in meta["items"]
                        if it["id"] in desc_ids and not it.get("trashed", False)
                    ]
                    response_data["children"] = sub_items
                elif (
                    root_item["name"].lower().endswith((".md", ".markdown", ".txt", ".js", ".py", ".json", ".css", ".html", ".csv"))
                    and root_item.get("size", 0) < 2 * 1024 * 1024
                ):
                    disk_path = os.path.join(FILES_DIR, root_item.get("diskName", ""))
                    if os.path.exists(disk_path):
                        try:
                            with open(disk_path, "r", encoding="utf-8", errors="replace") as f:
                                response_data["textContent"] = f.read()
                        except Exception:
                            pass

                self.send_json(200, response_data)
                return

            if action == "raw":
                target_id = query.get("itemId", [root_item["id"]])[0]
                download_flag = query.get("download", ["0"])[0] == "1"
                if target_id != root_item["id"]:
                    desc_ids = get_descendant_ids(meta["items"], root_item["id"])
                    if target_id not in desc_ids:
                        self.send_json(403, {"error": "Acceso denegado fuera de la carpeta compartida"})
                        return
                target_item = next((it for it in meta["items"] if it["id"] == target_id and not it.get("trashed", False)), None)
                if not target_item:
                    self.send_json(404, {"error": "Elemento no encontrado"})
                    return
                if target_item["type"] == "folder":
                    self.serve_folder_zip(meta, target_item)
                    return
                disk_path = os.path.join(FILES_DIR, target_item.get("diskName", ""))
                mime = target_item.get("mimeType") or mimetypes.guess_type(target_item["name"])[0] or "application/octet-stream"
                self.serve_file_bytes(disk_path, mime, download_name=target_item["name"] if download_flag else None)
                return

        # --- Servir archivos estáticos del Frontend ---
        rel_path = path.lstrip("/")
        if not rel_path or rel_path == "":
            rel_path = "index.html"
        static_file = os.path.normpath(os.path.join(PUBLIC_DIR, rel_path))
        if not static_file.startswith(PUBLIC_DIR) or not os.path.isfile(static_file):
            static_file = os.path.join(PUBLIC_DIR, "index.html")

        mime = mimetypes.guess_type(static_file)[0] or "text/html; charset=utf-8"
        self.serve_file_bytes(static_file, mime)

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        # --- API: Crear nueva carpeta ---
        if path == "/api/folders":
            body = self.read_json_body()
            name = (body.get("name") or "").strip()
            parent_id = body.get("parentId") or None
            if parent_id in ("", "null", "root"):
                parent_id = None
            if not name:
                self.send_json(400, {"error": "El nombre de la carpeta es obligatorio"})
                return

            meta = load_meta()
            now = now_iso()
            new_folder = {
                "id": str(uuid.uuid4()),
                "name": name,
                "type": "folder",
                "parentId": parent_id,
                "size": 0,
                "mimeType": "inode/directory",
                "starred": False,
                "trashed": False,
                "createdAt": now,
                "updatedAt": now,
            }
            meta["items"].append(new_folder)
            save_meta(meta)
            self.send_json(201, {"item": new_folder})
            return

        # --- API: Crear archivo de texto o Markdown (.md) directamente ---
        if path == "/api/files/text":
            body = self.read_json_body()
            name = (body.get("name") or "Documento sin título.md").strip()
            content = body.get("content") or ""
            parent_id = body.get("parentId") or None
            if parent_id in ("", "null", "root"):
                parent_id = None

            if "." not in name:
                name += ".md"
            ext = os.path.splitext(name)[1].lower() or ".md"
            file_id = str(uuid.uuid4())
            disk_name = f"{file_id}{ext}"
            disk_path = os.path.join(FILES_DIR, disk_name)
            encoded = content.encode("utf-8")
            with open(disk_path, "wb") as f:
                f.write(encoded)

            mime = mimetypes.guess_type(name)[0] or ("text/markdown" if ext == ".md" else "text/plain")
            now = now_iso()
            meta = load_meta()
            new_item = {
                "id": file_id,
                "name": name,
                "type": "file",
                "parentId": parent_id,
                "size": len(encoded),
                "mimeType": mime,
                "diskName": disk_name,
                "starred": False,
                "trashed": False,
                "createdAt": now,
                "updatedAt": now,
            }
            meta["items"].append(new_item)
            save_meta(meta)
            self.send_json(201, {"item": new_item})
            return

        # --- API: Subir uno o varios archivos o carpetas completas (multipart/form-data) ---
        if path == "/api/upload":
            length = int(self.headers.get("Content-Length", 0))
            if length <= 0:
                self.send_json(400, {"error": "No se recibieron datos para subir"})
                return
            raw_body = self.rfile.read(length)
            fields, uploaded_files = parse_multipart_form_data(self.headers, raw_body)
            parent_id = fields.get("parentId") or None
            if parent_id in ("", "null", "root"):
                parent_id = None

            rel_paths = []
            if "relativePaths" in fields:
                try:
                    rel_paths = json.loads(fields["relativePaths"])
                except Exception:
                    rel_paths = []

            empty_folders = []
            if "emptyFolders" in fields:
                try:
                    empty_folders = json.loads(fields["emptyFolders"])
                except Exception:
                    empty_folders = []

            if not uploaded_files and not empty_folders:
                self.send_json(400, {"error": "No se seleccionaron archivos ni carpetas válidas"})
                return

            meta = load_meta()
            now = now_iso()
            created_items = []
            folder_cache = {}

            # Crear carpetas vacías o estructura base enviada
            for ef_path in empty_folders:
                norm_ef = str(ef_path).replace("\\", "/").strip("/")
                parts = [p for p in norm_ef.split("/") if p and p != "."]
                if parts:
                    _, new_f = ensure_folder_path(meta, parent_id, parts, now, folder_cache)
                    created_items.extend(new_f)

            for idx, uf in enumerate(uploaded_files):
                rel_p = rel_paths[idx] if idx < len(rel_paths) and rel_paths[idx] else (uf["filename"] or "archivo")
                norm_rel = str(rel_p).replace("\\", "/").strip("/")
                parts = [p for p in norm_rel.split("/") if p and p != "."]

                if len(parts) > 1:
                    folder_parts = parts[:-1]
                    orig_name = parts[-1]
                    target_parent_id, new_f = ensure_folder_path(meta, parent_id, folder_parts, now, folder_cache)
                    created_items.extend(new_f)
                else:
                    target_parent_id = parent_id
                    orig_name = parts[0] if parts else os.path.basename(uf["filename"] or "archivo")

                ext = os.path.splitext(orig_name)[1].lower()
                file_id = str(uuid.uuid4())
                disk_name = f"{file_id}{ext}"
                disk_path = os.path.join(FILES_DIR, disk_name)
                with open(disk_path, "wb") as f:
                    f.write(uf["data"])

                guessed_mime = mimetypes.guess_type(orig_name)[0]
                mime = guessed_mime or uf["contentType"] or "application/octet-stream"
                item = {
                    "id": file_id,
                    "name": orig_name,
                    "type": "file",
                    "parentId": target_parent_id,
                    "size": len(uf["data"]),
                    "mimeType": mime,
                    "diskName": disk_name,
                    "starred": False,
                    "trashed": False,
                    "createdAt": now,
                    "updatedAt": now,
                }
                meta["items"].append(item)
                created_items.append(item)

            save_meta(meta)
            self.send_json(201, {"items": created_items})
            return

        # --- API: Crear enlace compartido ---
        if path == "/api/shares":
            body = self.read_json_body()
            item_id = body.get("itemId")
            password = (body.get("password") or "").strip()
            expires_in_hours = body.get("expiresInHours")

            meta = load_meta()
            item = next((it for it in meta["items"] if it["id"] == item_id and not it.get("trashed", False)), None)
            if not item:
                self.send_json(404, {"error": "El archivo o carpeta no existe"})
                return

            expires_at = None
            if expires_in_hours and float(expires_in_hours) > 0:
                exp_ts = time.time() + float(expires_in_hours) * 3600
                expires_at = datetime.fromtimestamp(exp_ts, tz=timezone.utc).isoformat()

            token = uuid.uuid4().hex[:12]
            share_obj = {
                "token": token,
                "itemId": item["id"],
                "passwordHash": hash_password(password) if password else "",
                "expiresAt": expires_at,
                "views": 0,
                "createdAt": now_iso(),
            }
            meta["shares"].append(share_obj)
            save_meta(meta)
            self.send_json(201, {
                "share": {
                    "token": token,
                    "itemId": item["id"],
                    "itemName": item["name"],
                    "itemType": item["type"],
                    "hasPassword": bool(password),
                    "expiresAt": expires_at,
                    "views": 0,
                    "createdAt": share_obj["createdAt"],
                }
            })
            return

        # --- API: Vaciar papelera ---
        if path == "/api/trash/empty":
            meta = load_meta()
            trashed_roots = [it["id"] for it in meta["items"] if it.get("trashed", False)]
            to_remove = set(trashed_roots)
            for tid in trashed_roots:
                to_remove.update(get_descendant_ids(meta["items"], tid))

            remaining = []
            for it in meta["items"]:
                if it["id"] in to_remove:
                    if it["type"] == "file" and it.get("diskName"):
                        p = os.path.join(FILES_DIR, it["diskName"])
                        if os.path.exists(p):
                            try:
                                os.remove(p)
                            except Exception:
                                pass
                else:
                    remaining.append(it)

            meta["items"] = remaining
            meta["shares"] = [s for s in meta["shares"] if s["itemId"] not in to_remove]
            save_meta(meta)
            self.send_json(200, {"deletedCount": len(to_remove)})
            return

        self.send_json(404, {"error": "Ruta POST no encontrada"})

    def do_PUT(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        # --- API: Guardar edición de archivo de texto / Markdown ---
        if path.startswith("/api/files/") and path.endswith("/content"):
            file_id = path.split("/")[3]
            body = self.read_json_body()
            new_content = body.get("content", "")
            meta = load_meta()
            item = next((it for it in meta["items"] if it["id"] == file_id and it["type"] == "file"), None)
            if not item:
                self.send_json(404, {"error": "Archivo no encontrado"})
                return
            disk_path = os.path.join(FILES_DIR, item.get("diskName", ""))
            encoded = new_content.encode("utf-8")
            with open(disk_path, "wb") as f:
                f.write(encoded)
            item["size"] = len(encoded)
            item["updatedAt"] = now_iso()
            save_meta(meta)
            self.send_json(200, {"item": item})
            return

        self.send_json(404, {"error": "Ruta PUT no encontrada"})

    def do_PATCH(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        # --- API: Actualizar metadatos (renombrar, mover, destacar, enviar/restaurar de papelera) ---
        if path.startswith("/api/items/"):
            item_id = path.split("/")[3]
            body = self.read_json_body()
            meta = load_meta()
            item = next((it for it in meta["items"] if it["id"] == item_id), None)
            if not item:
                self.send_json(404, {"error": "Elemento no encontrado"})
                return

            if "name" in body and str(body["name"]).strip():
                item["name"] = str(body["name"]).strip()
                if item["type"] == "file":
                    guessed = mimetypes.guess_type(item["name"])[0]
                    if guessed:
                        item["mimeType"] = guessed

            if "starred" in body:
                item["starred"] = bool(body["starred"])

            if "trashed" in body:
                trashed_val = bool(body["trashed"])
                item["trashed"] = trashed_val
                if item["type"] == "folder":
                    for desc_id in get_descendant_ids(meta["items"], item["id"]):
                        desc_item = next((x for x in meta["items"] if x["id"] == desc_id), None)
                        if desc_item:
                            desc_item["trashed"] = trashed_val

            if "parentId" in body:
                new_parent = body["parentId"]
                if new_parent in ("", "null", "root"):
                    new_parent = None
                if item["type"] == "folder" and new_parent:
                    invalid_ids = get_descendant_ids(meta["items"], item["id"])
                    invalid_ids.add(item["id"])
                    if new_parent in invalid_ids:
                        self.send_json(400, {"error": "No puedes mover una carpeta dentro de sí misma"})
                        return
                item["parentId"] = new_parent

            item["updatedAt"] = now_iso()
            save_meta(meta)
            self.send_json(200, {"item": item})
            return

        self.send_json(404, {"error": "Ruta PATCH no encontrada"})

    def do_DELETE(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        # --- API: Eliminar elemento permanentemente ---
        if path.startswith("/api/items/"):
            item_id = path.split("/")[3]
            meta = load_meta()
            item = next((it for it in meta["items"] if it["id"] == item_id), None)
            if not item:
                self.send_json(404, {"error": "Elemento no encontrado"})
                return

            to_delete = {item_id}
            if item["type"] == "folder":
                to_delete.update(get_descendant_ids(meta["items"], item_id))

            remaining = []
            for it in meta["items"]:
                if it["id"] in to_delete:
                    if it["type"] == "file" and it.get("diskName"):
                        disk_path = os.path.join(FILES_DIR, it["diskName"])
                        if os.path.exists(disk_path):
                            try:
                                os.remove(disk_path)
                            except Exception:
                                pass
                else:
                    remaining.append(it)

            meta["items"] = remaining
            meta["shares"] = [s for s in meta["shares"] if s["itemId"] not in to_delete]
            save_meta(meta)
            self.send_json(200, {"deleted": list(to_delete)})
            return

        # --- API: Revocar enlace compartido ---
        if path.startswith("/api/shares/"):
            token = path.split("/")[3]
            meta = load_meta()
            before = len(meta["shares"])
            meta["shares"] = [s for s in meta["shares"] if s["token"] != token]
            save_meta(meta)
            self.send_json(200, {"revoked": before != len(meta["shares"])})
            return

        self.send_json(404, {"error": "Ruta DELETE no encontrada"})


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    ensure_storage()
    server = ThreadingHTTPServer(("0.0.0.0", PORT), CloudRequestHandler)
    print("============================================================", flush=True)
    print(f" [Nimbus Cloud] Servidor iniciado en: http://localhost:{PORT}", flush=True)
    print(f" [Storage] Almacenamiento en disco: {FILES_DIR}", flush=True)
    print("============================================================", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nCerrando servidor...")
        server.server_close()


if __name__ == "__main__":
    main()
