const test = require('node:test');
const assert = require('node:assert/strict');
const React = require('react');
const {create,act}=require('react-test-renderer');
const ts=require('typescript');
const fs=require('node:fs');
const vm=require('node:vm');
global.IS_REACT_ACT_ENVIRONMENT=true;
const m={exports:{}};
vm.runInNewContext(ts.transpileModule(fs.readFileSync('components/typed-confirmation.tsx','utf8'),{
 compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2020,jsx:ts.JsxEmit.ReactJSX}
}).outputText,{module:m,exports:m.exports,require});
test('confirmation stays disabled for wrong text and enables only exact content',async()=>{
 const values=[];let tree;
 await act(async()=>{tree=create(React.createElement(m.exports.TypedConfirmation,{expected:'APPLY default/api',description:'Apply',onClose:v=>values.push(v)}),{createNodeMock:()=>({showModal(){}})});});
 const button=()=>tree.root.findAllByType('button').find(b=>b.props.type==='submit');
 assert.equal(button().props.disabled,true);
 await act(async()=>tree.root.findByType('input').props.onChange({target:{value:'123'}}));
 assert.equal(button().props.disabled,true);
 await act(async()=>tree.root.findByType('form').props.onSubmit({preventDefault(){}}));
 assert.deepEqual(values,[]);
 await act(async()=>tree.root.findByType('input').props.onChange({target:{value:'APPLY default/api'}}));
 assert.equal(button().props.disabled,false);
 await act(async()=>tree.root.findByType('form').props.onSubmit({preventDefault(){}}));
 assert.deepEqual(values,['APPLY default/api']);
 await act(async()=>tree.unmount());
});
