/**
 * Nimbus Cloud — Cliente Web Completo para Nube Personal
 * Incluye: Explorador de carpetas, Drag & Drop, Estudio Markdown (.md) con edición en vivo,
 * Previsualizador Multimedia/PDF/CSV/Código y Sistema de Enlaces Compartidos.
 */

const state = {
  items: [],
  shares: [],
  breadcrumbs: [],
  stats: { usedBytes: 0, trashBytes: 0, quotaBytes: 5 * 1024 * 1024 * 1024, totalFiles: 0, totalFolders: 0 },
  currentSection: "drive", // drive | recent | starred | markdown | shares | trash
  currentFolderId: null,
  searchQuery: "",
  typeFilter: "all", // all | md | image | media | code | doc
  sortBy: "date-desc",
  viewMode: localStorage.getItem("nimbus_view") || "grid",
  theme: localStorage.getItem("nimbus_theme") || "dark",
  activePreviewItem: null,
  activePreviewMode: "read", // read | split | edit
  activeEditorContent: "",
  imgZoom: 1,
  imgRotation: 0,
};

// ============================================================================
// UTILIDADES DE FORMATO Y CLASIFICACIÓN DE ARCHIVOS
// ============================================================================

function formatBytes(bytes) {
  if (!bytes || bytes === 0) return "0 B";
  const units = ["B", "KB", "MB", "GB", "TB"];
  const i = Math.floor(Math.log(bytes) / Math.log(1024));
  const val = bytes / Math.pow(1024, i);
  return `${val.toFixed(i === 0 ? 0 : 1)} ${units[i]}`;
}

