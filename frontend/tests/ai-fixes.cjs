const test=require('node:test');
const assert=require('node:assert/strict');
const React=require('react');
const {create,act}=require('react-test-renderer');
const ts=require('typescript');
const fs=require('node:fs');
const vm=require('node:vm');
global.IS_REACT_ACT_ENVIRONMENT=true;
function setup(state,confirmation){
 const calls=[];
 const proposal={id:'p1',state,context:'cluster-a',namespace:'default',deployment:'demo',objective:'Change health path',explanation:'Review',checks:[],evidence:[],evidence_ids:[],audit:[],confirmation:'APPLY cluster-a default/demo p1',rollback_confirmation:'ROLLBACK cluster-a default/demo p1',diff:'- /\n+ /health'};
 const m={exports:{}};
 vm.runInNewContext(ts.transpileModule(fs.readFileSync('components/ai-fix-assistant.tsx','utf8'),{compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2020,jsx:ts.JsxEmit.ReactJSX}}).outputText,{module:m,exports:m.exports,require:id=>{
  if(id==='@/components/diagnostic-checks')return {DiagnosticChecks:()=>null};
  if(id==='@tanstack/react-query')return {useQuery:({queryKey})=>({data:queryKey[0]==="fix-targets" ? [{name:"demo"}] : [proposal]}),useQueryClient:()=>({invalidateQueries:async()=>{}})};
  if(id==='@/lib/api')return {API_BASE_URL:'http://localhost:8000/api',apiFetch:async(...a)=>calls.push(a),errorMessage:String};
  if(id==='@/components/typed-confirmation')return {useTypedConfirmation:()=>({dialog:null,confirm:async()=>confirmation})};
  if(id==='@/lib/datetime')return {formatDateTime:String};
  return require(id);
 }});
 return {Component:m.exports.AiFixAssistant,calls};
}
test('AI apply is unavailable before validation and cancelled approval sends nothing',async()=>{
 for(const state of ['PROPOSED','NEEDS_INFORMATION','OUTCOME_UNKNOWN','APPLIED']){
  const s=setup(state,null);let tree;
  await act(async()=>{tree=create(React.createElement(s.Component,{investigationId:'i1'}))});
  assert.equal(tree.root.findAllByType('button').filter(b=>b.props.children==='Review approval and apply').length,0);
  await act(async()=>tree.unmount());
 }
 const s=setup('VALIDATED',null);let tree;
 await act(async()=>{tree=create(React.createElement(s.Component,{investigationId:'i1'}))});
 await act(async()=>tree.root.findAllByType('button').find(b=>b.props.children==='Review approval and apply').props.onClick());
 assert.equal(s.calls.length,0);
 await act(async()=>tree.unmount());
});
test('AI apply and rollback send only proposal-scoped approval, never client YAML',async()=>{
 for(const [state,label,verb] of [['VALIDATED','Review approval and apply','apply'],['APPLIED','Review rollback approval','rollback']]){
 const s=setup(state,'exact approval');let tree;
 await act(async()=>{tree=create(React.createElement(s.Component,{investigationId:'i1'}))});
 await act(async()=>tree.root.findAllByType('button').find(b=>b.props.children===label).props.onClick());
 assert.equal(s.calls[0][0],`/v1/fixes/p1/${verb}`);
 assert.deepEqual(JSON.parse(s.calls[0][1].body),{confirmation:'exact approval'});
 await act(async()=>tree.unmount());
 }
});
test('assessment is explicit in generation payload and defaults on',async()=>{
 const s=setup('ASSESSMENT',null);let tree;
 await act(async()=>{tree=create(React.createElement(s.Component,{investigationId:'i1'}))});
 await act(async()=>tree.root.findByType('textarea').props.onChange({target:{value:'Assess the evidence without changing anything.'}}));
 assert.equal(tree.root.findByType('input').props.checked,true);
 await act(async()=>tree.root.findAllByType('button').find(b=>b.props.children==='Assess with AI').props.onClick());
 assert.equal(JSON.parse(s.calls[0][1].body).assessment_only,true);
 await act(async()=>tree.unmount());
});
