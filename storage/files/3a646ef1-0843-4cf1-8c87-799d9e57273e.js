const forms = {
  create: document.querySelector('#create-form'),
  update: document.querySelector('#update-form'),
};
const statusElement = document.querySelector('#connection-status');

function parsePayload(form) {
  const rawJson = form.querySelector('.json-input').value.trim();
  if (!rawJson) throw new Error('Pegue el JSON de la notificación antes de enviarlo.');
  try {
    const payload = JSON.parse(rawJson);
    if (!payload || Array.isArray(payload) || typeof payload !== 'object') {
      throw new Error('El JSON debe ser un objeto con los campos de la notificación.');
    }
    return payload;
  } catch (error) {
    throw new Error(error instanceof SyntaxError ? 'El texto no es un JSON válido. Revise comas, comillas y llaves.' : error.message);
  }
}

function showResult(title, content, isError = false) {
  const panel = document.querySelector('#result-panel');
  panel.classList.remove('hidden', 'error');
  panel.classList.toggle('error', isError);
  document.querySelector('#result-title').textContent = title;
  document.querySelector('#result-content').textContent = typeof content === 'string' ? content : JSON.stringify(content, null, 2);
  panel.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

async function sendForm(kind) {
  const form = forms[kind];
  let payload;
  try {
    payload = parsePayload(form);
  } catch (error) {
    showResult('JSON inválido', error.message, true);
    return;
  }

  const button = form.querySelector('[type="submit"]');
  button.disabled = true;
  button.innerHTML = 'Enviando…';
  try {
    const response = await fetch(`/api/notificaciones/${kind === 'create' ? 'crear' : 'actualizar'}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ payload }),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || 'No fue posible completar la operación.');
    showResult('Operación enviada correctamente', data.result);
  } catch (error) {
    showResult('Error al comunicarse con SAT', error.message, true);
  } finally {
    button.disabled = false;
    button.innerHTML = kind === 'create' ? 'Enviar creación <span>→</span>' : 'Enviar actualización <span>→</span>';
  }
}

async function checkStatus() {
  try {
    const response = await fetch('/api/status');
    const data = await response.json();
    statusElement.className = `connection ${data.authenticated ? 'online' : 'offline'}`;
    statusElement.querySelector('span').textContent = data.authenticated
      ? `Conectado · token vigente (${Math.ceil(data.seconds_remaining / 60)} min)`
      : 'Sin token · se autentica al enviar';
  } catch {
    statusElement.className = 'connection offline';
    statusElement.querySelector('span').textContent = 'Estado no disponible';
  }
}

document.querySelectorAll('.tab').forEach((tab) => tab.addEventListener('click', () => {
  document.querySelectorAll('.tab').forEach((item) => item.classList.toggle('active', item === tab));
  Object.entries(forms).forEach(([key, form]) => form.classList.toggle('hidden', key !== tab.dataset.tab));
}));
Object.entries(forms).forEach(([kind, form]) => form.addEventListener('submit', (event) => { event.preventDefault(); sendForm(kind); }));
document.querySelector('#close-result').addEventListener('click', () => document.querySelector('#result-panel').classList.add('hidden'));
checkStatus();
setInterval(checkStatus, 60000);
