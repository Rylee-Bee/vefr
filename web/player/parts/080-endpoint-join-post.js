// ---- endpoint join + post ----
// The config URL is player-entered: it may or may not end in /v1 (the
// placeholder shows one), may carry trailing slashes. Join once, here,
// so no caller can ever produce /v1/v1 again.
function chatEndpoint(base) {
  var u = String(base || '').replace(/\/+$/, '');
  if (/\/chat\/completions$/.test(u)) return u;
  if (/\/v1$/.test(u)) return u + '/chat/completions';
  return u + '/v1/chat/completions';
}
// No endpoint configured (offline play) -> reject straight into the
// caller's pool/fragment fallback; never fetch a relative URL.
function llmPost(body) {
  if (!llmUrl || !llmModel) {
    return Promise.reject(new Error('offline - no endpoint set'));
  }
  return fetch(chatEndpoint(llmUrl), {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
}
var config = loadConfig();
var llmUrl = config.llmUrl || '';
var llmModel = config.llmModel || '';
// Games play without a model (docs/adr/0003). A pack may offer one as an
// optional extra ("player": {"model": "optional"}); otherwise any saved
// endpoint is ignored and the baked lines carry the world.
var MODEL_OPTIONAL = !!(window.VEFR_WORLD && window.VEFR_WORLD.player
  && window.VEFR_WORLD.player.model === 'optional');
if (!MODEL_OPTIONAL) { llmUrl = ''; llmModel = ''; }

