#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Servidor Local Multiusuario para Nube Personal (Nimbus Cloud v1.2.0)
Incluye: Autenticación (Login/Registro), Espacio privado por usuario,
Compartir interno entre usuarios (Solo lectura / Edición) y Enlaces públicos (?share=TOKEN).
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

AVATAR_COLORS = ["#38bdf8", "#6366f1", "#10b981", "#f59e0b", "#ec4899", "#8b5cf6", "#14b8a6"]

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
    else:
        migrate_multiuser_if_needed()


def migrate_multiuser_if_needed():
    """Garantiza que metadata.json tenga usuarios por defecto y que los archivos previos pertenezcan a admin."""
    try:
        with open(META_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        seed_initial_data()
        return

    changed = False
    if "users" not in data or not data["users"]:
        created = now_iso()
        admin_id = str(uuid.uuid4())
        guest_id = str(uuid.uuid4())
        data["users"] = [
            {
                "id": admin_id,
                "username": "admin",
                "displayName": "Administrador Principal",
                "passwordHash": hash_password("admin123"),
                "role": "admin",
                "avatarColor": "#38bdf8",
                "quotaBytes": 5 * 1024 * 1024 * 1024,
                "createdAt": created,
            },
            {
                "id": guest_id,
                "username": "invitado",
                "displayName": "Usuario Invitado",
                "passwordHash": hash_password("123456"),
                "role": "user",
                "avatarColor": "#10b981",
                "quotaBytes": 2 * 1024 * 1024 * 1024,
                "createdAt": created,
            },
        ]
        changed = True

    admin_user_id = data["users"][0]["id"]

    if "sessions" not in data:
        data["sessions"] = {}
        changed = True

    for it in data.get("items", []):
        if not it.get("ownerId"):
            it["ownerId"] = admin_user_id
            changed = True
        if "sharedWith" not in it:
            it["sharedWith"] = []
            changed = True

    for s in data.get("shares", []):
        if not s.get("ownerId"):
            s["ownerId"] = admin_user_id
            changed = True

    if changed:
        save_meta(data)


def load_meta():
    ensure_storage()
    try:
        with open(META_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
            if "items" not in data:
                data["items"] = []
            if "shares" not in data:
                data["shares"] = []
            if "users" not in data:
                data["users"] = []
            if "sessions" not in data:
                data["sessions"] = {}
            return data
    except Exception:
        return {"items": [], "shares": [], "users": [], "sessions": {}}


def save_meta(data):
    os.makedirs(STORAGE_DIR, exist_ok=True)
    temp_path = META_PATH + ".tmp"
    with open(temp_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(temp_path, META_PATH)


def seed_user_welcome_files(meta, user_id, display_name):
    """Crea una nota de bienvenida en el espacio personal de un nuevo usuario registrado."""
    created = now_iso()
    welcome_id = str(uuid.uuid4())
    disk_name = f"{welcome_id}.md"
    content = f"""# 👋 ¡Hola, {display_name}! Bienvenido a tu espacio en Nimbus Cloud

Este es tu **espacio personal privado** en la nube.

## ✨ ¿Qué puedes hacer aquí?
- 📁 **Subir archivos y carpetas completas**: Arrastra carpetas desde tu PC o usa el botón **📁⬆️ Subir Carpeta**.
- 📝 **Crear y editar notas `.md` en vivo**: Usa el modo **⚡ Vista Dividida** para editar con vista previa instantánea.
- 👥 **Compartir con otros usuarios**: Haz clic en **🔗 Compartir** sobre cualquier archivo o carpeta para darle acceso de **Solo lectura** o **Edición** a otro usuario de la nube, o crear un enlace público.
"""
    encoded = content.encode("utf-8")
    with open(os.path.join(FILES_DIR, disk_name), "wb") as f:
        f.write(encoded)

    meta["items"].append({
        "id": welcome_id,
        "ownerId": user_id,
        "name": f"Bienvenida de {display_name}.md",
        "type": "file",
        "parentId": None,
        "size": len(encoded),
        "mimeType": "text/markdown",
        "diskName": disk_name,
        "starred": True,
        "trashed": False,
        "sharedWith": [],
        "createdAt": created,
        "updatedAt": created,
    })


def seed_initial_data():
    """Inicializa usuarios y archivos de demostración."""
    os.makedirs(FILES_DIR, exist_ok=True)
    created = now_iso()
    admin_id = str(uuid.uuid4())
    guest_id = str(uuid.uuid4())

    users = [
        {
            "id": admin_id,
            "username": "admin",
            "displayName": "Administrador Principal",
            "passwordHash": hash_password("admin123"),
            "role": "admin",
            "avatarColor": "#38bdf8",
            "quotaBytes": 5 * 1024 * 1024 * 1024,
            "createdAt": created,
        },
        {
            "id": guest_id,
            "username": "invitado",
            "displayName": "Usuario Invitado",
            "passwordHash": hash_password("123456"),
            "role": "user",
            "avatarColor": "#10b981",
            "quotaBytes": 2 * 1024 * 1024 * 1024,
            "createdAt": created,
        },
    ]

    meta = {"users": users, "sessions": {}, "items": [], "shares": []}
    seed_user_welcome_files(meta, admin_id, "Administrador")
    seed_user_welcome_files(meta, guest_id, "Invitado")
    save_meta(meta)


def get_descendant_ids(items, root_id):
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


def get_effective_share_permission(items, item, user_id):
    """Verifica si el usuario tiene acceso directo o heredado de una carpeta padre compartida."""
    if item.get("ownerId") == user_id:
        return "owner"
    item_map = {it["id"]: it for it in items}
    curr = item
    visited = set()
    while curr and curr["id"] not in visited:
        visited.add(curr["id"])
        for entry in curr.get("sharedWith", []):
            if entry.get("userId") == user_id:
                return entry.get("permission", "view")
        parent_id = curr.get("parentId")
        curr = item_map.get(parent_id) if parent_id else None
    return None


def ensure_folder_path(meta, owner_id, root_parent_id, folder_parts, now_str, folder_cache):
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
                and it.get("ownerId") == owner_id
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
                "ownerId": owner_id,
                "name": clean_part,
                "type": "folder",
                "parentId": curr_parent,
                "size": 0,
                "mimeType": "inode/directory",
                "starred": False,
                "trashed": False,
                "sharedWith": [],
                "createdAt": now_str,
                "updatedAt": now_str,
            }
            meta["items"].append(new_folder)
            created_folders.append(new_folder)
            curr_parent = new_folder["id"]
            folder_cache[cache_key] = curr_parent
    return curr_parent, created_folders


def parse_multipart_form_data(headers, body: bytes):
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


def sanitize_user(u):
    return {
        "id": u["id"],
        "username": u["username"],
        "displayName": u.get("displayName") or u["username"],
        "role": u.get("role", "user"),
        "avatarColor": u.get("avatarColor", "#38bdf8"),
        "quotaBytes": u.get("quotaBytes", 5 * 1024 * 1024 * 1024),
        "createdAt": u.get("createdAt"),
    }


class CloudRequestHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, fmt, *args):
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

    def get_current_user(self, meta, query=None):
        auth_header = self.headers.get("Authorization", "")
        token = ""
        if auth_header.startswith("Bearer "):
            token = auth_header[7:].strip()
        elif query and "token" in query:
            token = query["token"][0]
        if not token:
            return None, ""
        user_id = meta.get("sessions", {}).get(token)
        if not user_id:
            return None, ""
        user = next((u for u in meta.get("users", []) if u["id"] == user_id), None)
        return user, token

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

        # --- API: Sesión actual ---
        if path == "/api/auth/me":
            meta = load_meta()
            user, _ = self.get_current_user(meta, query)
            if not user:
                self.send_json(401, {"error": "No autenticado"})
                return
            self.send_json(200, {"user": sanitize_user(user)})
            return

        # --- API: Directorio de usuarios (para compartir y panel admin) ---
        if path == "/api/users":
            meta = load_meta()
            user, _ = self.get_current_user(meta, query)
            if not user:
                self.send_json(401, {"error": "No autenticado"})
                return
            out_users = []
            for u in meta["users"]:
                u_info = sanitize_user(u)
                u_info["usedBytes"] = sum(
                    it.get("size", 0)
                    for it in meta["items"]
                    if it.get("ownerId") == u["id"] and it["type"] == "file" and not it.get("trashed", False)
                )
                u_info["filesCount"] = sum(
                    1
                    for it in meta["items"]
                    if it.get("ownerId") == u["id"] and it["type"] == "file" and not it.get("trashed", False)
                )
                out_users.append(u_info)
            self.send_json(200, {"users": out_users})
            return

        # --- API: Listar elementos del usuario y elementos compartidos con él ---
        if path == "/api/items":
            meta = load_meta()
            user, _ = self.get_current_user(meta, query)
            if not user:
                self.send_json(401, {"error": "No autenticado"})
                return

            uid = user["id"]
            items = meta["items"]
            shares = meta["shares"]
            user_map = {u["id"]: u for u in meta["users"]}
            active_share_ids = {s["itemId"] for s in shares if not is_share_expired(s)}

            own_items = []
            shared_with_me = []

            for it in items:
                perm = get_effective_share_permission(items, it, uid)
                if not perm:
                    continue
                copy_it = dict(it)
                owner_obj = user_map.get(copy_it.get("ownerId"), {})
                copy_it["ownerUsername"] = owner_obj.get("username", "admin")
                copy_it["ownerDisplayName"] = owner_obj.get("displayName", "Administrador")
                copy_it["myPermission"] = perm
                if copy_it["type"] == "folder":
                    copy_it["size"] = compute_folder_size(items, copy_it["id"])
                    copy_it["childrenCount"] = sum(
                        1
                        for c in items
                        if c.get("parentId") == copy_it["id"] and not c.get("trashed", False)
                    )
                copy_it["isShared"] = (
                    copy_it["id"] in active_share_ids or len(copy_it.get("sharedWith", [])) > 0
                )

                if perm == "owner":
                    own_items.append(copy_it)
                elif not copy_it.get("trashed", False):
                    shared_with_me.append(copy_it)

            parent_id = query.get("parentId", [None])[0]
            if parent_id in ("", "null", "root"):
                parent_id = None

            total_used = sum(
                it.get("size", 0)
                for it in own_items
                if it["type"] == "file" and not it.get("trashed", False)
            )
            trash_used = sum(
                it.get("size", 0)
                for it in own_items
                if it["type"] == "file" and it.get("trashed", False)
            )

            self.send_json(200, {
                "items": own_items,
                "sharedWithMe": shared_with_me,
                "breadcrumbs": build_breadcrumbs(items, parent_id),
                "stats": {
                    "usedBytes": total_used,
                    "trashBytes": trash_used,
                    "quotaBytes": user.get("quotaBytes", 5 * 1024 * 1024 * 1024),
                    "totalFiles": sum(1 for it in own_items if it["type"] == "file" and not it.get("trashed", False)),
                    "totalFolders": sum(1 for it in own_items if it["type"] == "folder" and not it.get("trashed", False)),
                },
            })
            return

        # --- API: Obtener contenido de texto / Markdown o preview ---
        if path.startswith("/api/files/") and path.endswith("/content"):
            file_id = path.split("/")[3]
            meta = load_meta()
            user, _ = self.get_current_user(meta, query)
            if not user:
                self.send_json(401, {"error": "No autenticado"})
                return
            item = next((it for it in meta["items"] if it["id"] == file_id and it["type"] == "file"), None)
            if not item or not get_effective_share_permission(meta["items"], item, user["id"]):
                self.send_json(404, {"error": "Archivo no encontrado o sin acceso"})
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
            self.send_json(200, {
                "id": item["id"],
                "name": item["name"],
                "content": text,
                "updatedAt": item["updatedAt"],
                "myPermission": get_effective_share_permission(meta["items"], item, user["id"]),
            })
            return

        if path.startswith("/api/files/") and path.endswith("/preview"):
            file_id = path.split("/")[3]
            meta = load_meta()
            user, _ = self.get_current_user(meta, query)
            if not user:
                self.send_json(401, {"error": "No autenticado"})
                return
            item = next((it for it in meta["items"] if it["id"] == file_id and it["type"] == "file"), None)
            if not item or not get_effective_share_permission(meta["items"], item, user["id"]):
                self.send_json(404, {"error": "Archivo no encontrado"})
                return
            disk_path = os.path.join(FILES_DIR, item.get("diskName", ""))
            mime = item.get("mimeType") or mimetypes.guess_type(item["name"])[0] or "application/octet-stream"
            self.serve_file_bytes(disk_path, mime, download_name=None)
            return

        if path.startswith("/api/files/") and path.endswith("/download"):
            file_id = path.split("/")[3]
            meta = load_meta()
            user, _ = self.get_current_user(meta, query)
            if not user:
                self.send_json(401, {"error": "No autenticado"})
                return
            item = next((it for it in meta["items"] if it["id"] == file_id and it["type"] == "file"), None)
            if not item or not get_effective_share_permission(meta["items"], item, user["id"]):
                self.send_json(404, {"error": "Archivo no encontrado"})
                return
            disk_path = os.path.join(FILES_DIR, item.get("diskName", ""))
            mime = item.get("mimeType") or mimetypes.guess_type(item["name"])[0] or "application/octet-stream"
            self.serve_file_bytes(disk_path, mime, download_name=item["name"])
            return

        if path.startswith("/api/folders/") and path.endswith("/zip"):
            folder_id = path.split("/")[3]
            meta = load_meta()
            user, _ = self.get_current_user(meta, query)
            if not user:
                self.send_json(401, {"error": "No autenticado"})
                return
            folder = next((it for it in meta["items"] if it["id"] == folder_id and it["type"] == "folder"), None)
            if not folder or not get_effective_share_permission(meta["items"], folder, user["id"]):
                self.send_json(404, {"error": "Carpeta no encontrada"})
                return
            self.serve_folder_zip(meta, folder)
            return

        # --- API: Listar enlaces públicos del usuario actual ---
        if path == "/api/shares":
            meta = load_meta()
            user, _ = self.get_current_user(meta, query)
            if not user:
                self.send_json(401, {"error": "No autenticado"})
                return
            item_map = {it["id"]: it for it in meta["items"]}
            result = []
            for s in meta["shares"]:
                it = item_map.get(s["itemId"])
                if not it or it.get("trashed", False) or it.get("ownerId") != user["id"]:
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

        # --- API: Vista pública de enlace compartido (sin requerir login) ---
        if path.startswith("/api/public/"):
            parts = path.strip("/").split("/")
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
        query = urllib.parse.parse_qs(parsed.query)

        # --- API: Iniciar sesión ---
        if path == "/api/auth/login":
            body = self.read_json_body()
            username = (body.get("username") or "").strip().lower()
            password = body.get("password") or ""
            meta = load_meta()
            user = next((u for u in meta["users"] if u["username"].lower() == username), None)
            if not user or user.get("passwordHash") != hash_password(password):
                self.send_json(401, {"error": "Usuario o contraseña incorrectos"})
                return
            token = uuid.uuid4().hex
            meta["sessions"][token] = user["id"]
            save_meta(meta)
            self.send_json(200, {"token": token, "user": sanitize_user(user)})
            return

        # --- API: Registrar nuevo usuario ---
        if path == "/api/auth/register":
            body = self.read_json_body()
            username = (body.get("username") or "").strip().lower()
            display_name = (body.get("displayName") or username).strip()
            password = body.get("password") or ""

            if len(username) < 3 or " " in username:
                self.send_json(400, {"error": "El nombre de usuario debe tener al menos 3 caracteres y sin espacios"})
                return
            if len(password) < 4:
                self.send_json(400, {"error": "La contraseña debe tener al menos 4 caracteres"})
                return

            meta = load_meta()
            if any(u["username"].lower() == username for u in meta["users"]):
                self.send_json(409, {"error": "Ese nombre de usuario ya está registrado"})
                return

            new_user_id = str(uuid.uuid4())
            color = AVATAR_COLORS[len(meta["users"]) % len(AVATAR_COLORS)]
            new_user = {
                "id": new_user_id,
                "username": username,
                "displayName": display_name,
                "passwordHash": hash_password(password),
                "role": "user",
                "avatarColor": color,
                "quotaBytes": 5 * 1024 * 1024 * 1024,
                "createdAt": now_iso(),
            }
            meta["users"].append(new_user)
            seed_user_welcome_files(meta, new_user_id, display_name)

            token = uuid.uuid4().hex
            meta["sessions"][token] = new_user_id
            save_meta(meta)
            self.send_json(201, {"token": token, "user": sanitize_user(new_user)})
            return

        # --- API: Cerrar sesión ---
        if path == "/api/auth/logout":
            meta = load_meta()
            _, token = self.get_current_user(meta, query)
            if token and token in meta.get("sessions", {}):
                del meta["sessions"][token]
                save_meta(meta)
            self.send_json(200, {"loggedOut": True})
            return

        # Todas las rutas siguientes requieren usuario autenticado
        meta = load_meta()
        user, _ = self.get_current_user(meta, query)
        if not user:
            self.send_json(401, {"error": "Sesión expirada o no autenticada"})
            return

        # --- API: Compartir internamente con otro usuario ---
        if path.startswith("/api/items/") and path.endswith("/share-user"):
            item_id = path.split("/")[3]
            body = self.read_json_body()
            target_user_id = body.get("targetUserId")
            permission = body.get("permission", "view")
            if permission not in ("view", "edit"):
                permission = "view"

            item = next((it for it in meta["items"] if it["id"] == item_id and it.get("ownerId") == user["id"]), None)
            if not item:
                self.send_json(404, {"error": "Solo el propietario puede administrar los permisos de este elemento"})
                return

            target_user = next((u for u in meta["users"] if u["id"] == target_user_id), None)
            if not target_user or target_user["id"] == user["id"]:
                self.send_json(400, {"error": "Selecciona un usuario válido distinto al tuyo"})
                return

            if "sharedWith" not in item:
                item["sharedWith"] = []

            existing_entry = next((e for e in item["sharedWith"] if e["userId"] == target_user["id"]), None)
            if existing_entry:
                existing_entry["permission"] = permission
                existing_entry["sharedAt"] = now_iso()
            else:
                item["sharedWith"].append({
                    "userId": target_user["id"],
                    "username": target_user["username"],
                    "displayName": target_user.get("displayName", target_user["username"]),
                    "permission": permission,
                    "sharedAt": now_iso(),
                })

            save_meta(meta)
            self.send_json(200, {"item": item})
            return

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

            now = now_iso()
            new_folder = {
                "id": str(uuid.uuid4()),
                "ownerId": user["id"],
                "name": name,
                "type": "folder",
                "parentId": parent_id,
                "size": 0,
                "mimeType": "inode/directory",
                "starred": False,
                "trashed": False,
                "sharedWith": [],
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
            new_item = {
                "id": file_id,
                "ownerId": user["id"],
                "name": name,
                "type": "file",
                "parentId": parent_id,
                "size": len(encoded),
                "mimeType": mime,
                "diskName": disk_name,
                "starred": False,
                "trashed": False,
                "sharedWith": [],
                "createdAt": now,
                "updatedAt": now,
            }
            meta["items"].append(new_item)
            save_meta(meta)
            self.send_json(201, {"item": new_item})
            return

        # --- API: Subir uno o varios archivos o carpetas completas ---
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

            now = now_iso()
            created_items = []
            folder_cache = {}

            for ef_path in empty_folders:
                norm_ef = str(ef_path).replace("\\", "/").strip("/")
                parts = [p for p in norm_ef.split("/") if p and p != "."]
                if parts:
                    _, new_f = ensure_folder_path(meta, user["id"], parent_id, parts, now, folder_cache)
                    created_items.extend(new_f)

            for idx, uf in enumerate(uploaded_files):
                rel_p = rel_paths[idx] if idx < len(rel_paths) and rel_paths[idx] else (uf["filename"] or "archivo")
                norm_rel = str(rel_p).replace("\\", "/").strip("/")
                parts = [p for p in norm_rel.split("/") if p and p != "."]

                if len(parts) > 1:
                    folder_parts = parts[:-1]
                    orig_name = parts[-1]
                    target_parent_id, new_f = ensure_folder_path(meta, user["id"], parent_id, folder_parts, now, folder_cache)
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
                    "ownerId": user["id"],
                    "name": orig_name,
                    "type": "file",
                    "parentId": target_parent_id,
                    "size": len(uf["data"]),
                    "mimeType": mime,
                    "diskName": disk_name,
                    "starred": False,
                    "trashed": False,
                    "sharedWith": [],
                    "createdAt": now,
                    "updatedAt": now,
                }
                meta["items"].append(item)
                created_items.append(item)

            save_meta(meta)
            self.send_json(201, {"items": created_items})
            return

        # --- API: Crear enlace público compartido ---
        if path == "/api/shares":
            body = self.read_json_body()
            item_id = body.get("itemId")
            password = (body.get("password") or "").strip()
            expires_in_hours = body.get("expiresInHours")

            item = next(
                (it for it in meta["items"] if it["id"] == item_id and it.get("ownerId") == user["id"] and not it.get("trashed", False)),
                None,
            )
            if not item:
                self.send_json(404, {"error": "El archivo o carpeta no existe en tu unidad"})
                return

            expires_at = None
            if expires_in_hours and float(expires_in_hours) > 0:
                exp_ts = time.time() + float(expires_in_hours) * 3600
                expires_at = datetime.fromtimestamp(exp_ts, tz=timezone.utc).isoformat()

            token = uuid.uuid4().hex[:12]
            share_obj = {
                "token": token,
                "ownerId": user["id"],
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

        # --- API: Vaciar papelera del usuario actual ---
        if path == "/api/trash/empty":
            trashed_roots = [
                it["id"] for it in meta["items"]
                if it.get("ownerId") == user["id"] and it.get("trashed", False)
            ]
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
        query = urllib.parse.parse_qs(parsed.query)

        meta = load_meta()
        user, _ = self.get_current_user(meta, query)
        if not user:
            self.send_json(401, {"error": "No autenticado"})
            return

        # --- API: Guardar edición de archivo de texto / Markdown (Propietario o Permiso Edit) ---
        if path.startswith("/api/files/") and path.endswith("/content"):
            file_id = path.split("/")[3]
            body = self.read_json_body()
            new_content = body.get("content", "")
            item = next((it for it in meta["items"] if it["id"] == file_id and it["type"] == "file"), None)
            if not item:
                self.send_json(404, {"error": "Archivo no encontrado"})
                return
            perm = get_effective_share_permission(meta["items"], item, user["id"])
            if perm not in ("owner", "edit"):
                self.send_json(403, {"error": "Solo tienes permiso de lectura en este archivo"})
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
        query = urllib.parse.parse_qs(parsed.query)

        meta = load_meta()
        user, _ = self.get_current_user(meta, query)
        if not user:
            self.send_json(401, {"error": "No autenticado"})
            return

        if path.startswith("/api/items/"):
            item_id = path.split("/")[3]
            body = self.read_json_body()
            item = next((it for it in meta["items"] if it["id"] == item_id), None)
            if not item:
                self.send_json(404, {"error": "Elemento no encontrado"})
                return

            perm = get_effective_share_permission(meta["items"], item, user["id"])
            if perm not in ("owner", "edit"):
                self.send_json(403, {"error": "No tienes permisos para modificar este elemento"})
                return

            if "name" in body and str(body["name"]).strip():
                item["name"] = str(body["name"]).strip()
                if item["type"] == "file":
                    guessed = mimetypes.guess_type(item["name"])[0]
                    if guessed:
                        item["mimeType"] = guessed

            if "starred" in body and perm == "owner":
                item["starred"] = bool(body["starred"])

            if "trashed" in body and perm == "owner":
                trashed_val = bool(body["trashed"])
                item["trashed"] = trashed_val
                if item["type"] == "folder":
                    for desc_id in get_descendant_ids(meta["items"], item["id"]):
                        desc_item = next((x for x in meta["items"] if x["id"] == desc_id), None)
                        if desc_item:
                            desc_item["trashed"] = trashed_val

            if "parentId" in body and perm == "owner":
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
        query = urllib.parse.parse_qs(parsed.query)

        meta = load_meta()
        user, _ = self.get_current_user(meta, query)
        if not user:
            self.send_json(401, {"error": "No autenticado"})
            return

        # --- API: Quitar acceso compartido a un usuario ---
        if path.startswith("/api/items/") and "/share-user/" in path:
            parts = path.strip("/").split("/")
            item_id = parts[2]
            target_uid = parts[4]
            item = next((it for it in meta["items"] if it["id"] == item_id and it.get("ownerId") == user["id"]), None)
            if not item:
                self.send_json(404, {"error": "Elemento no encontrado"})
                return
            item["sharedWith"] = [e for e in item.get("sharedWith", []) if e.get("userId") != target_uid]
            save_meta(meta)
            self.send_json(200, {"item": item})
            return

        # --- API: Eliminar elemento permanentemente ---
        if path.startswith("/api/items/"):
            item_id = path.split("/")[3]
            item = next((it for it in meta["items"] if it["id"] == item_id and it.get("ownerId") == user["id"]), None)
            if not item:
                self.send_json(404, {"error": "Elemento no encontrado o no eres el propietario"})
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
            before = len(meta["shares"])
            meta["shares"] = [
                s for s in meta["shares"]
                if not (s["token"] == token and s.get("ownerId") == user["id"])
            ]
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
    print(f" [Nimbus Cloud v1.2.0] Servidor Multiusuario en: http://localhost:{PORT}", flush=True)
    print(f" [Storage] Almacenamiento en disco: {FILES_DIR}", flush=True)
    print("============================================================", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nCerrando servidor...")
        server.server_close()


if __name__ == "__main__":
    main()
