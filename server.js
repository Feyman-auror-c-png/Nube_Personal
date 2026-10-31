/**
 * Servidor Local Node.js + Express para Nube Personal (Nimbus Cloud)
 * Comparte el mismo esquema de almacenamiento (./storage/metadata.json y ./storage/files) que server.py
 */

const express = require("express");
const multer = require("multer");
const path = require("path");
const fs = require("fs");
const crypto = require("crypto");

const app = express();
const PORT = process.env.PORT || 3000;

const PUBLIC_DIR = path.join(__dirname, "public");
const STORAGE_DIR = path.join(__dirname, "storage");
const FILES_DIR = path.join(STORAGE_DIR, "files");
const META_PATH = path.join(STORAGE_DIR, "metadata.json");

app.use(express.json({ limit: "50mb" }));
app.use(express.static(PUBLIC_DIR));

function ensureStorage() {
  if (!fs.existsSync(PUBLIC_DIR)) fs.mkdirSync(PUBLIC_DIR, { recursive: true });
  if (!fs.existsSync(FILES_DIR)) fs.mkdirSync(FILES_DIR, { recursive: true });
  if (!fs.existsSync(META_PATH)) {
    const initial = {
      items: [],
      shares: [],
      settings: { quotaBytes: 5 * 1024 * 1024 * 1024, pinHash: "" },
    };
    fs.writeFileSync(META_PATH, JSON.stringify(initial, null, 2), "utf8");
  }
}

function loadMeta() {
  ensureStorage();
  try {
    return JSON.parse(fs.readFileSync(META_PATH, "utf8"));
  } catch {
    return { items: [], shares: [], settings: { quotaBytes: 5 * 1024 * 1024 * 1024, pinHash: "" } };
  }
}

function saveMeta(data) {
  ensureStorage();
  fs.writeFileSync(META_PATH, JSON.stringify(data, null, 2), "utf8");
}

function hashPassword(pwd) {
  if (!pwd) return "";
  return crypto.createHash("sha256").update(pwd, "utf8").digest("hex");
}

function getDescendantIds(items, rootId) {
  const result = new Set();
  const stack = [rootId];
  while (stack.length > 0) {
    const curr = stack.pop();
    for (const it of items) {
      if (it.parentId === curr && !result.has(it.id)) {
        result.add(it.id);
        if (it.type === "folder") stack.push(it.id);
      }
    }
  }
  return result;
}

function computeFolderSize(items, folderId) {
  const desc = getDescendantIds(items, folderId);
  return items
    .filter((it) => desc.has(it.id) && it.type === "file" && !it.trashed)
    .reduce((acc, it) => acc + (it.size || 0), 0);
}

function buildBreadcrumbs(items, folderId) {
  const crumbs = [];
  const map = new Map(items.map((i) => [i.id, i]));
  const visited = new Set();
  let curr = folderId;
  while (curr && map.has(curr) && !visited.has(curr)) {
    visited.add(curr);
    const folder = map.get(curr);
    crumbs.unshift({ id: folder.id, name: folder.name });
    curr = folder.parentId;
  }
  return crumbs;
}

function isShareExpired(share) {
  if (!share.expiresAt) return false;
  return Date.now() > new Date(share.expiresAt).getTime();
}

const upload = multer({
  storage: multer.diskStorage({
    destination: (_req, _file, cb) => {
      ensureStorage();
      cb(null, FILES_DIR);
    },
    filename: (_req, file, cb) => {
      const id = crypto.randomUUID();
      const ext = path.extname(file.originalname).toLowerCase();
      file.generatedId = id;
      file.diskName = `${id}${ext}`;
      cb(null, file.diskName);
    },
  }),
});

app.get("/api/items", (req, res) => {
  const meta = loadMeta();
  const activeShareIds = new Set(
    meta.shares.filter((s) => !isShareExpired(s)).map((s) => s.itemId)
  );
  const enriched = meta.items.map((it) => {
    const copy = { ...it, isShared: activeShareIds.has(it.id) };
    if (copy.type === "folder") {
      copy.size = computeFolderSize(meta.items, copy.id);
      copy.childrenCount = meta.items.filter(
        (c) => c.parentId === copy.id && !c.trashed
      ).length;
    }
    return copy;
  });

  const parentId =
    !req.query.parentId || req.query.parentId === "null" || req.query.parentId === "root"
      ? null
      : req.query.parentId;

  const usedBytes = meta.items
    .filter((i) => i.type === "file" && !i.trashed)
    .reduce((a, b) => a + (b.size || 0), 0);
  const trashBytes = meta.items
    .filter((i) => i.type === "file" && i.trashed)
    .reduce((a, b) => a + (b.size || 0), 0);

  res.json({
    items: enriched,
    breadcrumbs: buildBreadcrumbs(meta.items, parentId),
    stats: {
      usedBytes,
      trashBytes,
      quotaBytes: meta.settings?.quotaBytes || 5 * 1024 * 1024 * 1024,
      totalFiles: meta.items.filter((i) => i.type === "file" && !i.trashed).length,
      totalFolders: meta.items.filter((i) => i.type === "folder" && !i.trashed).length,
    },
  });
});