function formatDate(isoStr) {
  if (!isoStr) return "—";
  try {
    const d = new Date(isoStr);
    return d.toLocaleDateString("es-ES", {
      day: "2-digit",
      month: "short",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return isoStr;
  }
}

function getExt(name = "") {
  const idx = name.lastIndexOf(".");
  return idx !== -1 ? name.slice(idx + 1).toLowerCase() : "";
}

function getFileCategory(item) {
  if (item.type === "folder") return "folder";
  const ext = getExt(item.name);
  const mime = (item.mimeType || "").toLowerCase();

  if (ext === "md" || ext === "markdown") return "md";
  if (["png", "jpg", "jpeg", "gif", "webp", "svg", "bmp", "ico"].includes(ext) || mime.startsWith("image/")) {
    return "image";
  }
  if (["mp4", "webm", "ogg", "mov", "mkv"].includes(ext) || mime.startsWith("video/")) {
    return "video";
  }
  if (["mp3", "wav", "flac", "m4a", "aac"].includes(ext) || mime.startsWith("audio/")) {
    return "audio";
  }
  if (ext === "pdf" || mime === "application/pdf") return "pdf";
  if (ext === "csv") return "csv";
  if (
    [
      "js", "ts", "jsx", "tsx", "py", "html", "css", "json", "xml",
      "yaml", "yml", "sh", "bat", "ps1", "sql", "c", "cpp", "java", "go", "rs", "txt", "ini", "env"
    ].includes(ext)
  ) {
    return "code";
  }
  return "doc";
}

function getFileIcon(item) {
  const cat = getFileCategory(item);
  switch (cat) {
    case "folder": return "📁";
    case "md": return "📝";
    case "image": return "🖼️";
    case "video": return "🎬";
    case "audio": return "🎵";
    case "pdf": return "📕";
    case "csv": return "📊";
    case "code": return "💻";
    default: return "📄";
  }
}

function escapeHtml(str = "") {
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function showToast(message, icon = "✨") {
  const container = document.getElementById("toast-container");
  const el = document.createElement("div");
  el.className = "toast";
  el.innerHTML = `<span>${icon}</span><span>${escapeHtml(message)}</span>`;
  container.appendChild(el);
  setTimeout(() => {
    el.style.opacity = "0";
    el.style. transition = "opacity 0.25s";
    setTimeout(() => el.remove(), 260);
  }, 3200);
}

// ============================================================================
// MOTOR DE RENDERIZADO MARKDOWN (.MD) INTEGRADO (SOPORTA TABLAS, TAREAS, CÓDIGO)
// ============================================================================

function renderMarkdown(mdText = "") {
  if (!mdText) return "<p class='preview-meta'>Documento vacío.</p>";

  const codeBlocks = [];
  let text = mdText.replace(/\r\n/g, "\n");

  // 1. Extraer bloques de código cercados ```lang ... ```
  text = text.replace(/```([a-zA-Z0-9_-]*)\n([\s\S]*?)```/g, (_match, lang, code) => {
    const idx = codeBlocks.length;
    const langLabel = lang ? `<div style="font-size:0.74rem;color:#94a3b8;margin-bottom:6px;font-family:sans-serif;text-transform:uppercase;letter-spacing:0.05em">${escapeHtml(lang)}</div>` : "";
    codeBlocks.push(`<pre>${langLabel}<code>${escapeHtml(code.replace(/\n$/, ""))}</code></pre>`);
    return `\n@@CODEBLOCK_${idx}@@\n`;
  });

  const lines = text.split("\n");
  const out = [];
  let inList = null; // 'ul' | 'ol'
  let inTable = false;
  let tableRows = [];

  function flushList() {
    if (inList) {
      out.push(`</${inList}>`);
      inList = null;
    }
  }

  function flushTable() {
    if (!inTable) return;
    inTable = false;
    if (tableRows.length === 0) return;
    const headerCells = tableRows[0];
    const bodyRows = tableRows.slice(2); // saltar fila separadora |---|---|
    let html = "<table><thead><tr>";
    for (const c of headerCells) {
      html += `<th>${parseInlineMarkdown(c.trim())}</th>`;
    }
    html += "</tr></thead><tbody>";
    for (const row of bodyRows) {
      html += "<tr>";
      for (const c of row) {
        html += `<td>${parseInlineMarkdown(c.trim())}</td>`;
      }
      html += "</tr>";
    }
    html += "</tbody></table>";
    out.push(html);
    tableRows = [];
  }

  for (let i = 0; i < lines.length; i++) {
    const rawLine = lines[i];
    const trimmed = rawLine.trim();

    // Marcador de bloque de código
    const codeMatch = trimmed.match(/^@@CODEBLOCK_(\d+)@@$/);
    if (codeMatch) {
      flushList();
      flushTable();
      out.push(codeBlocks[Number(codeMatch[1])]);
      continue;
    }

    // Detectar tablas GFM | col1 | col2 |
    if (trimmed.startsWith("|") && trimmed.endsWith("|") && trimmed.length > 2) {
      flushList();
      inTable = true;
      const cells = trimmed
        .slice(1, -1)
        .split("|");
      tableRows.push(cells);
      continue;
    } else if (inTable) {
      flushTable();
    }

    if (!trimmed) {
      flushList();
      continue;
    }

    // Línea horizontal
    if (/^(-{3,}|\*{3,}|_{3,})$/.test(trimmed)) {
      flushList();
      out.push("<hr />");
      continue;
    }

    // Encabezados # a ####
    const hMatch = trimmed.match(/^(#{1,4})\s+(.*)$/);
    if (hMatch) {
      flushList();
      const level = hMatch[1].length;
      out.push(`<h${level}>${parseInlineMarkdown(hMatch[2])}</h${level}>`);
      continue;
    }

    // Citas >
    if (trimmed.startsWith(">")) {
      flushList();
      const quoteText = trimmed.replace(/^>\s?/, "");
      out.push(`<blockquote>${parseInlineMarkdown(quoteText)}</blockquote>`);
      continue;
    }

    // Lista de tareas - [x] o - [ ]
    const taskMatch = trimmed.match(/^[-*]\s+\[([ xX])\]\s+(.*)$/);
    if (taskMatch) {
      if (inList !== "ul") {
        flushList();
        inList = "ul";
        out.push('<ul style="list-style:none;padding-left:0.4em;">');
      }
      const checked = taskMatch[1].toLowerCase() === "x";
      out.push(
        `<li style="display:flex;align-items:center;gap:8px;"><input type="checkbox" disabled ${
          checked ? "checked" : ""
        } /> <span style="${checked ? "text-decoration:line-through;opacity:0.7" : ""}">${parseInlineMarkdown(
          taskMatch[2]
        )}</span></li>`
      );
      continue;
    }

    // Lista desordenada - o *
    const ulMatch = trimmed.match(/^[-*+]\s+(.*)$/);
    if (ulMatch) {
      if (inList !== "ul") {
        flushList();
        inList = "ul";
        out.push("<ul>");
      }
      out.push(`<li>${parseInlineMarkdown(ulMatch[1])}</li>`);
      continue;
    }

    // Lista ordenada 1.
    const olMatch = trimmed.match(/^\d+\.\s+(.*)$/);
    if (olMatch) {
      if (inList !== "ol") {
        flushList();
        inList = "ol";
        out.push("<ol>");
      }
      out.push(`<li>${parseInlineMarkdown(olMatch[1])}</li>`);
      continue;
    }

    flushList();
    out.push(`<p>${parseInlineMarkdown(trimmed)}</p>`);
  }

  flushList();
  flushTable();
  return out.join("\n");
}

function parseInlineMarkdown(str) {
  let s = escapeHtml(str);
  // Código en línea `code`
  s = s.replace(/`([^`]+)`/g, "<code>$1</code>");
  // Imágenes ![alt](url)
  s = s.replace(/!\[([^\]]*)\]\(([^)]+)\)/g, '<img src="$2" alt="$1" />');
  // Enlaces [texto](url)
  s = s.replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank" rel="noopener noreferrer">$1</a>');
  // Negrita **texto**
  s = s.replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>");
  // Cursiva *texto*
  s = s.replace(/\*([^*]+)\*/g, "<em>$1</em>");
  // Tachado ~~texto~~
  s = s.replace(/~~([^~]+)~~/g, "<del>$1</del>");
  return s;
}

function renderCsvTable(csvText = "") {
  const rows = csvText
    .replace(/\r\n/g, "\n")
    .trim()
    .split("\n")
    .filter(Boolean)
    .map((line) => line.split(","));
  if (rows.length === 0) return "<p class='preview-meta'>Archivo CSV vacío.</p>";

  let html = '<div class="csv-table-container"><div class="markdown-body"><table><thead><tr>';
  rows[0].forEach((col) => {
    html += `<th>${escapeHtml(col.trim())}</th>`;
  });
  html += "</tr></thead><tbody>";
  rows.slice(1).forEach((row) => {
    html += "<tr>";
    row.forEach((cell) => {
      html += `<td>${escapeHtml(cell.trim())}</td>`;
    });
    html += "</tr>";
  });
  html += "</tbody></table></div></div>";
  return html;
}

// ============================================================================
// CARGA DE DATOS Y RENDERIZADO DEL EXPLORADOR
// ============================================================================

async function fetchCloudData() {
  try {
    const parentParam = state.currentFolderId || "";
    const [itemsRes, sharesRes] = await Promise.all([
      fetch(`/api/items?parentId=${encodeURIComponent(parentParam)}`),
      fetch("/api/shares"),
    ]);
    const itemsData = await itemsRes.json();
    const sharesData = await sharesRes.json();

    state.items = itemsData.items || [];
    state.breadcrumbs = itemsData.breadcrumbs || [];
    state.stats = itemsData.stats || state.stats;
    state.shares = sharesData.shares || [];

    renderStorageWidget();
    renderBreadcrumbs();
    renderExplorer();
  } catch (err) {
    console.error(err);
    showToast("Error al conectar con el servidor de la nube", "⚠️");
  }
}

function renderStorageWidget() {
  const { usedBytes, quotaBytes, totalFiles, totalFolders } = state.stats;
  const pct = Math.min(100, Math.max(1, Math.round((usedBytes / (quotaBytes || 1)) * 100)));
  document.getElementById("storage-percent").textContent = `${
    usedBytes > 0 && pct < 1 ? "< 1" : pct
  }%`;
  document.getElementById("storage-bar-fill").style.width = `${Math.max(3, pct)}%`;
  document.getElementById("storage-meta-text").textContent = `${formatBytes(
    usedBytes
  )} usados de ${formatBytes(quotaBytes)}`;
  document.getElementById(
    "storage-counts-text"
  ).textContent = `${totalFiles} archivos · ${totalFolders} carpetas`;

  const activeSharesCount = state.shares.filter((s) => !s.expired).length;
  const badge = document.getElementById("badge-shares");
  if (activeSharesCount > 0) {
    badge.textContent = String(activeSharesCount);
    badge.classList.remove("hidden");
  } else {
    badge.classList.add("hidden");
  }
}

function renderBreadcrumbs() {
  const bar = document.getElementById("breadcrumbs-bar");
  const btnEmptyTrash = document.getElementById("btn-empty-trash");
  const btnZipFolder = document.getElementById("btn-download-current-folder");

  btnEmptyTrash.classList.toggle("hidden", state.currentSection !== "trash");
  btnZipFolder.classList.toggle(
    "hidden",
    state.currentSection !== "drive" || !state.currentFolderId
  );

  if (state.currentSection !== "drive") {
    const titles = {
      recent: "🕒 Archivos Recientes",
      starred: "⭐ Elementos Destacados",
      markdown: "📝 Documentos Markdown (.md)",
      shares: "🔗 Enlaces Compartidos Activos",
      trash: "🗑️ Papelera de Reciclaje",
    };
    bar.innerHTML = `<span class="crumb active">${titles[state.currentSection] || "Mi Nube"}</span>`;
    return;
  }

  let html = `<button class="crumb ${!state.currentFolderId ? "active" : ""}" data-id="">🏠 Mi Unidad</button>`;
  state.breadcrumbs.forEach((crumb, idx) => {
    const isLast = idx === state.breadcrumbs.length - 1;
    html += `<span class="crumb-sep">›</span><button class="crumb ${
      isLast ? "active" : ""
    }" data-id="${crumb.id}">📁 ${escapeHtml(crumb.name)}</button>`;
  });
  bar.innerHTML = html;

  bar.querySelectorAll(".crumb[data-id]").forEach((btn) => {
    btn.addEventListener("click", () => {
      state.currentFolderId = btn.dataset.id || null;
      fetchCloudData();
    });
  });
}

function getFilteredAndSortedItems() {
  const q = state.searchQuery.trim().toLowerCase();

  let list = state.items.filter((item) => {
    if (state.currentSection === "trash") {
      return Boolean(item.trashed);
    }
    if (item.trashed) return false;

    if (q) {
      return item.name.toLowerCase().includes(q);
    }

    if (state.currentSection === "drive") {
      return (item.parentId || null) === (state.currentFolderId || null);
    }
    if (state.currentSection === "recent") {
      return item.type === "file";
    }
    if (state.currentSection === "starred") {
      return Boolean(item.starred);
    }
    if (state.currentSection === "markdown") {
      return getFileCategory(item) === "md";
    }
    return true;
  });

  // Filtro por tipo en la barra superior
  if (state.typeFilter !== "all") {
    list = list.filter((item) => {
      const cat = getFileCategory(item);
      if (state.typeFilter === "md") return cat === "md";
      if (state.typeFilter === "image") return cat === "image";
      if (state.typeFilter === "media") return cat === "video" || cat === "audio";
      if (state.typeFilter === "code") return cat === "code";
      if (state.typeFilter === "doc") return cat === "pdf" || cat === "csv" || cat === "doc";
      return true;
    });
  }

  // Ordenar: Carpetas siempre primero en Mi Unidad, luego criterio elegido
  list.sort((a, b) => {
    if (state.currentSection === "drive" && a.type !== b.type) {
      return a.type === "folder" ? -1 : 1;
    }
    if (state.sortBy === "name-asc") return a.name.localeCompare(b.name, "es");
    if (state.sortBy === "name-desc") return b.name.localeCompare(a.name, "es");
    if (state.sortBy === "size-desc") return (b.size || 0) - (a.size || 0);
    return new Date(b.updatedAt || 0) - new Date(a.updatedAt || 0);
  });

  return list;
}

function renderExplorer() {
  const container = document.getElementById("items-container");

  // Vista especial de Enlaces Compartidos
  if (state.currentSection === "shares") {
    renderSharesSection(container);
    return;
  }

  const items = getFilteredAndSortedItems();
  container.className = state.viewMode === "grid" ? "items-grid" : "items-list";

  if (items.length === 0) {
    container.className = "";
    container.innerHTML = `
      <div class="empty-state">
        <div class="empty-icon">${state.currentSection === "trash" ? "🗑️" : "☁️"}</div>
        <h3>${
          state.searchQuery
            ? "No se encontraron resultados para tu búsqueda"
            : state.currentSection === "trash"
            ? "La papelera está vacía"
            : "Esta carpeta está vacía"
        }</h3>
        <p>${
          state.currentSection === "trash"
            ? "Los elementos eliminados aparecerán aquí por si necesitas restaurarlos."
            : "Arrastra y suelta archivos aquí desde tu equipo, o usa los botones + Nuevo .md / + Carpeta."
        }</p>
      </div>
    `;
    return;
  }

  if (state.viewMode === "grid") {
    container.innerHTML = items.map((item) => buildGridCardHtml(item)).join("");
  } else {
    container.innerHTML = items.map((item) => buildListRowHtml(item)).join("");
  }

  attachItemEvents(container);
}

function buildGridCardHtml(item) {
  const cat = getFileCategory(item);
  const icon = getFileIcon(item);
  const isImg = cat === "image";

  const previewVisual = isImg
    ? `<img src="/api/files/${item.id}/preview" alt="${escapeHtml(item.name)}" loading="lazy" />`
    : `<div class="card-big-icon">${icon}</div>`;

  const badges = [];
  if (cat === "md") badges.push(`<span class="badge-pill badge-md">MARKDOWN</span>`);
  if (item.isShared) badges.push(`<span class="badge-pill badge-shared">🔗 Compartido</span>`);

  const subLeft =
    item.type === "folder"
      ? `${item.childrenCount || 0} elem. · ${formatBytes(item.size)}`
      : formatBytes(item.size);

  return `
    <div class="item-card" data-id="${item.id}" data-type="${item.type}" draggable="${!item.trashed}">
      <div class="card-preview">
        ${previewVisual}
        <div class="card-badges">${badges.join("")}</div>
        <div class="card-top-actions">
          ${
            !item.trashed
              ? `<button class="card-action-btn btn-star" data-id="${item.id}" title="${
                  item.starred ? "Quitar de destacados" : "Destacar"
                }">${item.starred ? "⭐" : "☆"}</button>
                 <button class="card-action-btn btn-share-item" data-id="${item.id}" title="Compartir enlace">🔗</button>`
              : ""
          }
          <button class="card-action-btn btn-more-item" data-id="${item.id}" title="Más opciones">⋮</button>
        </div>
      </div>
      <div class="card-info">
        <div class="card-name" title="${escapeHtml(item.name)}">${escapeHtml(item.name)}</div>
        <div class="card-sub">
          <span>${subLeft}</span>
          <span>${formatDate(item.updatedAt).split(",")[0]}</span>
        </div>
      </div>
    </div>
  `;
}

