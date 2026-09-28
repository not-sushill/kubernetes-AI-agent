const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const ts = require('typescript');
const React = require('react');
const {create, act} = require('react-test-renderer');
global.IS_REACT_ACT_ENVIRONMENT = true;
function setup({defer = false, approve = true} = {}) {
 const requests = [], sockets = [], approvals = [];
 let finish;
 class Socket {
  static OPEN = 1;
  constructor(url) {this.url=url;this.sent=[];this.readyState=1;sockets.push(this);}
  send(data) {this.sent.push(JSON.parse(data));}
  close() {this.closed=true;this.onclose?.();}
 }
 const api = {API_BASE_URL:'http://localhost:8000/api', responseErrorMessage:()=>null,
  apiFetch:async(path, options)=>{
   requests.push({path,options});
   if(path.endsWith('/terminal')) return defer ? new Promise(resolve=>{finish=resolve;}) : {ticket:'one-use'};
   return {context:'cluster-a', namespace:'default',pod:'api',uid:'uid-a',containers:[{name:'app',running:true},{name:'sidecar',running:true}]};
  }};
 const TerminalStub=React.forwardRef(function TerminalStub(props,ref){
  React.useImperativeHandle(ref,()=>({write(){},clear(){},focus(){},size:()=>({rows:24,cols:80})}),[]);
  React.useEffect(()=>{props.onReady();},[]);
  return React.createElement('div',{'data-terminal':true,onInput:props.onInput,onResize:props.onResize});
 });
 const m={exports:{}};
 vm.runInNewContext(ts.transpileModule(fs.readFileSync('components/container-access.tsx','utf8'),{
  compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2020,jsx:ts.JsxEmit.ReactJSX}
 }).outputText,{module:m,exports:m.exports,URL,AbortController,WebSocket:Socket,setTimeout,
  window:{location:{href:'http://localhost:3000/pods'}},
  require:name=>name==='@/components/terminal-view'?{TerminalView:TerminalStub}:name==='@/lib/api'?api:name==='@/components/typed-confirmation'?{useTypedConfirmation:()=>({dialog:null,confirm:async expected=>{approvals.push(expected);return approve?expected:null;}})}:require(name)});
 return {Component:m.exports.ContainerAccess,requests,sockets,approvals,resolve:()=>finish({ticket:'late'})};
}
const button=(tree,name)=>tree.root.findAllByType('button').find(b=>b.children.join('')===name);
test('terminal targets selected container, streams input, and closes on unmount',async()=>{
 const x=setup();let tree;
 await act(async()=>{tree=create(React.createElement(x.Component,{namespace:'default',pod:'api'}));});
 await act(async()=>tree.root.findByProps({'aria-label':'Container'}).props.onChange({target:{value:'sidecar'}}));
 await act(async()=>button(tree,'Open terminal').props.onClick());
 assert.equal(x.approvals[0],'EXEC cluster-a default/api/sidecar');
 const payload=JSON.parse(x.requests[1].options.body);
 assert.equal(payload.container,'sidecar');assert.equal(payload.context,'cluster-a');assert.equal(payload.uid,'uid-a');
 const ws=x.sockets[0];assert.equal(ws.url.protocol,'ws:');
 await act(async()=>{ws.onopen();ws.onmessage({data:JSON.stringify({type:'ready'})});});
 assert.equal(ws.sent[0].ticket,'one-use');
 const raw='cd /tmp/\t\t\x1b[A\x03';
 await act(async()=>tree.root.findByProps({'data-terminal':true}).props.onInput(raw));
 assert.equal(ws.sent[1].data,raw);
 await act(async()=>tree.root.findByProps({'data-terminal':true}).props.onResize(40,120));
 assert.equal(ws.sent[2].type,'resize');assert.equal(ws.sent[2].cols,120);
 await act(async()=>tree.unmount());assert.equal(ws.closed,true);
});
test('cancelled terminal approval makes no session request',async()=>{
 const x=setup({approve:false});let tree;
 await act(async()=>{tree=create(React.createElement(x.Component,{namespace:'default',pod:'api'}));});
 await act(async()=>button(tree,'Open terminal').props.onClick());
 assert.equal(x.requests.length,1);assert.equal(x.sockets.length,0);
 await act(async()=>tree.unmount());
});
test('disconnect during ticket creation cannot open a late connection',async()=>{
 const x=setup({defer:true});let tree;
 await act(async()=>{tree=create(React.createElement(x.Component,{namespace:'default',pod:'api'}));});
 let pending;
 await act(async()=>{pending=button(tree,'Open terminal').props.onClick();await Promise.resolve();});
 await act(async()=>button(tree,'Disconnect').props.onClick());
 await act(async()=>{x.resolve();await pending;});
 assert.equal(x.sockets.length,0);
 await act(async()=>tree.unmount());
});