app.post("/api/folders", (req, res) => {
  const name = (req.body.name || "").trim();
  const parentId =
    !req.body.parentId || req.body.parentId === "null" || req.body.parentId === "root"
      ? null
      : req.body.parentId;
  if (!name) return res.status(400).json({ error: "El nombre es obligatorio" });

  const meta = loadMeta();
  const now = new Date().toISOString();
  const folder = {
    id: crypto.randomUUID(),
    name,
    type: "folder",
    parentId,
    size: 0,
    mimeType: "inode/directory",
    starred: false,
    trashed: false,
    createdAt: now,
    updatedAt: now,
  };
  meta.items.push(folder);
  saveMeta(meta);
  res.status(201).json({ item: folder });
});

app.post("/api/files/text", (req, res) => {
  let name = (req.body.name || "Documento.md").trim();
  if (!name.includes(".")) name += ".md";
  const content = req.body.content || "";
  const parentId =
    !req.body.parentId || req.body.parentId === "null" || req.body.parentId === "root"
      ? null
      : req.body.parentId;

  const id = crypto.randomUUID();
  const ext = path.extname(name).toLowerCase() || ".md";
  const diskName = `${id}${ext}`;
  const buf = Buffer.from(content, "utf8");
  fs.writeFileSync(path.join(FILES_DIR, diskName), buf);

  const now = new Date().toISOString();
  const item = {
    id,
    name,
    type: "file",
    parentId,
    size: buf.length,
    mimeType: ext === ".md" ? "text/markdown" : "text/plain",
    diskName,
    starred: false,
    trashed: false,
    createdAt: now,
    updatedAt: now,
  };
  const meta = loadMeta();
  meta.items.push(item);
  saveMeta(meta);
  res.status(201).json({ item });
});

app.post("/api/upload", upload.array("files"), (req, res) => {
  const parentId =
    !req.body.parentId || req.body.parentId === "null" || req.body.parentId === "root"
      ? null
      : req.body.parentId;
  const meta = loadMeta();
  const now = new Date().toISOString();
  const created = (req.files || []).map((f) => {
    const item = {
      id: f.generatedId,
      name: Buffer.from(f.originalname, "latin1").toString("utf8"),
      type: "file",
      parentId,
      size: f.size,
      mimeType: f.mimetype || "application/octet-stream",
      diskName: f.diskName,
      starred: false,
      trashed: false,
      createdAt: now,
      updatedAt: now,
    };
    meta.items.push(item);
    return item;
  });
  saveMeta(meta);
  res.status(201).json({ items: created });
});

app.get("/api/files/:id/content", (req, res) => {
  const meta = loadMeta();
  const item = meta.items.find((i) => i.id === req.params.id && i.type === "file");
  if (!item) return res.status(404).json({ error: "Archivo no encontrado" });
  const diskPath = path.join(FILES_DIR, item.diskName);
  if (!fs.existsSync(diskPath)) return res.status(404).json({ error: "No existe en disco" });
  const content = fs.readFileSync(diskPath, "utf8");
  res.json({ id: item.id, name: item.name, content, updatedAt: item.updatedAt });
});

app.put("/api/files/:id/content", (req, res) => {
  const meta = loadMeta();
  const item = meta.items.find((i) => i.id === req.params.id && i.type === "file");
  if (!item) return res.status(404).json({ error: "Archivo no encontrado" });
  const buf = Buffer.from(req.body.content || "", "utf8");
  fs.writeFileSync(path.join(FILES_DIR, item.diskName), buf);
  item.size = buf.length;
  item.updatedAt = new Date().toISOString();
  saveMeta(meta);
  res.json({ item });
});

app.get("/api/files/:id/preview", (req, res) => {
  const meta = loadMeta();
  const item = meta.items.find((i) => i.id === req.params.id && i.type === "file");
  if (!item) return res.status(404).json({ error: "Archivo no encontrado" });
  res.sendFile(path.join(FILES_DIR, item.diskName));
});