function buildListRowHtml(item) {
  const icon = getFileIcon(item);
  const cat = getFileCategory(item);
  const subSize =
    item.type === "folder"
      ? `${item.childrenCount || 0} elem. (${formatBytes(item.size)})`
      : formatBytes(item.size);

  return `
    <div class="list-row" data-id="${item.id}" data-type="${item.type}">
      <div class="list-icon">${icon}</div>
      <div class="list-name-wrap">
        <span class="list-name">${escapeHtml(item.name)}</span>
        ${cat === "md" ? `<span class="badge-pill badge-md">.md</span>` : ""}
        ${item.isShared ? `<span class="badge-pill badge-shared">🔗</span>` : ""}
      </div>
      <div class="list-meta">${subSize}</div>
      <div class="list-meta">${formatDate(item.updatedAt)}</div>
      <div class="list-actions">
        ${
          !item.trashed
            ? `<button class="icon-btn btn-star" data-id="${item.id}" title="Destacar">${
                item.starred ? "⭐" : "☆"
              }</button>
               <button class="icon-btn btn-share-item" data-id="${item.id}" title="Compartir">🔗</button>`
            : ""
        }
        <button class="icon-btn btn-more-item" data-id="${item.id}" title="Opciones">⋮</button>
      </div>
    </div>
  `;
}

function renderSharesSection(container) {
  container.className = "items-list";
  if (state.shares.length === 0) {
    container.className = "";
    container.innerHTML = `
      <div class="empty-state">
        <div class="empty-icon">🔗</div>
        <h3>No tienes enlaces compartidos activos</h3>
        <p>Haz clic en el botón 🔗 de cualquier archivo o carpeta para generar un enlace público.</p>
      </div>
    `;
    return;
  }

  container.innerHTML = state.shares
    .map((s) => {
      const url = `${window.location.origin}/?share=${s.token}`;
      return `
        <div class="list-row" style="grid-template-columns: 40px 1fr 160px 130px 230px; cursor: default;">
          <div class="list-icon">${s.itemType === "folder" ? "📁" : "📄"}</div>
          <div class="list-name-wrap">
            <div>
              <div class="list-name">${escapeHtml(s.itemName)}</div>
              <div class="list-meta" style="font-size:0.75rem">${url}</div>
            </div>
          </div>
          <div class="list-meta">
            ${s.hasPassword ? "🔒 Con contraseña" : "🌐 Público"} · 👁️ ${s.views} vistas
          </div>
          <div class="list-meta">
            ${s.expiresAt ? `Expira: ${formatDate(s.expiresAt).split(",")[0]}` : "Sin expiración"}
          </div>
          <div class="list-actions">
            <button class="btn btn-secondary btn-sm btn-copy-token" data-url="${escapeHtml(url)}">📋 Copiar</button>
            <a href="${escapeHtml(url)}" target="_blank" class="btn btn-secondary btn-sm">↗ Probar</a>
            <button class="btn btn-danger btn-sm btn-revoke-token" data-token="${s.token}">Revocar</button>
          </div>
        </div>
      `;
    })
    .join("");

  container.querySelectorAll(".btn-copy-token").forEach((btn) => {
    btn.addEventListener("click", () => {
      navigator.clipboard.writeText(btn.dataset.url);
      showToast("Enlace copiado al portapapeles", "📋");
    });
  });

  container.querySelectorAll(".btn-revoke-token").forEach((btn) => {
    btn.addEventListener("click", async () => {
      await fetch(`/api/shares/${btn.dataset.token}`, { method: "DELETE" });
      showToast("Enlace compartido revocado", "🗑️");
      fetchCloudData();
    });
  });
}

