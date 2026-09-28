"use client";

import {
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";

import { normalizeService, normalizeIngress, normalizeNode } from "@/lib/resource-detail";

import { apiFetch } from "@/lib/api";

/* =========================================================
   HEALTH
========================================================= */

export type BackendHealth = {
  status: string;
  application: string;
  version: string;
  environment: string;
  timestamp: string;
};

export type ClusterHealth = {
  connected: boolean;
  current_context: string;
  kubectl_version: string;
  server_version: string;
  latency_ms: number;
};

/* =========================================================
   NAMESPACES
========================================================= */

export type NamespaceSummary = {
  name: string;
  status: string;
  age: string;
};

/* =========================================================
   KUBERNETES CONTEXTS
========================================================= */

export type KubernetesContexts = {
  contexts: string[];
  current_context: string;
};

export type ContextSwitchRequest = {
  context: string;
};

export type ContextSwitchResponse = {
  success: boolean;
  message: string;
  current_context: string;
};

/* =========================================================
   PODS
========================================================= */

export type PodSummary = {
  namespace: string;
  name: string;
  status: string;
  ready: string;
  restarts: number;
  node: string;
  pod_ip: string;
  age: string;
};

export type PodLogs = {
  pod: string;
  namespace: string;
  container?: string | null;
  previous?: boolean;
  available?: boolean;
  line_count: number;
  logs: string[];
  message?: string;
};

/* =========================================================
   EVENTS
========================================================= */

export type EventSummary = {
  type: string;
  reason: string;
  message: string;
  count: number;
  first_timestamp: string;
  last_timestamp: string;
};

/* =========================================================
   POD DIAGNOSTICS
========================================================= */

export type DiagnosticSeverity =
  | "critical"
  | "warning"
  | "info";

export type DiagnosticIssue = {
  id?: string;
  type?: string;

  severity?: string;
  category?: string;

  title?: string;

  message?: string;
  description?: string;

  container?: string;

  evidence?: string[] | string;

  possible_causes?: string[];
};

/* =========================================================
   POD INVESTIGATION
========================================================= */

export type RootCause = {
  rank?: number;

  priority_score?: number;

  title: string;

  category: string;

  severity?: string;

  confidence: number | string;

  description?: string;

  summary?: string;

  evidence: string[];

  recommended_actions?: string[];

  recommended_checks?: string[];
};

export type PodInvestigation = {
  namespace: string;

  pod: string;

  pod_data: Record<string, unknown>;

  events: EventSummary[];

  logs: {
    current: Record<string, string>;

    previous: Record<string, string>;
  };

  diagnostics: {
    issue_count: number;

    issues: DiagnosticIssue[];
  };

  root_causes: RootCause[];

  root_cause_count?: number;
};

/* =========================================================
   DEPLOYMENTS
========================================================= */

export type DeploymentSummary = {
  namespace: string;
  name: string;

  replicas: number;

  ready_replicas: number;

  available_replicas: number;

  updated_replicas: number;

  strategy: string;

  age: string;
};

export type DeploymentDetail =
  DeploymentSummary & {
    selector: Record<string, string>;

    labels: Record<string, string>;

    annotations: Record<string, string>;

    containers: Array<{
      name: string;

      image: string;
    }>;

    conditions: Array<{
      type: string;

      status: string;

      reason: string;

      message: string;

      last_transition_time: string;
    }>;
  };

export type DeploymentEvents = {
  deployment: string;

  namespace: string;

  total_events: number;

  events: EventSummary[];
};

export type DeploymentYaml = {
  deployment: string;

  namespace: string;

  yaml: string;
};

export type DeploymentYamlRequest = {
  yaml: string;
};

export type DeploymentYamlValidationResponse = {
  valid: boolean;

  message: string;
};

export type DeploymentApplyResponse = {
  success: boolean;

  message: string;

  backup_id?: string | null;
};

export type DeploymentBackup = {
  id: string;

  created_at: string;
};

export type DeploymentBackupDetail = {
  id: string;

  deployment: string;

  namespace: string;

  yaml: string;

  created_at: string;
};

export type DeploymentRestoreResponse = {
  success: boolean;

  message: string;
};

/* =========================================================
   NODES
========================================================= */

export type NodeSummary = {
  name: string;

  status: string;

  roles: string;

  version: string;

  internal_ip: string;

  os_image: string;

  kernel_version: string;

  container_runtime: string;

  age: string;
};

export type NodeCondition = {
  type: string;

  status: string;

  reason?: string;

  message?: string;

  lastTransitionTime?: string;
};

export type NodeMetrics = {
  available: boolean;

  cpu: string | null;

  memory: string | null;
};

export type NodeDetail =
  NodeSummary & {
    labels: Record<string, string>;

    annotations: Record<string, string>;

    capacity: Record<string, string>;

    allocatable: Record<string, string>;

    conditions: NodeCondition[];

    provider_id: string;

    pod_cidr: string;

    unschedulable: boolean;

    metrics: NodeMetrics;

    health_score: number | null;

    yaml: string;

    events: EventSummary[];
  };

/* =========================================================
   SERVICES
========================================================= */

export type ServicePort = {
  name: string;

  port: number;

  target_port: number | string;

  protocol: string;
};

export type ServiceSummary = {
  namespace: string;

  name: string;

  type: string;

  cluster_ip: string;

  external_ip?: string | null;

  ports: ServicePort[];

  selector: Record<string, string>;

  age: string;
};

export type ServiceDetail =
  ServiceSummary & {
    labels: Record<string, string>;

    annotations: Record<string, string>;
  };

export type ServiceEvents = {
  service: string;

  namespace: string;

  total_events: number;

  events: EventSummary[];
};

export type ServiceYaml = {
  service: string;

  namespace: string;

  yaml: string;
};

/* =========================================================
   INGRESSES
========================================================= */

export type IngressSummary = {
  namespace: string;

  name: string;

  ingress_class: string;

  hosts: string[];

  address: string;

  ports: string;

  age: string;
};

export type IngressRule = {
  host: string;

  path: string;

  service: string;

  port: number | string;
};

export type IngressTLS = {
  hosts: string[];

  secret_name: string;
};

export type IngressDetail = {
  namespace: string;

  name: string;

  ingress_class: string;

  address: string;

  rules: IngressRule[];

  tls: IngressTLS[];

  labels: Record<string, string>;

  annotations: Record<string, string>;
};

export type IngressEvents = {
  namespace: string;

  name: string;

  total_events: number;

  events: EventSummary[];
};

export type IngressYaml = {
  namespace: string;

  name: string;

  yaml: string;
};

/* =========================================================
   INVESTIGATIONS
========================================================= */

export type InvestigationSummary = {
  id: string;

  cluster: string;

  namespace: string;

  resource_type: string;

  resource_name: string;

  status: string;

  created_at?: string;

  updated_at?: string;
};

export type InvestigationListResponse = {
  items: InvestigationSummary[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
};
export type InvestigationSection = {
  status: string;
  data?: unknown;
  error?: string | null;
};

export type InvestigationEvidence = {
  namespace: InvestigationSection;
  pod: InvestigationSection;
  deployment: InvestigationSection;
  replicaset: InvestigationSection;
  node: InvestigationSection;
  events: InvestigationSection;
  logs: InvestigationSection;
  services: InvestigationSection;
  pvc: InvestigationSection;
  metrics: InvestigationSection;
};

export type InvestigationTarget = {
  namespace: string;
  resource_type: string;
  resource_name: string;
};

export type AISeverity =
  | "INFO"
  | "LOW"
  | "MEDIUM"
  | "HIGH"
  | "CRITICAL";

export type AIRootCause = {
  title: string;
  explanation: string;
  severity: AISeverity;
  confidence: number;
  evidence: string[];
};

export type AIRecommendation = {
  action: string;
  reason: string;
  risk: string;
  commands: string[];
};

export type AIDiagnosis = {
  summary: string;
  severity: AISeverity;
  confidence: number;
  root_causes: AIRootCause[];
  recommendations: AIRecommendation[];
  limitations: string[];
};

export type InvestigationAnalysis = {
  diagnostics: Array<Record<string, unknown>>;
  root_causes: Array<Record<string, unknown>>;
  ai: AIDiagnosis | null;
};

export type Investigation = {
  id: string;
  target: {
    namespace: string;
    resource_type: string;
    resource_name: string;
  };
  status: string;
  evidence: InvestigationEvidence;
  analysis?: InvestigationAnalysis;
  created_at: string;
  updated_at: string;
};

export type InvestigationFilters = {
  page?: number;
  page_size?: number;
  search?: string;
  namespace?: string;
  status?: string;
  resource_type?: string;
};

/* =========================================================
   BACKEND HEALTH HOOK
========================================================= */

export function useBackendHealth() {
  return useQuery({
    queryKey: [
      "backend-health",
    ],

    queryFn: ({ signal }) =>
      apiFetch<BackendHealth>(
        "/health",
        {
          signal,
        },
      ),

    refetchInterval: 30_000,
  });
}

/* =========================================================
   CLUSTER HEALTH HOOK
========================================================= */

export function useClusterHealth() {
  return useQuery({
    queryKey: [
      "cluster-health",
    ],

    queryFn: ({ signal }) =>
      apiFetch<ClusterHealth>(
        "/kubernetes/cluster/health",
        {
          signal,
        },
      ),

    refetchInterval: 30_000,

    retry: 1,
  });
}

/* =========================================================
   NAMESPACES HOOK
========================================================= */

export function useNamespaces() {
  return useQuery({
    queryKey: [
      "namespaces",
    ],

    queryFn: ({ signal }) =>
      apiFetch<NamespaceSummary[]>(
        "/kubernetes/namespaces",
        {
          signal,
        },
      ),

    refetchInterval: 30_000,
  });
}

/* =========================================================
   PODS HOOK
========================================================= */

export function usePods(
  namespace?: string,
) {
  const path = namespace
    ? `/kubernetes/pods/${encodeURIComponent(
      namespace,
    )}`
    : "/kubernetes/pods";

  return useQuery({
    queryKey: [
      "pods",
      namespace ?? "all",
    ],

    queryFn: ({ signal }) =>
      apiFetch<PodSummary[]>(
        path,
        {
          signal,
        },
      ),

    refetchInterval: 20_000,
  });
}

/* =========================================================
   KUBERNETES CONTEXTS
========================================================= */

export function useKubernetesContexts() {
  return useQuery({
    queryKey: [
      "kubernetes-contexts",
    ],

    queryFn: ({ signal }) =>
      apiFetch<KubernetesContexts>(
        "/kubernetes/contexts",
        {
          signal,
        },
      ),

    refetchInterval: 30_000,
  });
}

export function useSwitchKubernetesContext() {
  const queryClient =
    useQueryClient();

  return useMutation({
    mutationFn: async (
      payload: ContextSwitchRequest,
    ) =>
      apiFetch<ContextSwitchResponse>(
        "/kubernetes/contexts/select",
        {
          method: "POST",

          headers: {
            "Content-Type":
              "application/json",
          },

          body: JSON.stringify(
            payload,
          ),
        },
      ),

    onSuccess: async () => {
      await queryClient.invalidateQueries();
    },
  });
}

/* =========================================================
   POD LOGS
========================================================= */

export type LogOptions = {tail: number; since?: string; since_time?: string; container?: string; previous?: boolean};

export function usePodLogs(
  pod: PodSummary | null,
  options: LogOptions = {tail:200},
) {
  return useQuery({
    queryKey: [
      "pod-logs",
      pod?.namespace,
      pod?.name,
      options,
    ],

    queryFn: ({ signal }) =>
      apiFetch<PodLogs>(
        `/kubernetes/pods/${encodeURIComponent(
          pod?.namespace ?? "",
        )}/${encodeURIComponent(
          pod?.name ?? "",
        )}/logs?${new URLSearchParams({tail:String(options.tail), timestamps:"true", ...(options.since ? {since:options.since} : {}), ...(options.since_time ? {since_time:options.since_time} : {}), ...(options.container ? {container:options.container} : {}), previous:String(!!options.previous)}).toString()}`,
        {
          signal,
        },
      ),

    enabled: Boolean(pod),

    retry: false,
  });
}

/* =========================================================
   POD INVESTIGATION
========================================================= */

export function usePodInvestigation(pod: PodSummary | null) {
  const queryClient = useQueryClient();
  const mutation = useMutation({
    mutationFn: async (target: PodSummary): Promise<PodInvestigation & { id: string }> => {
      const saved = await apiFetch<Investigation>("/v1/investigations", {
        method: "POST",
        body: JSON.stringify({
          namespace: target.namespace, resource_type: "pod",
          resource_name: target.name, log_tail: 100, include_previous_logs: true,
        }),
      });
      queryClient.setQueryData(["investigation", saved.id], saved);
      await queryClient.invalidateQueries({ queryKey: ["investigations"] });
      const record = (value: unknown): Record<string, unknown> =>
        value && typeof value === "object" && !Array.isArray(value)
          ? value as Record<string, unknown> : {};
      const payload = record(saved.evidence.logs.data);
      const podLogs = record(record(payload.pods)[target.name] ?? payload);
      const logMap = (value: unknown): Record<string, string> =>
        Object.fromEntries(Object.entries(record(value)).map(([name, entry]) => {
          const lines = record(entry).logs ?? entry;
          return [name, Array.isArray(lines) ? lines.join("\n") : typeof lines === "string" ? lines : ""];
        }));
      const events = record(saved.evidence.events.data).events;
      const issues = (saved.analysis?.diagnostics ?? []) as DiagnosticIssue[];
      const causes = (saved.analysis?.root_causes ?? []) as RootCause[];
      return {
        id: saved.id, namespace: target.namespace, pod: target.name,
        pod_data: record(saved.evidence.pod.data),
        events: Array.isArray(events) ? events as EventSummary[] : [],
        logs: { current: logMap(podLogs.containers ?? podLogs.current),
                previous: logMap(podLogs.previous) },
        diagnostics: { issue_count: issues.length, issues },
        root_causes: causes, root_cause_count: causes.length,
      };
    },
    retry: false,
  });
  const matches = mutation.variables?.namespace === pod?.namespace &&
    mutation.variables?.name === pod?.name;
  return {
    data: matches ? mutation.data : undefined,
    error: matches ? mutation.error : null,
    isLoading: mutation.isPending,
    isFetching: mutation.isPending,
    run: (target: PodSummary) => { if (!mutation.isPending) mutation.mutate(target); },
    refetch: () => { if (pod && !mutation.isPending) mutation.mutate(pod); },
  };
}

/* =========================================================
   DEPLOYMENTS
========================================================= */

export function useDeployments(
  namespace?: string,
) {
  const path = namespace
    ? `/kubernetes/deployments/${encodeURIComponent(
      namespace,
    )}`
    : "/kubernetes/deployments";

  return useQuery({
    queryKey: [
      "deployments",
      namespace ?? "all",
    ],

    queryFn: ({ signal }) =>
      apiFetch<DeploymentSummary[]>(
        path,
        {
          signal,
        },
      ),

    refetchInterval: 20_000,
  });
}

export function useDeploymentDetail(
  deployment: DeploymentSummary | null,
) {
  return useQuery({
    queryKey: [
      "deployment-detail",
      deployment?.namespace,
      deployment?.name,
    ],

    queryFn: ({ signal }) =>
      apiFetch<DeploymentDetail>(
        `/kubernetes/deployments/${encodeURIComponent(
          deployment?.namespace ?? "",
        )}/${encodeURIComponent(
          deployment?.name ?? "",
        )}`,
        {
          signal,
        },
      ),

    enabled: Boolean(
      deployment,
    ),
  });
}

export function useDeploymentEvents(
  deployment: DeploymentSummary | null,
) {
  return useQuery({
    queryKey: [
      "deployment-events",
      deployment?.namespace,
      deployment?.name,
    ],

    queryFn: ({ signal }) =>
      apiFetch<DeploymentEvents>(
        `/kubernetes/deployments/${encodeURIComponent(
          deployment?.namespace ?? "",
        )}/${encodeURIComponent(
          deployment?.name ?? "",
        )}/events`,
        {
          signal,
        },
      ),

    enabled: Boolean(
      deployment,
    ),
  });
}

export function useDeploymentYaml(
  deployment: DeploymentSummary | null,
) {
  return useQuery({
    queryKey: [
      "deployment-yaml",
      deployment?.namespace,
      deployment?.name,
    ],

    queryFn: ({ signal }) =>
      apiFetch<DeploymentYaml>(
        `/kubernetes/deployments/${encodeURIComponent(
          deployment?.namespace ?? "",
        )}/${encodeURIComponent(
          deployment?.name ?? "",
        )}/yaml`,
        {
          signal,
        },
      ),

    enabled: Boolean(
      deployment,
    ),
  });
}

export function useValidateDeploymentYaml() {
  return useMutation({
    mutationFn: async ({
      namespace,
      deployment,
      yaml,
    }: {
      namespace: string;
      deployment: string;
      yaml: string;
    }) =>
      apiFetch<DeploymentYamlValidationResponse>(
        `/kubernetes/deployments/${encodeURIComponent(
          namespace,
        )}/${encodeURIComponent(
          deployment,
        )}/yaml/validate`,
        {
          method: "POST",

          headers: {
            "Content-Type":
              "application/json",
          },

          body: JSON.stringify({
            yaml,
          }),
        },
      ),
  });
}

export function useApplyDeploymentYaml() {
  const queryClient =
    useQueryClient();

  return useMutation({
    mutationFn: async ({
      namespace,
      deployment,
      yaml,
      confirmation,
    }: {
      namespace: string;
      deployment: string;
      yaml: string;
      confirmation: string;
    }) =>
      apiFetch<DeploymentApplyResponse>(
        `/kubernetes/deployments/${encodeURIComponent(
          namespace,
        )}/${encodeURIComponent(
          deployment,
        )}/yaml/apply`,
        {
          method: "POST",

          headers: {
            "Content-Type":
              "application/json",
          },

          body: JSON.stringify({
            yaml,
            confirmation,
          }),
        },
      ),

    onSuccess: async () => {
      await queryClient.invalidateQueries({
        queryKey: [
          "deployments",
        ],
      });

      await queryClient.invalidateQueries({
        queryKey: [
          "deployment-detail",
        ],
      });

      await queryClient.invalidateQueries({
        queryKey: [
          "deployment-yaml",
        ],
      });
    },
  });
}

export function useDeploymentBackups(
  deployment: DeploymentSummary | null,
) {
  return useQuery({
    queryKey: [
      "deployment-backups",
      deployment?.namespace,
      deployment?.name,
    ],

    queryFn: ({ signal }) =>
      apiFetch<DeploymentBackup[]>(
        `/kubernetes/deployments/${encodeURIComponent(
          deployment?.namespace ?? "",
        )}/${encodeURIComponent(
          deployment?.name ?? "",
        )}/backups`,
        {
          signal,
        },
      ),

    enabled: Boolean(
      deployment,
    ),
  });
}

export function useDeploymentBackup(
  deployment: DeploymentSummary | null,
  backupId: string | null,
) {
  return useQuery({
    queryKey: [
      "deployment-backup",
      deployment?.namespace,
      deployment?.name,
      backupId,
    ],

    queryFn: ({ signal }) =>
      apiFetch<DeploymentBackupDetail>(
        `/kubernetes/deployments/${encodeURIComponent(
          deployment?.namespace ?? "",
        )}/${encodeURIComponent(
          deployment?.name ?? "",
        )}/backups/${encodeURIComponent(
          backupId ?? "",
        )}`,
        {
          signal,
        },
      ),

    enabled: Boolean(
      deployment &&
      backupId,
    ),
  });
}

export function useRestoreDeploymentBackup() {
  const queryClient =
    useQueryClient();

  return useMutation({
    mutationFn: async ({
      namespace,
      deployment,
      backupId,
      confirmation,
    }: {
      namespace: string;
      deployment: string;
      backupId: string;
      confirmation: string;
    }) =>
      apiFetch<DeploymentRestoreResponse>(
        `/kubernetes/deployments/${encodeURIComponent(
          namespace,
        )}/${encodeURIComponent(
          deployment,
        )}/backups/${encodeURIComponent(
          backupId,
        )}/restore`,
        {
          method: "POST",
          body: JSON.stringify({ confirmation }),
        },
      ),

    onSuccess: async () => {
      await queryClient.invalidateQueries({
        queryKey: [
          "deployments",
        ],
      });

      await queryClient.invalidateQueries({
        queryKey: [
          "deployment-detail",
        ],
      });

      await queryClient.invalidateQueries({
        queryKey: [
          "deployment-yaml",
        ],
      });

      await queryClient.invalidateQueries({
        queryKey: [
          "deployment-backups",
        ],
      });
    },
  });
}

/* =========================================================
   NODES
========================================================= */

export function useNodes() {
  return useQuery({
    queryKey: [
      "nodes",
    ],

    queryFn: ({ signal }) =>
      apiFetch<NodeSummary[]>(
        "/kubernetes/nodes",
        {
          signal,
        },
      ),

    retry: false,
  });
}

export function useNodeDetail(
  node: NodeSummary | null,
) {
  return useQuery({
    queryKey: [
      "node-detail",
      node?.name,
    ],

    enabled: Boolean(
      node,
    ),

    queryFn: ({ signal }) =>
      apiFetch<unknown>(
        `/kubernetes/nodes/${encodeURIComponent(
          node?.name ?? "",
        )}`,
        {
          signal,
        },
      ).then(normalizeNode),

    refetchInterval: 30_000,
  });
}

/* =========================================================
   SERVICES
========================================================= */

export function useServices(
  namespace?: string,
) {
  const path = namespace
    ? `/kubernetes/services/${encodeURIComponent(
      namespace,
    )}`
    : "/kubernetes/services";

  return useQuery({
    queryKey: [
      "services",
      namespace ?? "all",
    ],

    queryFn: ({ signal }) =>
      apiFetch<ServiceSummary[]>(
        path,
        {
          signal,
        },
      ),

    refetchInterval: 20_000,
  });
}

export function useServiceDetail(
  service: ServiceSummary | null,
) {
  return useQuery({
    queryKey: [
      "service-detail",
      service?.namespace,
      service?.name,
    ],

    queryFn: ({ signal }) =>
      apiFetch<unknown>(
        `/kubernetes/services/${encodeURIComponent(
          service?.namespace ?? "",
        )}/${encodeURIComponent(
          service?.name ?? "",
        )}`,
        {
          signal,
        },
      ).then(normalizeService),

    enabled: Boolean(
      service,
    ),
  });
}

export function useServiceEvents(
  service: ServiceSummary | null,
) {
  return useQuery({
    queryKey: [
      "service-events",
      service?.namespace,
      service?.name,
    ],

    queryFn: ({ signal }) =>
      apiFetch<ServiceEvents>(
        `/kubernetes/services/${encodeURIComponent(
          service?.namespace ?? "",
        )}/${encodeURIComponent(
          service?.name ?? "",
        )}/events`,
        {
          signal,
        },
      ),

    enabled: Boolean(
      service,
    ),
  });
}

export function useServiceYaml(
  service: ServiceSummary | null,
) {
  return useQuery({
    queryKey: [
      "service-yaml",
      service?.namespace,
      service?.name,
    ],

    queryFn: ({ signal }) =>
      apiFetch<ServiceYaml>(
        `/kubernetes/services/${encodeURIComponent(
          service?.namespace ?? "",
        )}/${encodeURIComponent(
          service?.name ?? "",
        )}/yaml`,
        {
          signal,
        },
      ),

    enabled: Boolean(
      service,
    ),
  });
}

/* =========================================================
   INGRESSES
========================================================= */

export function useIngresses(
  namespace?: string,
) {
  const path = namespace
    ? `/kubernetes/ingresses/${encodeURIComponent(
      namespace,
    )}`
    : "/kubernetes/ingresses";

  return useQuery({
    queryKey: [
      "ingresses",
      namespace ?? "all",
    ],

    queryFn: ({ signal }) =>
      apiFetch<IngressSummary[]>(
        path,
        {
          signal,
        },
      ),

    refetchInterval: 20_000,
  });
}

export function useIngressDetail(
  ingress: IngressSummary | null,
) {
  return useQuery({
    queryKey: [
      "ingress-detail",
      ingress?.namespace,
      ingress?.name,
    ],

    queryFn: ({ signal }) =>
      apiFetch<unknown>(
        `/kubernetes/ingresses/${encodeURIComponent(
          ingress?.namespace ?? "",
        )}/${encodeURIComponent(
          ingress?.name ?? "",
        )}`,
        {
          signal,
        },
      ).then(normalizeIngress),

    enabled: Boolean(
      ingress,
    ),
  });
}

export function useIngressEvents(
  ingress: IngressSummary | null,
) {
  return useQuery({
    queryKey: [
      "ingress-events",
      ingress?.namespace,
      ingress?.name,
    ],

    queryFn: ({ signal }) =>
      apiFetch<IngressEvents>(
        `/kubernetes/ingresses/${encodeURIComponent(
          ingress?.namespace ?? "",
        )}/${encodeURIComponent(
          ingress?.name ?? "",
        )}/events`,
        {
          signal,
        },
      ),

    enabled: Boolean(
      ingress,
    ),
  });
}

export function useIngressYaml(
  ingress: IngressSummary | null,
) {
  return useQuery({
    queryKey: [
      "ingress-yaml",
      ingress?.namespace,
      ingress?.name,
    ],

    queryFn: ({ signal }) =>
      apiFetch<IngressYaml>(
        `/kubernetes/ingresses/${encodeURIComponent(
          ingress?.namespace ?? "",
        )}/${encodeURIComponent(
          ingress?.name ?? "",
        )}/yaml`,
        {
          signal,
        },
      ),

    enabled: Boolean(
      ingress,
    ),
  });
}

/* =========================================================
   INVESTIGATION HISTORY
========================================================= */

export function useInvestigations(
  filters: InvestigationFilters = {},
) {
  const params = new URLSearchParams();

  params.set(
    "page",
    String(filters.page ?? 1),
  );

  params.set(
    "page_size",
    String(filters.page_size ?? 20),
  );

  if (filters.search?.trim()) {
    params.set(
      "search",
      filters.search.trim(),
    );
  }

  if (filters.namespace) {
    params.set(
      "namespace",
      filters.namespace,
    );
  }

  if (filters.status) {
    params.set(
      "status",
      filters.status,
    );
  }

  if (filters.resource_type) {
    params.set(
      "resource_type",
      filters.resource_type,
    );
  }

  return useQuery({
    queryKey: [
      "investigations",
      filters,
    ],

    queryFn: ({ signal }) =>
      apiFetch<InvestigationListResponse>(
        `/v1/investigations?${params.toString()}`,
        {
          signal,
        },
      ),

    retry: false,
  });
}

export function useInvestigation(
  investigationId: string | null,
) {
  return useQuery({
    queryKey: [
      "investigation",
      investigationId,
    ],

    queryFn: ({ signal }) =>
      apiFetch<Investigation>(
        `/v1/investigations/${encodeURIComponent(
          investigationId ?? "",
        )}`,
        {
          signal,
        },
      ),

    enabled: Boolean(
      investigationId,
    ),

    retry: false,
  });
}