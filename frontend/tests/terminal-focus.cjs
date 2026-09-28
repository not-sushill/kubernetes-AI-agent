const test=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
const ts=require('typescript');
const React=require('react');
const {create,act}=require('react-test-renderer');
global.IS_REACT_ACT_ENVIRONMENT=true;
test('terminal enables input after connection and click restores focus',async()=>{
 let instance,ready=0,received=[];
 class Terminal {
  constructor(options){this.options=options;this.rows=24;this.cols=80;this.focusCount=0;instance=this;}
  loadAddon(){} open(){} write(){} reset(){} dispose(){} focus(){this.focusCount++;}
  onData(fn){this.data=fn;return {dispose(){}};} onResize(){return {dispose(){}};}
  attachCustomKeyEventHandler(){}
 }
 const m={exports:{}};
 vm.runInNewContext(ts.transpileModule(fs.readFileSync('components/terminal-view.tsx','utf8'),{
  compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2020,jsx:ts.JsxEmit.ReactJSX}
 }).outputText,{module:m,exports:m.exports,ResizeObserver:class{observe(){}disconnect(){}},require:name=>{
  if(name==='@xterm/xterm')return {Terminal};
  if(name==='@xterm/addon-fit')return {FitAddon:class{fit(){}}};
  if(name.endsWith('.css'))return {};
  return require(name);
 }});
 const props={onInput:value=>received.push(value),onResize(){},onReady(){ready++;},onError:e=>{throw Error(e);}};
 let tree;
 await act(async()=>{tree=create(React.createElement(m.exports.TerminalView,{...props,enabled:false}),{createNodeMock:()=>({clientWidth:800,focus(){}})});});
 assert.equal(ready,1);assert.equal(instance.options.disableStdin,true);
 await act(async()=>tree.update(React.createElement(m.exports.TerminalView,{...props,enabled:true})));
 assert.equal(instance.options.disableStdin,false);assert.ok(instance.focusCount>0);
 instance.options.disableStdin=true;
 await act(async()=>tree.root.findByType('div').props.onPointerUp());
 assert.equal(instance.options.disableStdin,false);
 instance.data('pwd\r\t\x03');assert.deepEqual(received,['pwd\r\t\x03']);
 await act(async()=>tree.unmount());
});
