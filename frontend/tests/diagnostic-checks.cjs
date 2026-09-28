const test=require('node:test'),assert=require('node:assert/strict'),React=require('react'),{create,act}=require('react-test-renderer'),ts=require('typescript'),fs=require('fs'),vm=require('vm');
global.IS_REACT_ACT_ENVIRONMENT=true;
test('diagnostics preview does not execute; explicit run submits a fixed check ID only',async()=>{
 const calls=[];let reassessed=false;const m={exports:{}};
 vm.runInNewContext(ts.transpileModule(fs.readFileSync('components/diagnostic-checks.tsx','utf8'),{compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2020,jsx:ts.JsxEmit.ReactJSX}}).outputText,{module:m,exports:m.exports,require:id=>{
  if(id==='@tanstack/react-query')return {useQuery:({queryKey})=>({data:queryKey[0]==='diagnostic-checks'?[{id:'pod_status',title:'Owned pods',purpose:'Read-only',commands:[['kubectl','--context','cluster-a','get','pods']]}]:[{id:'r1',title:'Owned pods',state:'COMPLETED',output:'Running',started_at:'2026-09-25T00:00:00Z',executed_commands:[]}]}),useQueryClient:()=>({invalidateQueries:async()=>{}})};
  if(id==='@/lib/api')return {apiFetch:async(...args)=>calls.push(args),errorMessage:String};
  if(id==='@/lib/datetime')return {formatDateTime:String};return require(id);
 }});
 let tree;await act(async()=>{tree=create(React.createElement(m.exports.DiagnosticChecks,{proposalId:'p1',disabled:false,hasInheritedResults:false,onPrepareFix(){},onReassess:async()=>{reassessed=true;}}))});
 assert.equal(calls.length,0);
 const button=text=>tree.root.findAllByType('button').find(n=>n.props.children===text);
 await act(async()=>button('Run read-only check').props.onClick());
 assert.equal(calls[0][0],'/v1/fixes/p1/diagnostic-runs');
 assert.deepEqual(JSON.parse(calls[0][1].body),{check_id:'pod_status'});
 await act(async()=>button('Reassess with check results').props.onClick());assert.equal(reassessed,true);
 await act(async()=>tree.unmount());
});