function attachItemEvents(container) {
  container.querySelectorAll(".item-card, .list-row").forEach((el) => {
    const id = el.dataset.id;
    const item = state.items.find((i) => i.id === id);
    if (!item) return;

    el.addEventListener("click", (e) => {
      if (e.target.closest("button")) return;
      handleItemPrimaryAction(item);
    });

    el.addEventListener("contextmenu", (e) => {
      e.preventDefault();
      openContextMenu(e.clientX, e.clientY, item);
    });

    // Drag & Drop interno para mover archivos dentro de una carpeta
    if (!item.trashed) {
      el.addEventListener("dragstart", (e) => {
        e.dataTransfer.setData("text/nimbus-item-id", item.id);
      });
      if (item.type === "folder") {
        el.addEventListener("dragover", (e) => {
          if (e.dataTransfer.types.includes("text/nimbus-item-id")) {
            e.preventDefault();
            el.style.borderColor = "var(--accent)";
          }
        });
        el.addEventListener("dragleave", () => {
          el.style.borderColor = "";
        });
        el.addEventListener("drop", async (e) => {
          const draggedId = e.dataTransfer.getData("text/nimbus-item-id");
          el.style.borderColor = "";
          if (draggedId && draggedId !== item.id) {
            e.preventDefault();
            e.stopPropagation();
            await updateItem(draggedId, { parentId: item.id });
            showToast(`Movido a "${item.name}"`, "📁");
          }
        });
      }
    }
  });

  container.querySelectorAll(".btn-star").forEach((btn) => {
    btn.addEventListener("click", async (e) => {
      e.stopPropagation();
      const item = state.items.find((i) => i.id === btn.dataset.id);
      if (!item) return;
      await updateItem(item.id, { starred: !item.starred });
      showToast(item.starred ? "Quitado de destacados" : "Añadido a destacados", "⭐");
    });
  });

  container.querySelectorAll(".btn-share-item").forEach((btn) => {
    btn.addEventListener("click", (e) => {
      e.stopPropagation();
      const item = state.items.find((i) => i.id === btn.dataset.id);
      if (item) openShareModal(item);
    });
  });

  container.querySelectorAll(".btn-more-item").forEach((btn) => {
    btn.addEventListener("click", (e) => {
      e.stopPropagation();
      const item = state.items.find((i) => i.id === btn.dataset.id);
      const rect = btn.getBoundingClientRect();
      if (item) openContextMenu(rect.left - 140, rect.bottom + 6, item);
    });
  });
}

function handleItemPrimaryAction(item) {
  if (item.trashed) {
    openContextMenu(window.innerWidth / 2 - 100, window.innerHeight / 2 - 60, item);
    return;
  }
  if (item.type === "folder") {
    state.currentSection = "drive";
    state.currentFolderId = item.id;
    document.querySelectorAll(".nav-item").forEach((n) => {
      n.classList.toggle("active", n.dataset.section === "drive");
    });
    fetchCloudData();
  } else {
    openPreviewModal(item);
  }
}

// ============================================================================
// PREVISUALIZADOR DE ARCHIVOS Y ESTUDIO MARKDOWN (.MD) EN VIVO
// ============================================================================

async function openPreviewModal(item, initialMode = "read") {
  state.activePreviewItem = item;
  state.activePreviewMode = initialMode;
  state.imgZoom = 1;
  state.imgRotation = 0;

  const modal = document.getElementById("preview-modal");
  const cat = getFileCategory(item);

  document.getElementById("preview-file-icon").textContent = getFileIcon(item);
  document.getElementById("preview-file-name").textContent = item.name;
  document.getElementById("preview-file-meta").textContent = `${formatBytes(
    item.size
  )} · Modificado: ${formatDate(item.updatedAt)}`;

  const modeTabs = document.getElementById("preview-mode-tabs");
  const imgControls = document.getElementById("preview-image-controls");
  const saveBtn = document.getElementById("preview-save-btn");
  const mdToolbar = document.getElementById("md-toolbar");

  modeTabs.classList.toggle("hidden", !(cat === "md" || cat === "code" || cat === "csv"));
  imgControls.classList.toggle("hidden", cat !== "image");
  saveBtn.classList.add("hidden");
  mdToolbar.classList.add("hidden");

  modal.classList.remove("hidden");

  const body = document.getElementById("preview-body");
  body.innerHTML = `<div class="preview-stage-center"><p class="preview-meta">Cargando vista previa...</p></div>`;

  if (cat === "md" || cat === "code" || cat === "csv") {
    const res = await fetch(`/api/files/${item.id}/content`);
    const data = await res.json();
    state.activeEditorContent = data.content || "";
    renderTextOrMarkdownWorkspace();
    return;
  }

  if (cat === "image") {
    body.innerHTML = `
      <div class="preview-stage-center">
        <img id="preview-stage-img" src="/api/files/${item.id}/preview?t=${Date.now()}" alt="${escapeHtml(item.name)}" />
      </div>
    `;
    updateImageTransform();
    return;
  }

  if (cat === "video") {
    body.innerHTML = `
      <div class="preview-stage-center">
        <video controls autoplay src="/api/files/${item.id}/preview"></video>
      </div>
    `;
    return;
  }

  if (cat === "audio") {
    body.innerHTML = `
      <div class="preview-stage-center">
        <div class="audio-player-card">
          <div style="font-size:3.8rem;margin-bottom:14px;">🎵</div>
          <h3 style="margin-bottom:6px;">${escapeHtml(item.name)}</h3>
          <p class="preview-meta" style="margin-bottom:20px;">${formatBytes(item.size)}</p>
          <audio controls autoplay src="/api/files/${item.id}/preview" style="width:100%"></audio>
        </div>
      </div>
    `;
    return;
  }

  if (cat === "pdf") {
    body.innerHTML = `<iframe class="pdf-frame" src="/api/files/${item.id}/preview"></iframe>`;
    return;
  }

  // Otros tipos de archivo
  body.innerHTML = `
    <div class="preview-stage-center">
      <div class="audio-player-card">
        <div style="font-size:3.6rem;margin-bottom:12px;">${getFileIcon(item)}</div>
        <h3 style="margin-bottom:8px;">${escapeHtml(item.name)}</h3>
        <p class="preview-meta" style="margin-bottom:20px;">Tipo: ${escapeHtml(
          item.mimeType || "Archivo binario"
        )} · ${formatBytes(item.size)}</p>
        <a href="/api/files/${item.id}/download" class="btn btn-primary">⬇️ Descargar Archivo</a>
      </div>
    </div>
  `;
}

