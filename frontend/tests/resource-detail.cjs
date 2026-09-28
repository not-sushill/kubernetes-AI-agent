const test = require("node:test");
const assert = require("node:assert/strict");
const vm = require("node:vm");
const fs = require("node:fs");
const ts = require("typescript");
const moduleObject = {exports:{}};
vm.runInNewContext(ts.transpileModule(fs.readFileSync("lib/resource-detail.ts","utf8"),{
 compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2020}
}).outputText,{module:moduleObject,exports:moduleObject.exports});
const {normalizeService,normalizeIngress,normalizeNode}=moduleObject.exports;
test("raw Kubernetes Service maps ports and named targets",()=>{
 const r=normalizeService({metadata:{name:"api",namespace:"default",labels:{app:"api"}},spec:{
 type:"ClusterIP",clusterIP:"10.0.0.1",ports:[{port:80,targetPort:"http",protocol:"TCP"}],selector:{app:"api"}}});
 assert.equal(r.ports.length,1);assert.equal(r.ports[0].target_port,"http");
 assert.equal(r.cluster_ip,"10.0.0.1");assert.equal(r.labels.app,"api");
});
test("raw Ingress maps nested paths, TLS and missing optional fields",()=>{
 const r=normalizeIngress({metadata:{name:"web"},spec:{rules:[{host:"example.test",http:{paths:[
 {path:"/",backend:{service:{name:"api",port:{number:80}}}}]}}]}});
 assert.equal(r.rules[0].service,"api");assert.equal(r.rules[0].port,80);
 assert.equal(r.tls.length,0);
});
test("flat and wrapped responses remain compatible",()=>{
 assert.equal(normalizeService({data:{name:"api",ports:[{port:443,target_port:8443}]}}).ports[0].target_port,8443);
 assert.equal(normalizeIngress({name:"web",rules:[{host:"h",path:"/",service:"api",port:"http"}],tls:[{hosts:["h"],secret_name:"tls"}]}).tls[0].secret_name,"tls");
});
test("missing Node enrichment is unavailable, not a fake health score",()=>{
 const r=normalizeNode({name:"node-a",status:"True"});
 assert.equal(r.conditions.length,0);assert.equal(r.events.length,0);
 assert.equal(r.metrics.available,false);assert.equal(r.health_score,null);
});
test("invalid detail payload raises a readable error",()=>{
 assert.throws(()=>normalizeIngress({detail:"unexpected"}),/unrecognized resource/);
});
