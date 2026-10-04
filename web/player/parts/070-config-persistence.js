// ---- config persistence ----
const CONFIG_KEY = 'vefr-packaged-config';
function loadConfig() {
  try { return JSON.parse(localStorage.getItem(CONFIG_KEY) || '{}'); }
  catch (_) { return {}; }
}
function saveConfig(c) {
  try { localStorage.setItem(CONFIG_KEY, JSON.stringify(c)); } catch (_) { /* blocked storage: keep going in memory */ }
}