function renderTextOrMarkdownWorkspace() {
  const item = state.activePreviewItem;
  if (!item) return;
  const cat = getFileCategory(item);
  const mode = state.activePreviewMode;

  document.querySelectorAll("#preview-mode-tabs .mode-tab").forEach((btn) => {
    btn.classList.toggle("active", btn.dataset.mode === mode);
  });

  const saveBtn = document.getElementById("preview-save-btn");
  const mdToolbar = document.getElementById("md-toolbar");
  const isEditing = mode === "split" || mode === "edit";

  saveBtn.classList.toggle("hidden", !isEditing);
  mdToolbar.classList.toggle("hidden", !(cat === "md" && isEditing));

  const body = document.getElementById("preview-body");

  if (cat === "csv" && mode === "read") {
    body.innerHTML = renderCsvTable(state.activeEditorContent);
    return;
  }

  if (cat === "code" && mode === "read") {
    body.innerHTML = `
      <div class="md-preview-pane">
        <div class="markdown-body">
          <pre><code>${escapeHtml(state.activeEditorContent)}</code></pre>
        </div>
      </div>
    `;
    return;
  }

  if (mode === "read") {
    body.innerHTML = `
      <div class="md-workspace mode-read">
        <div class="md-preview-pane">
          <div class="markdown-body" id="live-md-output">${renderMarkdown(state.activeEditorContent)}</div>
        </div>
      </div>
    `;
    return;
  }

  if (mode === "split") {
    body.innerHTML = `
      <div class="md-workspace mode-split">
        <div class="md-editor-pane">
          <textarea id="live-md-textarea" class="md-textarea" spellcheck="false" placeholder="Escribe tu contenido Markdown aquí..."></textarea>
        </div>
        <div class="md-preview-pane">
          <div class="markdown-body" id="live-md-output">${
            cat === "csv"
              ? renderCsvTable(state.activeEditorContent)
              : cat === "code"
              ? `<pre><code>${escapeHtml(state.activeEditorContent)}</code></pre>`
              : renderMarkdown(state.activeEditorContent)
          }</div>
        </div>
      </div>
    `;
  } else {
    body.innerHTML = `
      <div class="md-workspace mode-edit">
        <div class="md-editor-pane">
          <textarea id="live-md-textarea" class="md-textarea" spellcheck="false"></textarea>
        </div>
      </div>
    `;
  }

  const textarea = document.getElementById("live-md-textarea");
  if (textarea) {
    textarea.value = state.activeEditorContent;
    updateMarkdownCounters(textarea.value);
    textarea.addEventListener("input", () => {
      state.activeEditorContent = textarea.value;
      updateMarkdownCounters(textarea.value);
      const output = document.getElementById("live-md-output");
      if (output) {
        if (cat === "csv") output.innerHTML = renderCsvTable(textarea.value);
        else if (cat === "code") output.innerHTML = `<pre><code>${escapeHtml(textarea.value)}</code></pre>`;
        else output.innerHTML = renderMarkdown(textarea.value);
      }
    });
  }
}

function updateMarkdownCounters(text = "") {
  const words = text.trim() ? text.trim().split(/\s+/).length : 0;
  const chars = text.length;
  const el = document.getElementById("md-stats-counter");
  if (el) el.textContent = `${words} palabras · ${chars} caracteres`;
}

async function saveActiveFileContent() {
  const item = state.activePreviewItem;
  if (!item) return;
  const res = await fetch(`/api/files/${item.id}/content`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ content: state.activeEditorContent }),
  });
  if (res.ok) {
    const data = await res.json();
    state.activePreviewItem = data.item;
    document.getElementById("preview-file-meta").textContent = `${formatBytes(
      data.item.size
    )} · Guardado: ${formatDate(data.item.updatedAt)}`;
    showToast("Cambios guardados en la nube", "💾");
    fetchCloudData();
  } else {
    showToast("No se pudo guardar el archivo", "⚠️");
  }
}

function insertMarkdownSnippet(type) {
  const textarea = document.getElementById("live-md-textarea");
  if (!textarea) return;
  const start = textarea.selectionStart;
  const end = textarea.selectionEnd;
  const selected = textarea.value.slice(start, end) || "texto";

  const snippets = {
    h1: `\n# ${selected}\n`,
    h2: `\n## ${selected}\n`,
    bold: `**${selected}**`,
    italic: `*${selected}*`,
    strike: `~~${selected}~~`,
    task: `\n- [ ] ${selected}`,
    ul: `\n- ${selected}`,
    quote: `\n> ${selected}`,
    code: `\n\`\`\`javascript\n${selected}\n\`\`\`\n`,
    table: `\n| Columna 1 | Columna 2 | Columna 3 |\n| :--- | :--- | :--- |\n| Valor 1 | Valor 2 | Valor 3 |\n`,
    link: `[${selected}](https://ejemplo.com)`,
  };

  const insert = snippets[type] || selected;
  textarea.setRangeText(insert, start, end, "end");
  textarea.dispatchEvent(new Event("input"));
  textarea.focus();
}

function updateImageTransform() {
  const img = document.getElementById("preview-stage-img");
  const label = document.getElementById("img-zoom-label");
  if (img) {
    img.style.transform = `scale(${state.imgZoom}) rotate(${state.imgRotation}deg)`;
  }
  if (label) {
    label.textContent = `${Math.round(state.imgZoom * 100)}%`;
  }
}

// ============================================================================
// OPERACIONES CRUD: SUBIR, CARPETAS, NUEVO .MD, MOVER, RENOMBRAR, PAPELERA
// ============================================================================

async function uploadFilesList(fileList) {
  if (!fileList || fileList.length === 0) return;
  const formData = new FormData();
  formData.append("parentId", state.currentFolderId || "");
  for (const file of fileList) {
    formData.append("files", file);
  }

  showToast(`Subiendo ${fileList.length} archivo(s)...`, "⬆️");
  const res = await fetch("/api/upload", {
    method: "POST",
    body: formData,
  });
  if (res.ok) {
    showToast(`${fileList.length} archivo(s) subidos con éxito`, "✅");
    fetchCloudData();
  } else {
    showToast("Error al subir archivos", "⚠️");
  }
}

async function updateItem(itemId, patchData) {
  const res = await fetch(`/api/items/${itemId}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(patchData),
  });
  if (res.ok) {
    await fetchCloudData();
  } else {
    const err = await res.json().catch(() => ({}));
    showToast(err.error || "No se pudo actualizar el elemento", "⚠️");
  }
}

function openDialogModal({ title, contentHtml, confirmText = "Guardar", onConfirm }) {
  const modal = document.getElementById("dialog-modal");
  document.getElementById("dialog-title").textContent = title;
  document.getElementById("dialog-content").innerHTML = contentHtml;
  document.getElementById("dialog-confirm").textContent = confirmText;
  modal.classList.remove("hidden");

  const firstInput = modal.querySelector("input, select");
  if (firstInput) setTimeout(() => firstInput.focus(), 50);

  const form = document.getElementById("dialog-form");
  form.onsubmit = async (e) => {
    e.preventDefault();
    await onConfirm();
    modal.classList.add("hidden");
  };
}

function promptNewFolder() {
  openDialogModal({
    title: "📁 Crear Nueva Carpeta",
    confirmText: "Crear Carpeta",
    contentHtml: `
      <div class="form-group">
        <label for="input-folder-name">Nombre de la carpeta</label>
        <input type="text" id="input-folder-name" placeholder="Ej. Mis Proyectos 2026" required />
      </div>
    `,
    onConfirm: async () => {
      const name = document.getElementById("input-folder-name").value.trim();
      if (!name) return;
      await fetch("/api/folders", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name, parentId: state.currentFolderId }),
      });
      showToast(`Carpeta "${name}" creada`, "📁");
      fetchCloudData();
    },
  });
}

function promptNewMarkdownDoc() {
  openDialogModal({
    title: "📝 Nuevo Documento Markdown (.md)",
    confirmText: "Crear y Abrir Editor",
    contentHtml: `
      <div class="form-group">
        <label for="input-md-name">Nombre del archivo (.md)</label>
        <input type="text" id="input-md-name" value="Nueva Nota.md" required />
      </div>
    `,
    onConfirm: async () => {
      let name = document.getElementById("input-md-name").value.trim();
      if (!name) return;
      if (!name.toLowerCase().endsWith(".md")) name += ".md";
      const titleClean = name.replace(/\.md$/i, "");
      const initialMd = `# ${titleClean}\n\nEscribe aquí tus notas en formato **Markdown**...\n\n- [ ] Primera tarea\n- [ ] Segunda tarea\n`;
      const res = await fetch("/api/files/text", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name,
          content: initialMd,
          parentId: state.currentFolderId,
        }),
      });
      if (res.ok) {
        const data = await res.json();
        await fetchCloudData();
        openPreviewModal(data.item, "split");
      }
    },
  });
}

