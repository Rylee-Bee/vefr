// Executes shipped pure engine and actual woven player; no copied rule logic.
import fs from 'node:fs';
import vm from 'node:vm';
import assert from 'node:assert/strict';
import { JSDOM } from 'jsdom';
const spec = JSON.parse(fs.readFileSync(process.argv[2], 'utf8'));
const html = fs.readFileSync(spec.player, 'utf8');
const ctx = { window: {} }; vm.createContext(ctx);
vm.runInContext(html.slice(html.indexOf('// -- rules start --'), html.indexOf('// -- rules end --')), ctx);
const E = ctx.window.VEFR_RULES_ENGINE;
const clean = v => JSON.parse(JSON.stringify(v));
const traces = [];
for (const ready of [false, true]) {
  const states = spec.packs.map(p => E.newState(p));
  states.forEach(s => { s.flags[spec.condition] = ready; });
  for (const [event, data] of [['opens', {what:'unrelated'}], [spec.event, spec.data], [spec.event, spec.data]]) {
    const results = states.map(s => clean(E.run(s, event, data)));
    assert.deepEqual(results[0], results[1]);
    assert.deepEqual(clean(states[0].flags), clean(states[1].flags));
    assert.deepEqual(clean(states[0].fired), clean(states[1].fired));
    if (event === 'opens' || !ready) assert.equal(results[0].fired.length, 0);
    traces.push({ready, event, result:results[0], flags:clean(states[0].flags), once:clean(states[0].fired)});
  }
}
const triggered = traces.find(t => t.result.fired.length);
assert.deepEqual(triggered.result.actions.map(a=>Object.keys(a)[0]), ['set','say']);
assert.equal(triggered.flags[spec.resultFlag], true);
assert.equal(traces.at(-1).result.fired.length, 0);
assert.ok(triggered.result.fired[0].why.includes(spec.ruleId));
// Separate synthetic adversary: giving an item must not invoke a picks-up rule.
const chain = E.newState({flags:{chained:''}, rules:[
  {id:'give',when:{starts:{}},then:[{give:'token'}]},
  {id:'receive',when:{'picks-up':{what:'token'}},then:[{set:'chained'}]}
]});
assert.equal(E.run(chain,'starts',{}).fired.length,1);
assert.equal(chain.flags.chained,false);
const unknown = E.newState({rules:[{id:'bad',when:{starts:{}},then:[{'teleport-through-time':{}}]}]});
const unknownResult = clean(E.run(unknown,'starts',{}));
assert.equal(unknownResult.fired.length,0);
const noop=()=>{};
async function player(pack, storage={}, replay=true) {
  const dom = new JSDOM(html,{runScripts:'dangerously',pretendToBeVisual:true,url:'http://localhost/',beforeParse:w=>{
    w.HTMLCanvasElement.prototype.getContext=function(){return new Proxy({canvas:this},{get:(t,k)=>k in t?t[k]:noop});};
    w.matchMedia=()=>({matches:false,addListener:noop,removeListener:noop});
    for(const [k,v] of Object.entries(storage)) w.localStorage.setItem(k,v);
  }});
  const w=dom.window;
  await new Promise(r=>w.setTimeout(r,100));
  w.VEFR_RULES=pack.rules; w.VEFR_FLAGS=pack.flags;
  w.document.getElementById('ts-enter').click();
  await new Promise(r=>w.setTimeout(r,100));
  w.fireRule('opens',{what:'unrelated'});
  const initial=clean({flags:w.VEFR_RULES_STATE.flags,fired:w.VEFR_RULES_STATE.fired});
  w.rulesWhyLoad();
  const restoredWhy=clean(w.VEFR_WHY||[]);
  if(replay){
    w.VEFR_RULES_STATE.flags[spec.condition]=true;
    w.fireRule(spec.event,spec.data);
    w.fireRule(spec.event,spec.data);
  }
  const out=clean({initial,restoredWhy,flags:w.VEFR_RULES_STATE.flags,fired:w.VEFR_RULES_STATE.fired,
    speech:w.document.getElementById('npc-line').textContent,why:w.VEFR_WHY,
    storage:Object.fromEntries(Array.from({length:w.localStorage.length},(_,i)=>{const k=w.localStorage.key(i);return [k,w.localStorage.getItem(k)];}))});
  w.close(); return out;
}
const played=await Promise.all(spec.packs.map(p=>player(p)));
assert.deepEqual(played[0],played[1]);
assert.equal(played[0].speech,spec.line);
const reload=await Promise.all(spec.packs.map((p,i)=>player(p,played[i].storage,false)));
assert.deepEqual(reload[0],reload[1]);
assert.equal(reload[0].flags[spec.condition],false);
assert.equal(reload[0].flags[spec.resultFlag],false);
assert.deepEqual(reload[0].fired,{});
assert.deepEqual(reload[0].restoredWhy,played[0].why);
fs.writeSync(1,JSON.stringify({comparison:'identical',traces,nonchaining:true,unknownRuntime:unknownResult,
  player:played[0],reload:reload[0],reloadLimitation:'flags and once markers reset; why survives'})+'\n');
