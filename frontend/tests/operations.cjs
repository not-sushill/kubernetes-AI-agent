const test=require('node:test'),assert=require('node:assert/strict'),fs=require('fs'),vm=require('vm'),ts=require('typescript'),React=require('react'),{act,create}=require('react-test-renderer');
global.IS_REACT_ACT_ENVIRONMENT=true;
function load(path,overrides={},globals={}){const m={exports:{}};vm.runInNewContext(ts.transpileModule(fs.readFileSync(path,'utf8'),{compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2020,jsx:ts.JsxEmit.ReactJSX,esModuleInterop:true}}).outputText,{module:m,exports:m.exports,process:{env:{}},...globals,require:id=>overrides[id]||require(id)});return m.exports;}
test('queue button persists the selected cluster and does not perform an inline investigation',async()=>{
 const calls=[];const {QueueInvestigation}=load('components/queue-investigation.tsx',{'next/link':({children,...p})=>React.createElement('a',p,children),'@/lib/api':{errorMessage:String,apiFetch:async(path,options)=>{calls.push({path,options});return path.endsWith('/contexts')?{current_context:'cluster-a'}:{id:'job'};}}});
 let tree;await act(async()=>{tree=create(React.createElement(QueueInvestigation,{namespace:'default',resourceType:'pod',resourceName:'demo'}));});
 assert.equal(calls.length,0);
 await act(async()=>tree.root.findByType('button').props.onClick());
 assert.equal(calls[1].path,'/v1/operations/jobs');const request=JSON.parse(calls[1].options.body);assert.equal(request.context,'cluster-a');assert.equal(request.resource_name,'demo');
 assert.equal(tree.root.findByType('a').props.href,'/operations');await act(async()=>tree.unmount());
});
test('API access token travels in headers, never the URL',async()=>{
 let sent;const {apiFetch}=load('lib/api.ts',{}, {window:{},sessionStorage:{getItem:()=> 'secret-token'},fetch:async(url,options)=>{sent={url,options};return {ok:true,text:async()=>'{"ok":true}'};}});
 await apiFetch('/v1/operations/jobs');assert.equal(sent.options.headers['X-API-Key'],'secret-token');assert.ok(!sent.url.includes('secret-token'));
});