function promptRenameItem(item) {
  openDialogModal({
    title: "✏️ Renombrar",
    confirmText: "Guardar Nombre",
    contentHtml: `
      <div class="form-group">
        <label for="input-rename">Nuevo nombre</label>
        <input type="text" id="input-rename" value="${escapeHtml(item.name)}" required />
      </div>
    `,
    onConfirm: async () => {
      const newName = document.getElementById("input-rename").value.trim();
      if (newName && newName !== item.name) {
        await updateItem(item.id, { name: newName });
        showToast("Nombre actualizado", "✏️");
      }
    },
  });
}

function promptMoveItem(item) {
  const folders = state.items.filter(
    (i) => i.type === "folder" && !i.trashed && i.id !== item.id
  );
  const optionsHtml = [
    `<option value="root" ${!item.parentId ? "selected" : ""}>🏠 Mi Unidad (Raíz)</option>`,
    ...folders.map(
      (f) =>
        `<option value="${f.id}" ${item.parentId === f.id ? "selected" : ""}>📁 ${escapeHtml(
          f.name
        )}</option>`
    ),
  ].join("");

  openDialogModal({
    title: `📂 Mover "${item.name}"`,
    confirmText: "Mover Aquí",
    contentHtml: `
      <div class="form-group">
        <label for="select-move-target">Selecciona carpeta de destino</label>
        <select id="select-move-target">${optionsHtml}</select>
      </div>
    `,
    onConfirm: async () => {
      const target = document.getElementById("select-move-target").value;
      await updateItem(item.id, { parentId: target === "root" ? null : target });
      showToast("Elemento movido correctamente", "📂");
    },
  });
}

// ============================================================================
// MENÚ CONTEXTUAL (CLIC DERECHO) Y MODAL DE COMPARTIR
// ============================================================================

function openContextMenu(x, y, item) {
  const menu = document.getElementById("context-menu");
  const cat = getFileCategory(item);

  if (item.trashed) {
    menu.innerHTML = `
      <button class="ctx-item" data-action="restore">♻️ Restaurar elemento</button>
      <div class="ctx-sep"></div>
      <button class="ctx-item danger" data-action="delete-perm">🔥 Eliminar definitivamente</button>
    `;
  } else {
    menu.innerHTML = `
      <button class="ctx-item" data-action="open">${
        item.type === "folder" ? "📂 Abrir carpeta" : "👁️ Vista previa"
      }</button>
      ${
        cat === "md" || cat === "code"
          ? `<button class="ctx-item" data-action="edit-live">⚡ Editar en Vista Dividida</button>`
          : ""
      }
      <button class="ctx-item" data-action="share">🔗 Compartir enlace...</button>
      <button class="ctx-item" data-action="star">${
        item.starred ? "☆ Quitar de destacados" : "⭐ Añadir a destacados"
      }</button>
      <div class="ctx-sep"></div>
      <button class="ctx-item" data-action="rename">✏️ Renombrar</button>
      <button class="ctx-item" data-action="move">📂 Mover a otra carpeta...</button>
      <button class="ctx-item" data-action="download">${
        item.type === "folder" ? "📦 Descargar como .ZIP" : "⬇️ Descargar archivo"
      }</button>
      <div class="ctx-sep"></div>
      <button class="ctx-item danger" data-action="trash">🗑️ Enviar a la papelera</button>
    `;
  }

  menu.classList.remove("hidden");
  const maxX = window.innerWidth - 220;
  const maxY = window.innerHeight - 280;
  menu.style.left = `${Math.max(10, Math.min(x, maxX))}px`;
  menu.style.top = `${Math.max(10, Math.min(y, maxY))}px`;

  menu.querySelectorAll(".ctx-item").forEach((btn) => {
    btn.addEventListener("click", async () => {
      menu.classList.add("hidden");
      const act = btn.dataset.action;
      if (act === "open") handleItemPrimaryAction(item);
      if (act === "edit-live") openPreviewModal(item, "split");
      if (act === "share") openShareModal(item);
      if (act === "star") updateItem(item.id, { starred: !item.starred });
      if (act === "rename") promptRenameItem(item);
      if (act === "move") promptMoveItem(item);
      if (act === "download") {
        window.location.href =
          item.type === "folder"
            ? `/api/folders/${item.id}/zip`
            : `/api/files/${item.id}/download`;
      }
      if (act === "trash") {
        await updateItem(item.id, { trashed: true });
        showToast(`"${item.name}" enviado a la papelera`, "🗑️");
      }
      if (act === "restore") {
        await updateItem(item.id, { trashed: false });
        showToast(`"${item.name}" restaurado`, "♻️");
      }
      if (act === "delete-perm") {
        await fetch(`/api/items/${item.id}`, { method: "DELETE" });
        showToast("Eliminado permanentemente", "🔥");
        fetchCloudData();
      }
    });
  });
}

function openShareModal(item) {
  const modal = document.getElementById("share-modal");
  document.getElementById("share-modal-subtitle").textContent = `${getFileIcon(item)} ${
    item.name
  } (${formatBytes(item.size)})`;
  document.getElementById("share-password").value = "";
  document.getElementById("share-expiry").value = "0";
  document.getElementById("share-generated-box").classList.add("hidden");

  renderItemExistingShares(item.id);
  modal.classList.remove("hidden");

  const form = document.getElementById("create-share-form");
  form.onsubmit = async (e) => {
    e.preventDefault();
    const password = document.getElementById("share-password").value;
    const expiresInHours = Number(document.getElementById("share-expiry").value);

    const res = await fetch("/api/shares", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ itemId: item.id, password, expiresInHours }),
    });
    if (res.ok) {
      const data = await res.json();
      const shareUrl = `${window.location.origin}/?share=${data.share.token}`;
      document.getElementById("share-url-input").value = shareUrl;
      document.getElementById("btn-open-share-url").href = shareUrl;
      document.getElementById("share-generated-box").classList.remove("hidden");
      await fetchCloudData();
      renderItemExistingShares(item.id);
      showToast("Enlace público creado", "🔗");
    }
  };
}

function renderItemExistingShares(itemId) {
  const listEl = document.getElementById("item-shares-list");
  const itemShares = state.shares.filter((s) => s.itemId === itemId);

  if (itemShares.length === 0) {
    listEl.innerHTML = `<p class="preview-meta">Aún no hay enlaces activos para este elemento.</p>`;
    return;
  }

  listEl.innerHTML = itemShares
    .map((s) => {
      const url = `${window.location.origin}/?share=${s.token}`;
      return `
        <div class="share-list-item">
          <div>
            <strong>${s.hasPassword ? "🔒 Protegido" : "🌐 Público"}</strong> · 👁️ ${s.views} vistas
            <div class="preview-meta">${url}</div>
          </div>
          <div style="display:flex;gap:6px;">
            <button type="button" class="btn btn-secondary btn-sm btn-copy-s" data-url="${escapeHtml(
              url
            )}">Copiar</button>
            <button type="button" class="btn btn-danger btn-sm btn-del-s" data-token="${
              s.token
            }">✕</button>
          </div>
        </div>
      `;
    })
    .join("");

  listEl.querySelectorAll(".btn-copy-s").forEach((btn) => {
    btn.addEventListener("click", () => {
      navigator.clipboard.writeText(btn.dataset.url);
      showToast("Enlace copiado", "📋");
    });
  });

  listEl.querySelectorAll(".btn-del-s").forEach((btn) => {
    btn.addEventListener("click", async () => {
      await fetch(`/api/shares/${btn.dataset.token}`, { method: "DELETE" });
      await fetchCloudData();
      renderItemExistingShares(itemId);
      showToast("Enlace eliminado", "🗑️");
    });
  });
}

