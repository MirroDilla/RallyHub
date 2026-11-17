// Registro rápido de estudiantes. Crea la cuenta y abre la sesión (cookies del servidor).
import { api, ApiError } from './api.js';

const form = document.getElementById('form');
const msg = document.getElementById('msg');
const go = document.getElementById('go');

// Si ya hay sesión abierta, no tiene sentido registrarse: ir al panel.
api('/auth/me').then(() => { location.href = '/'; }).catch(() => { /* sin sesión: mostrar formulario */ });

form.addEventListener('submit', async (ev) => {
  ev.preventDefault();
  msg.replaceChildren();
  const data = {
    first_name: form.first_name.value.trim(),
    last_name: form.last_name.value.trim(),
    email: form.email.value.trim(),
    password: form.password.value,
  };
  const problem = validate(data, form.password2.value);
  if (problem) { show(problem); return; }
  go.disabled = true;
  try {
    await api('/auth/register', { method: 'POST', body: data });
    location.href = '/';
  } catch (e) {
    if (e instanceof ApiError && e.errors?.length) show(e.errors.map((x) => String(x.message ?? '').replace(/^Value error, /, '')).join(' '));
    else show(e instanceof ApiError ? e.message : 'No fue posible crear la cuenta.');
  } finally { go.disabled = false; }
});

// Mismas reglas que el servidor, para avisar antes de enviar.
function validate(d, confirm) {
  if (!d.first_name || !d.last_name || !d.email || !d.password) return 'Completa todos los campos.';
  if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(d.email)) return 'Escribe un correo electrónico válido.';
  if (d.password.length < 10) return 'La contraseña debe tener al menos 10 caracteres.';
  if (!/[A-Za-zÁÉÍÓÚáéíóúÑñ]/.test(d.password) || !/\d/.test(d.password)) return 'La contraseña debe incluir letras y números.';
  if (d.password !== confirm) return 'Las contraseñas no coinciden.';
  return '';
}

function show(text) {
  const d = document.createElement('div');
  d.className = 'alert err';
  d.textContent = text;
  msg.append(d);
}
