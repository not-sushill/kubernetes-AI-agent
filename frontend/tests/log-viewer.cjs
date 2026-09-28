const test=require('node:test'),assert=require('node:assert/strict'),React=require('react'),{create,act}=require('react-test-renderer'),ts=require('typescript'),fs=require('fs'),vm=require('vm');
global.IS_REACT_ACT_ENVIRONMENT=true;
function compile(path,req){const m={exports:{}};vm.runInNewContext(ts.transpileModule(fs.readFileSync(path,'utf8'),{compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2020,jsx:ts.JsxEmit.ReactJSX}}).outputText,{module:m,exports:m.exports,require:req});return m.exports;}
const helpers=compile('lib/log-search.ts',require);
const {PodLogViewer}=compile('components/pod-log-viewer.tsx',id=>id==='@/lib/log-search'?helpers:id==='@/lib/api'?{errorMessage:String}:id==='@/lib/datetime'?{formatDateTime:String}:require(id));
function contents(node){if(typeof node==='string')return node;return (node.children||[]).map(contents).join('');}
test('normal logs remain visible with highlights; filtering and reset are explicit',async()=>{
 let tree;await act(async()=>{tree=create(React.createElement(PodLogViewer,{options:{tail:5000,since:'24h'},onLoad(){},loading:false,error:null,data:{logs:['normal message','ERROR [id]','recovered'],line_count:3}}));});
 const pre=()=>tree.root.findByProps({'aria-label':'Pod log contents'});
 assert.match(contents(pre()),/normal message/);
 await act(async()=>tree.root.findByProps({'aria-label':'Search fetched logs'}).props.onChange({target:{value:'[id]'}}));
 assert.match(contents(pre()),/normal message/);assert.equal(tree.root.findAllByType('mark').length,1);
 const label=tree.root.findAllByType('label').find(n=>contents(n).includes('Show matching lines only'));
 await act(async()=>label.findByType('input').props.onChange({target:{checked:true}}));
 await act(async()=>tree.root.findAllByType('select').find(n=>n.props.value===2).props.onChange({target:{value:'0'}}));
 assert.doesNotMatch(contents(pre()),/normal message/);
 await act(async()=>tree.root.findAllByType('button').find(n=>contents(n)==='Show all fetched logs').props.onClick());
 assert.match(contents(pre()),/normal message/);assert.match(contents(pre()),/recovered/);
 await act(async()=>tree.unmount());
});
test('large responses render bounded pages without losing later logs',async()=>{
 let tree;await act(async()=>{tree=create(React.createElement(PodLogViewer,{options:{tail:5000},onLoad(){},loading:false,error:null,data:{logs:Array.from({length:1001},(_,i)=>'line-'+i),line_count:1001}}));});
 const pre=()=>contents(tree.root.findByProps({'aria-label':'Pod log contents'}));
 assert.match(pre(),/line-499/);assert.doesNotMatch(pre(),/line-500/);
 await act(async()=>tree.root.findAllByType('button').find(n=>contents(n)==='Next page').props.onClick());
 assert.match(pre(),/line-500/);assert.match(pre(),/line-999/);
 await act(async()=>tree.unmount());
});
test('log surface has an explicit color scope and wrapping preserves text',async()=>{
 let tree;await act(async()=>{tree=create(React.createElement(PodLogViewer,{options:{tail:5000},onLoad(){},loading:false,error:null,data:{logs:['INFO visible log'],line_count:1}}));});
 const pre=()=>tree.root.findByProps({'aria-label':'Pod log contents'});
 assert.match(pre().props.className,/log-content/);
 const wrap=tree.root.findAllByType('label').find(n=>contents(n).includes('Wrap lines'));
 await act(async()=>wrap.findByType('input').props.onChange({target:{checked:true}}));
 assert.match(pre().props.className,/log-wrap/);assert.match(contents(pre()),/INFO visible log/);
 await act(async()=>tree.unmount());
});