// ============================================================================
// PORTAL PÚBLICO PARA ENLACES COMPARTIDOS (?share=TOKEN)
// ============================================================================

async function initPublicSharePortal(token, password = "") {
  document.getElementById("main-cloud-app").classList.add("hidden");
  const appEl = document.getElementById("public-share-App");
  appEl.classList.remove("hidden");

  const container = document.getElementById("public-share-container");
  container.innerHTML = `<div class="public-card"><div class="public-card-body"><p>Cargando elemento compartido...</p></div></div>`;

  const url = `/api/public/${encodeURIComponent(token)}${
    password ? `?password=${encodeURIComponent(password)}` : ""
  }`;
  const res = await fetch(url);
  const data = await res.json();

  if (res.status === 401 && data.requiresPassword) {
    container.innerHTML = `
      <div class="public-card" style="max-width:440px;margin:40px auto;">
        <div class="public-card-header">
          <h3>🔒 Enlace Protegido con Contraseña</h3>
        </div>
        <form id="public-pwd-form" class="public-card-body">
          <p class="preview-meta" style="margin-bottom:14px;">Ingresa la contraseña para acceder a <strong>${escapeHtml(
            data.itemName
          )}</strong>.</p>
          <div class="form-group">
            <input type="password" id="public-pwd-input" placeholder="Contraseña..." required autofocus />
          </div>
          ${password ? `<p style="color:var(--danger);font-size:0.82rem;margin-bottom:10px;">Contraseña incorrecta, inténtalo de nuevo.</p>` : ""}
          <button type="submit" class="btn btn-primary btn-block">Desbloquear Contenido</button>
        </form>
      </div>
    `;
    document.getElementById("public-pwd-form").onsubmit = (e) => {
      e.preventDefault();
      const val = document.getElementById("public-pwd-input").value;
      initPublicSharePortal(token, val);
    };
    return;
  }

  if (!res.ok) {
    container.innerHTML = `
      <div class="public-card" style="max-width:500px;margin:40px auto;text-align:center;">
        <div class="public-card-body">
          <div style="font-size:3rem;margin-bottom:10px;">⚠️</div>
          <h3>Enlace no disponible</h3>
          <p class="preview-meta" style="margin:10px 0 20px;">${escapeHtml(
            data.error || "El enlace no existe o ha expirado."
          )}</p>
          <a href="/" class="btn btn-primary">Ir a Nimbus Cloud</a>
        </div>
      </div>
    `;
    return;
  }

  const item = data.item;
  const cat = getFileCategory(item);
  const rawBase = `/api/public/${encodeURIComponent(token)}/raw?itemId=${encodeURIComponent(
    item.id
  )}${password ? `&password=${encodeURIComponent(password)}` : ""}`;

  let bodyHtml = "";
  if (item.type === "folder") {
    const children = data.children || [];
    bodyHtml =
      children.length === 0
        ? `<p class="preview-meta">Esta carpeta compartida está vacía.</p>`
        : `<div class="items-list">
            ${children
              .map((c) => {
                const cDownload = `/api/public/${encodeURIComponent(
                  token
                )}/raw?itemId=${encodeURIComponent(c.id)}&download=1${
                  password ? `&password=${encodeURIComponent(password)}` : ""
                }`;
                return `
                  <div class="list-row" style="grid-template-columns:40px 1fr 120px 140px;cursor:default;">
                    <div class="list-icon">${getFileIcon(c)}</div>
                    <div class="list-name">${escapeHtml(c.name)}</div>
                    <div class="list-meta">${formatBytes(c.size)}</div>
                    <div class="list-actions">
                      <a href="${cDownload}" class="btn btn-secondary btn-sm">⬇️ Descargar</a>
                    </div>
                  </div>
                `;
              })
              .join("")}
          </div>`;
  } else if (cat === "md") {
    bodyHtml = `<div class="markdown-body">${renderMarkdown(data.textContent || "")}</div>`;
  } else if (cat === "csv") {
    bodyHtml = renderCsvTable(data.textContent || "");
  } else if (cat === "code") {
    bodyHtml = `<div class="markdown-body"><pre><code>${escapeHtml(
      data.textContent || ""
    )}</code></pre></div>`;
  } else if (cat === "image") {
    bodyHtml = `<div style="text-align:center"><img src="${rawBase}" style="max-width:100%;max-height:70vh;border-radius:12px;" /></div>`;
  } else if (cat === "video") {
    bodyHtml = `<div style="text-align:center"><video controls src="${rawBase}" style="max-width:100%;max-height:70vh;border-radius:12px;"></video></div>`;
  } else if (cat === "audio") {
    bodyHtml = `<div style="text-align:center;padding:24px;"><audio controls src="${rawBase}" style="width:100%;max-width:460px;"></audio></div>`;
  } else if (cat === "pdf") {
    bodyHtml = `<iframe src="${rawBase}" style="width:100%;height:72vh;border:none;border-radius:8px;"></iframe>`;
  } else {
    bodyHtml = `<p class="preview-meta">Haz clic en el botón Descargar arriba a la derecha para obtener este archivo.</p>`;
  }

  container.innerHTML = `
    <div class="public-card">
      <div class="public-card-header">
        <div style="display:flex;align-items:center;gap:12px;">
          <span style="font-size:2rem;">${getFileIcon(item)}</span>
          <div>
            <h2>${escapeHtml(item.name)}</h2>
            <span class="preview-meta">${formatBytes(item.size)} · Actualizado: ${formatDate(
    item.updatedAt
  )} · 👁️ ${data.views} vistas</span>
          </div>
        </div>
        <a href="${rawBase}&download=1" class="btn btn-primary">
          ${item.type === "folder" ? "📦 Descargar Carpeta (.ZIP)" : "⬇️ Descargar Archivo"}
        </a>
      </div>
      <div class="public-card-body">${bodyHtml}</div>
    </div>
  `;
}

// ============================================================================
// INICIALIZACIÓN Y EVENTOS GLOBALES DE LA INTERFAZ
// ============================================================================

function applyTheme(theme) {
  state.theme = theme;
  document.documentElement.setAttribute("data-theme", theme);
  localStorage.setItem("nimbus_theme", theme);
}

