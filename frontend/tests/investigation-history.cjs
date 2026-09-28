const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");
const ts = require("typescript");

test("inline pod investigation persists, adapts evidence and invalidates history", async () => {
  let mutationOptions;
  const calls = [];
  const cache = [];
  const saved = {
    id: "saved-123",
    evidence: {
      pod: {data: {name: "api"}},
      events: {data: {events: [{reason: "Unhealthy"}]}},
      logs: {data: {pods: {api: {
        containers: {app: {logs: ["first", "second"]}},
        previous: {app: {logs: ["previous"]}}
      }}}}
    },
    analysis: {diagnostics: [{title: "issue"}], root_causes: [{title: "cause"}]}
  };
  const compiled = ts.transpileModule(
    fs.readFileSync("hooks/use-kubernetes.ts", "utf8"),
    {compilerOptions: {module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2020}}
  ).outputText;
  const module = {exports: {}};
  vm.runInNewContext(compiled, {
    exports: module.exports, module, URLSearchParams,
    require: name => {
      if (name === "@tanstack/react-query") return {
        useMutation: options => { mutationOptions = options; return {isPending: false}; },
        useQuery: () => {throw Error("Investigation must not use automatic query execution");},
        useQueryClient: () => ({
          setQueryData: (...args) => cache.push(["set", ...args]),
          invalidateQueries: async options => cache.push(["invalidate", options])
        })
      };
      if (name === "@/lib/resource-detail") return {};
      if (name === "@/lib/api") return {
        apiFetch: async (...args) => {calls.push(args);return saved;}
      };
      throw Error(name);
    }
  });
  module.exports.usePodInvestigation({namespace: "default", name: "api"});
  assert.equal(calls.length, 0, "render must not create an investigation");
  const result = await mutationOptions.mutationFn({namespace: "default", name: "api"});
  assert.equal(calls.length, 1);
  assert.equal(calls[0][0], "/v1/investigations");
  assert.equal(calls[0][1].method, "POST");
  assert.deepEqual(JSON.parse(calls[0][1].body), {
    namespace: "default", resource_type: "pod", resource_name: "api",
    log_tail: 100, include_previous_logs: true
  });
  assert.equal(result.id, "saved-123");
  assert.equal(result.logs.current.app, "first\nsecond");
  assert.equal(result.logs.previous.app, "previous");
  assert.equal(result.events[0].reason, "Unhealthy");
  assert.equal(result.diagnostics.issue_count, 1);
  assert.equal(cache[0][1][1], "saved-123");
  assert.equal(cache[1][1].queryKey[0], "investigations");
  assert.equal(mutationOptions.retry, false);
});

test("sidebar destinations are unique", () => {
  const source = fs.readFileSync("components/layout/app-shell.tsx", "utf8");
  const nav = source.split("const navItems = [")[1].split("];")[0];
  const routes = [...nav.matchAll(/href:\s*"([^"]+)"/g)].map(match => match[1]);
  assert.ok(routes.includes("/services"));
  assert.equal(new Set(routes).size, routes.length);
});
