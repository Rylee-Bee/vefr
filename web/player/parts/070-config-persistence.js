// ---- config persistence ----
const CONFIG_KEY = 'vefr-packaged-config';
function loadConfig() {
  return store.getJSON(CONFIG_KEY, {});
}
function saveConfig(c) {
  store.setJSON(CONFIG_KEY, c);   // blocked storage: keep going in memory
}