function initApp() {
  applyTheme(state.theme);

  // Detectar si estamos visitando un enlace compartido (?share=TOKEN)
  const params = new URLSearchParams(window.location.search);
  const shareToken = params.get("share");
  if (shareToken) {
    document.getElementById("public-theme-btn").addEventListener("click", () => {
      applyTheme(state.theme === "dark" ? "light" : "dark");
    });
    initPublicSharePortal(shareToken);
    return;
  }

  // Navegación lateral
  document.querySelectorAll(".nav-item").forEach((btn) => {
    btn.addEventListener("click", () => {
      document.querySelectorAll(".nav-item").forEach((b) => b.classList.remove("active"));
      btn.classList.add("active");
      state.currentSection = btn.dataset.section;
      if (state.currentSection !== "drive") {
        state.currentFolderId = null;
      }
      fetchCloudData();
    });
  });

  // Botones de creación / subida rápida
  const fileInput = document.getElementById("hidden-file-input");
  document.getElementById("btn-quick-upload").addEventListener("click", () => fileInput.click());
  fileInput.addEventListener("change", () => {
    uploadFilesList(fileInput.files);
    fileInput.value = "";
  });

  document.getElementById("btn-new-folder").addEventListener("click", promptNewFolder);
  document.getElementById("btn-new-md").addEventListener("click", promptNewMarkdownDoc);

  // Descargar carpeta actual en ZIP
  document.getElementById("btn-download-current-folder").addEventListener("click", () => {
    if (state.currentFolderId) {
      window.location.href = `/api/folders/${state.currentFolderId}/zip`;
    }
  });

  // Vaciar papelera
  document.getElementById("btn-empty-trash").addEventListener("click", () => {
    openDialogModal({
      title: "🗑️ Vaciar Papelera",
      confirmText: "Eliminar Todo Definitivamente",
      contentHtml: `<p class="preview-meta">¿Estás seguro de que deseas eliminar permanentemente todos los archivos de la papelera? Esta acción no se puede deshacer.</p>`,
      onConfirm: async () => {
        await fetch("/api/trash/empty", { method: "POST" });
        showToast("Papelera vaciada por completo", "🗑️");
        fetchCloudData();
      },
    });
  });

  // Buscador en vivo + Atajo Ctrl + K
  const searchInput = document.getElementById("search-input");
  const searchClear = document.getElementById("search-clear");
  searchInput.addEventListener("input", () => {
    state.searchQuery = searchInput.value;
    searchClear.classList.toggle("hidden", !state.searchQuery);
    renderExplorer();
  });
  searchClear.addEventListener("click", () => {
    searchInput.value = "";
    state.searchQuery = "";
    searchClear.classList.add("hidden");
    renderExplorer();
  });

  // Filtros de categoría
  document.querySelectorAll("#type-filters .pill").forEach((pill) => {
    pill.addEventListener("click", () => {
      document.querySelectorAll("#type-filters .pill").forEach((p) => p.classList.remove("active"));
      pill.classList.add("active");
      state.typeFilter = pill.dataset.filter;
      renderExplorer();
    });
  });

  // Ordenamiento y Vista Cuadrícula / Lista
  document.getElementById("sort-select").addEventListener("change", (e) => {
    state.sortBy = e.target.value;
    renderExplorer();
  });

  const gridBtn = document.getElementById("view-grid-btn");
  const listBtn = document.getElementById("view-list-btn");
  const updateViewButtons = () => {
    gridBtn.classList.toggle("active", state.viewMode === "grid");
    listBtn.classList.toggle("active", state.viewMode === "list");
  };
  updateViewButtons();

  gridBtn.addEventListener("click", () => {
    state.viewMode = "grid";
    localStorage.setItem("nimbus_view", "grid");
    updateViewButtons();
    renderExplorer();
  });
  listBtn.addEventListener("click", () => {
    state.viewMode = "list";
    localStorage.setItem("nimbus_view", "list");
    updateViewButtons();
    renderExplorer();
  });

  // Cambiar tema Oscuro / Claro
  document.getElementById("theme-toggle-btn").addEventListener("click", () => {
    applyTheme(state.theme === "dark" ? "light" : "dark");
  });

  // Controles del Modal Previsualizador / Estudio Markdown
  document.querySelectorAll("#preview-mode-tabs .mode-tab").forEach((tab) => {
    tab.addEventListener("click", () => {
      state.activePreviewMode = tab.dataset.mode;
      renderTextOrMarkdownWorkspace();
    });
  });

  document.querySelectorAll(".md-tool-btn").forEach((btn) => {
    btn.addEventListener("click", () => insertMarkdownSnippet(btn.dataset.md));
  });

  document.getElementById("preview-save-btn").addEventListener("click", saveActiveFileContent);
  document.getElementById("preview-share-btn").addEventListener("click", () => {
    if (state.activePreviewItem) openShareModal(state.activePreviewItem);
  });
  document.getElementById("preview-download-btn").addEventListener("click", () => {
    if (state.activePreviewItem) {
      window.location.href = `/api/files/${state.activePreviewItem.id}/download`;
    }
  });
  document.getElementById("preview-close-btn").addEventListener("click", () => {
    document.getElementById("preview-modal").classList.add("hidden");
    document.getElementById("preview-body").innerHTML = "";
    state.activePreviewItem = null;
  });

  // Controles de zoom/rotación de imágenes
  document.getElementById("img-zoom-in").addEventListener("click", () => {
    state.imgZoom = Math.min(3, +(state.imgZoom + 0.25).toFixed(2));
    updateImageTransform();
  });
  document.getElementById("img-zoom-out").addEventListener("click", () => {
    state.imgZoom = Math.max(0.25, +(state.imgZoom - 0.25).toFixed(2));
    updateImageTransform();
  });
  document.getElementById("img-rotate").addEventListener("click", () => {
    state.imgRotation = (state.imgRotation + 90) % 360;
    updateImageTransform();
  });
  document.getElementById("img-reset").addEventListener("click", () => {
    state.imgZoom = 1;
    state.imgRotation = 0;
    updateImageTransform();
  });

  // Cerrar modales de compartir y diálogo
  document.getElementById("share-modal-close").addEventListener("click", () => {
    document.getElementById("share-modal").classList.add("hidden");
  });
  document.getElementById("btn-copy-share-url").addEventListener("click", () => {
    const val = document.getElementById("share-url-input").value;
    navigator.clipboard.writeText(val);
    showToast("Enlace copiado al portapapeles", "📋");
  });
  document.getElementById("dialog-close").addEventListener("click", () => {
    document.getElementById("dialog-modal").classList.add("hidden");
  });
  document.getElementById("dialog-cancel").addEventListener("click", () => {
    document.getElementById("dialog-modal").classList.add("hidden");
  });

  // Cerrar menú contextual al hacer clic fuera
  window.addEventListener("click", () => {
    document.getElementById("context-menu").classList.add("hidden");
  });

  // Atajos de teclado (Ctrl+K buscar, Ctrl+S guardar en editor .md, Esc cerrar modal)
  window.addEventListener("keydown", (e) => {
    if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "k") {
      e.preventDefault();
      searchInput.focus();
    }
    if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "s") {
      if (state.activePreviewItem && (state.activePreviewMode === "split" || state.activePreviewMode === "edit")) {
        e.preventDefault();
        saveActiveFileContent();
      }
    }
    if (e.key === "Escape") {
      document.getElementById("context-menu").classList.add("hidden");
      document.getElementById("dialog-modal").classList.add("hidden");
      document.getElementById("share-modal").classList.add("hidden");
      if (!document.getElementById("preview-modal").classList.contains("hidden")) {
        document.getElementById("preview-close-btn").click();
      }
    }
  });

  // Drag & Drop de archivos externos hacia la ventana
  let dragCounter = 0;
  const dropOverlay = document.getElementById("dropzone-overlay");

  window.addEventListener("dragenter", (e) => {
    if (e.dataTransfer && e.dataTransfer.types.includes("Files")) {
      e.preventDefault();
      dragCounter++;
      dropOverlay.classList.remove("hidden");
    }
  });

  window.addEventListener("dragover", (e) => {
    if (e.dataTransfer && e.dataTransfer.types.includes("Files")) {
      e.preventDefault();
    }
  });

  window.addEventListener("dragleave", (e) => {
    if (e.dataTransfer && e.dataTransfer.types.includes("Files")) {
      dragCounter--;
      if (dragCounter <= 0) {
        dragCounter = 0;
        dropOverlay.classList.add("hidden");
      }
    }
  });

  window.addEventListener("drop", (e) => {
    if (e.dataTransfer && e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      e.preventDefault();
      dragCounter = 0;
      dropOverlay.classList.add("hidden");
      uploadFilesList(e.dataTransfer.files);
    }
  });

  // Cargar datos iniciales de la nube
  fetchCloudData();
}

document.addEventListener("DOMContentLoaded", initApp);
