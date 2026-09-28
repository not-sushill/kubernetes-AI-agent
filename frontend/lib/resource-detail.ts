import type {ServiceDetail, IngressDetail, NodeDetail, NodeCondition, EventSummary} from "@/hooks/use-kubernetes";
type Obj = Record<string, unknown>;
const obj = (v: unknown): Obj => v && typeof v === "object" && !Array.isArray(v) ? v as Obj : {};
const list = (v: unknown): unknown[] => Array.isArray(v) ? v : [];
const text = (v: unknown): string => typeof v === "string" || typeof v === "number" ? String(v) : "";
const strings = (v: unknown): Record<string,string> => Object.fromEntries(Object.entries(obj(v)).map(([k,v])=>[k,text(v)]));
function resource(value: unknown): Obj {
  const root=obj(value), data=obj(root.data);
  const r = Object.keys(data).length ? data : root;
  if (!text(r.name) && !text(obj(r.metadata).name)) throw new Error("Backend returned an unrecognized resource detail response.");
  return r;
}
export function normalizeService(value: unknown): ServiceDetail {
 const r=resource(value), m=obj(r.metadata), s=obj(r.spec);
 const ports=list(r.ports ?? s.ports).map(value=>{
   const p=obj(value);
   return {name:text(p.name),port:Number(p.port),target_port:(p.target_port ?? p.targetPort ?? p.port) as string|number,protocol:text(p.protocol)||"TCP"};
 });
 const lb=list(obj(obj(r.status).loadBalancer).ingress).map(v=>text(obj(v).ip??obj(v).hostname)).filter(Boolean);
 return {name:text(r.name??m.name),namespace:text(r.namespace??m.namespace),type:text(r.type??s.type),
 cluster_ip:text(r.cluster_ip??s.clusterIP),external_ip:text(r.external_ip)||lb.join(", ")||list(s.externalIPs).map(text).join(", "),
 ports,selector:strings(r.selector??s.selector),labels:strings(r.labels??m.labels),annotations:strings(r.annotations??m.annotations),age:text(r.age??m.creationTimestamp)};
}
export function normalizeIngress(value: unknown): IngressDetail {
 const r=resource(value),m=obj(r.metadata),s=obj(r.spec);
 const rules=Array.isArray(r.rules)?r.rules.map(v=>{const a=obj(v);return {host:text(a.host),path:text(a.path),service:text(a.service),port:(a.port??"") as string|number};}):
 list(s.rules).flatMap(v=>{const rule=obj(v);return list(obj(rule.http).paths).map(v=>{
 const p=obj(v),backend=obj(p.backend),service=obj(backend.service),port=obj(service.port);
 return {host:text(rule.host),path:text(p.path)||"/",service:text(service.name??backend.serviceName),port:(port.number??port.name??backend.servicePort??"") as string|number};
 });});
 return {name:text(r.name??m.name),namespace:text(r.namespace??m.namespace),ingress_class:text(r.ingress_class??s.ingressClassName??obj(m.annotations)["kubernetes.io/ingress.class"]),
 address:text(r.address)||list(obj(obj(r.status).loadBalancer).ingress).map(v=>text(obj(v).ip??obj(v).hostname)).join(", "),
 rules,tls:list(r.tls??s.tls).map(v=>{const t=obj(v);return {hosts:list(t.hosts).map(text),secret_name:text(t.secret_name??t.secretName)};}),
 labels:strings(r.labels??m.labels),annotations:strings(r.annotations??m.annotations)};
}
export function normalizeNode(value: unknown): NodeDetail {
 const r=resource(value),m=obj(r.metadata),s=obj(r.spec),status=obj(r.status),info=obj(status.nodeInfo),metrics=obj(r.metrics);
 const conditions=list(r.conditions??status.conditions) as NodeCondition[];
 const ready=conditions.find(c=>c.type==="Ready");
 return {name:text(r.name??m.name),status:typeof r.status==="string"?r.status:ready?.status??"Unknown",
 roles:text(r.roles)||"unknown",version:text(r.version??info.kubeletVersion),
 internal_ip:text(r.internal_ip)||text(obj(list(status.addresses).find(v=>obj(v).type==="InternalIP")).address),
 os_image:text(r.os_image??info.osImage),kernel_version:text(r.kernel_version??info.kernelVersion),
 container_runtime:text(r.container_runtime??info.containerRuntimeVersion),age:text(r.age??m.creationTimestamp),
 labels:strings(r.labels??m.labels),annotations:strings(r.annotations??m.annotations),capacity:strings(r.capacity??status.capacity),
 allocatable:strings(r.allocatable??status.allocatable),conditions,provider_id:text(r.provider_id??s.providerID),pod_cidr:text(r.pod_cidr??s.podCIDR),
 unschedulable:Boolean(r.unschedulable??s.unschedulable),metrics:{available:metrics.available===true,cpu:text(metrics.cpu)||null,memory:text(metrics.memory)||null},
 health_score:typeof r.health_score==="number"?r.health_score:null,yaml:text(r.yaml),events:list(r.events) as EventSummary[]};
}
