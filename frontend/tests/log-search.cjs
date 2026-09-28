const test=require('node:test');const assert=require('node:assert/strict');const ts=require('typescript');const fs=require('node:fs');const vm=require('node:vm');
const m={exports:{}};vm.runInNewContext(ts.transpileModule(fs.readFileSync('lib/log-search.ts','utf8'),{compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2020}}).outputText,{module:m,exports:m.exports,require,Date,Set});
const {istLogStart,searchLogs}=m.exports;
test('IST log start becomes UTC independent of browser timezone',()=>{
 assert.equal(istLogStart('2026-09-25T04:00'),'2026-09-24T22:30:00.000Z');
 assert.throws(()=>istLogStart('2026-02-30T04:00'));assert.throws(()=>istLogStart('garbage'));
});
test('literal search supports case filtering and deduplicated context',()=>{
 const lines=['ready','ERROR request [id]','stack1','error second','recovered'];
 const r=searchLogs(lines,'error',false,false,1);
 assert.equal(r.matches.length,2);assert.equal(r.rows.length,5);
 assert.equal(searchLogs(lines,'[id]',false,false,0).rows.length,1);
 assert.equal(searchLogs(lines,'ERROR',false,true,0).rows.length,1);
 assert.equal(searchLogs(lines,'missing',false,false,2).rows.length,0);
 assert.equal(searchLogs(lines,'',true,false,0).rows.length,2);
});
test('switching pods clears previous-instance, container and custom-time filters',()=>{
 const stored={target:'kafka/pod-a',options:{tail:100000,previous:true,container:'kafka-container',since_time:'2026-09-25T03:00:00Z'}};
 const next=m.exports.logOptionsForTarget('sim/pod-b',stored);
 assert.equal(next.previous,false);assert.equal(next.container,undefined);assert.equal(next.since_time,undefined);assert.equal(next.since,undefined);
 assert.equal(m.exports.logOptionsForTarget('kafka/pod-a',stored),stored.options);
});
