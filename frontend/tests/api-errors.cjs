const test = require('node:test');
const assert = require('node:assert/strict');
const vm = require('node:vm');
const fs = require('node:fs');
const ts = require('typescript');
const m = {exports:{}};
vm.runInNewContext(ts.transpileModule(fs.readFileSync('lib/api.ts','utf8'), {
 compilerOptions: {module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2020}
}).outputText,{module:m,exports:m.exports,process:{env:{}},fetch:async()=>({ok:false,status:500,statusText:'Internal Server Error',text:async()=>JSON.stringify({detail:'Apply failed: test failure'})})});
test('API rejection preserves backend detail for mutation and resource UI',async()=>{
 await assert.rejects(m.exports.apiFetch('/test'), error=>{
  assert.equal(error.message,'Apply failed: test failure');
  assert.equal(m.exports.errorMessage(error),'Apply failed: test failure');
  return true;
 });
});