app.get("/api/files/:id/download", (req, res) => {
  const meta = loadMeta();
  const item = meta.items.find((i) => i.id === req.params.id && i.type === "file");
  if (!item) return res.status(404).json({ error: "Archivo no encontrado" });
  res.download(path.join(FILES_DIR, item.diskName), item.name);
});

app.patch("/api/items/:id", (req, res) => {
  const meta = loadMeta();
  const item = meta.items.find((i) => i.id === req.params.id);
  if (!item) return res.status(404).json({ error: "Elemento no encontrado" });

  if (typeof req.body.name === "string" && req.body.name.trim()) {
    item.name = req.body.name.trim();
  }
  if (typeof req.body.starred === "boolean") {
    item.starred = req.body.starred;
  }
  if (typeof req.body.trashed === "boolean") {
    item.trashed = req.body.trashed;
    if (item.type === "folder") {
      const desc = getDescendantIds(meta.items, item.id);
      meta.items.forEach((x) => {
        if (desc.has(x.id)) x.trashed = req.body.trashed;
      });
    }
  }
  if ("parentId" in req.body) {
    item.parentId =
      !req.body.parentId || req.body.parentId === "null" || req.body.parentId === "root"
        ? null
        : req.body.parentId;
  }
  item.updatedAt = new Date().toISOString();
  saveMeta(meta);
  res.json({ item });
});

app.delete("/api/items/:id", (req, res) => {
  const meta = loadMeta();
  const item = meta.items.find((i) => i.id === req.params.id);
  if (!item) return res.status(404).json({ error: "Elemento no encontrado" });

  const toDelete = new Set([item.id]);
  if (item.type === "folder") {
    for (const d of getDescendantIds(meta.items, item.id)) toDelete.add(d);
  }
  meta.items.forEach((it) => {
    if (toDelete.has(it.id) && it.type === "file" && it.diskName) {
      const p = path.join(FILES_DIR, it.diskName);
      if (fs.existsSync(p)) fs.unlinkSync(p);
    }
  });
  meta.items = meta.items.filter((it) => !toDelete.has(it.id));
  meta.shares = meta.shares.filter((s) => !toDelete.has(s.itemId));
  saveMeta(meta);
  res.json({ deleted: Array.from(toDelete) });
});

app.get("/api/shares", (_req, res) => {
  const meta = loadMeta();
  const map = new Map(meta.items.map((i) => [i.id, i]));
  const shares = meta.shares
    .filter((s) => map.has(s.itemId) && !map.get(s.itemId).trashed)
    .map((s) => {
      const it = map.get(s.itemId);
      return {
        token: s.token,
        itemId: s.itemId,
        itemName: it.name,
        itemType: it.type,
        mimeType: it.mimeType,
        size: it.type === "folder" ? computeFolderSize(meta.items, it.id) : it.size,
        hasPassword: Boolean(s.passwordHash),
        expiresAt: s.expiresAt,
        expired: isShareExpired(s),
        views: s.views || 0,
        createdAt: s.createdAt,
      };
    });
  res.json({ shares });
});

app.post("/api/shares", (req, res) => {
  const meta = loadMeta();
  const item = meta.items.find((i) => i.id === req.body.itemId && !i.trashed);
  if (!item) return res.status(404).json({ error: "Elemento no encontrado" });
  const token = crypto.randomBytes(6).toString("hex");
  const hours = Number(req.body.expiresInHours || 0);
  const expiresAt = hours > 0 ? new Date(Date.now() + hours * 3600 * 1000).toISOString() : null;
  const share = {
    token,
    itemId: item.id,
    passwordHash: req.body.password ? hashPassword(req.body.password.trim()) : "",
    expiresAt,
    views: 0,
    createdAt: new Date().toISOString(),
  };
  meta.shares.push(share);
  saveMeta(meta);
  res.status(201).json({
    share: {
      token,
      itemId: item.id,
      itemName: item.name,
      itemType: item.type,
      hasPassword: Boolean(share.passwordHash),
      expiresAt,
      views: 0,
      createdAt: share.createdAt,
    },
  });
});

app.delete("/api/shares/:token", (req, res) => {
  const meta = loadMeta();
  meta.shares = meta.shares.filter((s) => s.token !== req.params.token);
  saveMeta(meta);
  res.json({ revoked: true });
});

app.listen(PORT, () => {
  ensureStorage();
  console.log(`☁️  Nimbus Personal Cloud iniciada en http://localhost:${PORT}`);
});
