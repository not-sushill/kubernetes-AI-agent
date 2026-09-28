const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");
const ts = require("typescript");
const React = require("react");
const {act, create} = require("react-test-renderer");
global.IS_REACT_ACT_ENVIRONMENT = true;
function load(path, overrides = {}) {
  const output = ts.transpileModule(fs.readFileSync(path,"utf8"), {
    compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2020,jsx:ts.JsxEmit.ReactJSX,esModuleInterop:true}
  }).outputText;
  const module = {exports:{}};
  vm.runInNewContext(output,{module,exports:module.exports,URLSearchParams,Intl,Date,
    require:name=>Object.hasOwn(overrides,name)?overrides[name]:require(name)});
  return module.exports;
}
test("IST display handles UTC without offset, explicit UTC and existing IST offsets",()=>{
 const d=load("lib/datetime.ts");
 assert.equal(d.formatDateTime("2026-09-23T05:00:00"),d.formatDateTime("2026-09-23T05:00:00Z"));
 assert.equal(d.formatDateTime("2026-09-23T10:30:00+05:30"),d.formatDateTime("2026-09-23T05:00:00Z"));
 assert.match(d.formatDateTime("2026-09-23T05:00:00Z"),/10:30:00.*IST/);
 assert.equal(d.formatAge("3d"),"3d");
});
test("sorts numeric restarts and durations rather than lexical order",()=>{
 const {compareTableValues:compare}=load("lib/table-sort.ts");
 assert.ok(compare("12","2")>0);
 assert.ok(compare("2h","1d")<0);
 assert.ok(compare("Pending","Running")<0);
 assert.ok(compare("2026-09-22T12:00:00Z","2026-09-23T01:00:00Z")<0);
});
test("table headers sort rows ascending and descending",async()=>{
 const sort=load("lib/table-sort.ts");
 const {Table}=load("components/ui/table.tsx",{"@/lib/table-sort":sort,"@/lib/utils":{cn:(...v)=>v.filter(Boolean).join(" ")}});
 let tree;
 await act(async()=>{tree=create(React.createElement(Table,null,
   React.createElement("thead",null,React.createElement("tr",null,React.createElement("th",null,"Restarts"))),
   React.createElement("tbody",null,...[12,2,30].map(n=>React.createElement("tr",{key:n},React.createElement("td",null,n))))
 ))});
 await act(async()=>tree.root.findByType("button").props.onClick());
 assert.deepEqual(tree.root.findAllByType("td").map(n=>n.children.join("")),["2","12","30"]);
 await act(async()=>tree.root.findByType("button").props.onClick());
 assert.deepEqual(tree.root.findAllByType("td").map(n=>n.children.join("")),["30","12","2"]);
 await act(async()=>tree.unmount());
});
test("pod investigation remains pending across page unmount and returns saved result",async()=>{
 const query=require("@tanstack/react-query");
 let resolve,requests=0;
 const response=new Promise(r=>resolve=r);
 const hooks=load("hooks/use-kubernetes.ts",{"@/lib/resource-detail":load("lib/resource-detail.ts"),"@/lib/api":{apiFetch:()=>{requests++;return response}}});
 const state=load("components/pod-investigation-provider.tsx",{"@/hooks/use-kubernetes":hooks});
 const client=new query.QueryClient({defaultOptions:{queries:{retry:false}}});
 let observed;
 function Page(){observed=state.usePodInvestigationState();return null;}
 const shell=show=>React.createElement(query.QueryClientProvider,{client},
   React.createElement(state.PodInvestigationProvider,null,show?React.createElement(Page):null));
 let tree;
 await act(async()=>{tree=create(shell(true))});
 const pod={name:"api",namespace:"default"};
 await act(async()=>{
   observed.setSelectedPod(pod);observed.setInvestigationEnabled(true);observed.investigation.run(pod);
   await new Promise(r=>setTimeout(r,10));
 });
 await act(async()=>{tree.update(shell(false))});
 await act(async()=>{tree.update(shell(true))});
 assert.equal(observed.investigation.isFetching,true);
 assert.equal(observed.selectedPod.name,"api");
 assert.equal(requests,1);
 await act(async()=>{tree.update(shell(false))});
 await act(async()=>{
   resolve({id:"persisted",evidence:{pod:{data:{}},events:{data:{}},logs:{data:{}}},analysis:{diagnostics:[],root_causes:[]}});
   await new Promise(r=>setTimeout(r,20));
 });
 await act(async()=>{tree.update(shell(true))});
 assert.equal(observed.investigation.isFetching,false);
 assert.equal(observed.investigation.data.id,"persisted");
 assert.equal(requests,1);
 await act(async()=>tree.unmount());
 client.clear();
});
test("pagination sorts the full dataset and resets on size or filtered rows",async()=>{
 const {Table}=load("components/ui/table.tsx",{"@/lib/table-sort":load("lib/table-sort.ts"),"@/lib/utils":{cn:(...v)=>v.filter(Boolean).join(" ")}});
 const render=values=>React.createElement(Table,{paginate:true},React.createElement("thead",null,React.createElement("tr",null,React.createElement("th",null,"Restarts"))),React.createElement("tbody",null,...values.map(n=>React.createElement("tr",{key:n},React.createElement("td",null,n)))));
 let tree;const values=Array.from({length:23},(_,i)=>23-i);
 await act(async()=>{tree=create(render(values));});
 const cells=()=>tree.root.findAllByType('td').map(n=>Number(n.children.join('')));
 const button=text=>tree.root.findAllByType('button').find(n=>n.children.join('')===text);
 assert.equal(cells().length,10);
 await act(async()=>tree.root.findByProps({title:'Sort by Restarts'}).props.onClick());
 assert.deepEqual(cells(),[1,2,3,4,5,6,7,8,9,10]);
 await act(async()=>button('Next').props.onClick());assert.equal(cells()[0],11);
 await act(async()=>button('Next').props.onClick());assert.deepEqual(cells(),[21,22,23]);assert.equal(button('Next').props.disabled,true);
 await act(async()=>tree.root.findByProps({'aria-label':'Rows per page'}).props.onChange({target:{value:'5'}}));assert.deepEqual(cells(),[1,2,3,4,5]);
 await act(async()=>button('Next').props.onClick());
 await act(async()=>tree.update(render([100,101,102])));assert.deepEqual(cells(),[100,101,102]);assert.equal(button('Previous').props.disabled,true);
 await act(async()=>tree.unmount());
});
