import { useQuery } from "@tanstack/react-query";
import { Activity, Database, RefreshCw, Server } from "lucide-react";
import { api } from "../api/client";
import {
  PageHeading,
  ErrorNotice,
  Badge,
  JsonDetails,
} from "../components/ui/Common";
export default function System() {
  const health = useQuery({
    queryKey: ["health"],
    queryFn: api.health,
    staleTime: 30000,
  });
  const ready = useQuery({
    queryKey: ["ready"],
    queryFn: api.ready,
    staleTime: 30000,
  });
  return (
    <>
      <PageHeading eyebrow="SYSTEM" title="Behind the intelligence.">
        A direct view of the infrastructure that makes knowledge useful.
      </PageHeading>
      <button
        className="button ghost refresh"
        disabled={health.isFetching || ready.isFetching}
        onClick={() => {
          void health.refetch();
          void ready.refetch();
        }}
      >
        <RefreshCw
          size={15}
          className={health.isFetching || ready.isFetching ? "spin" : ""}
        />
        Refresh checks
      </button>
      <div className="system-grid">
        {[
          {
            name: "API process",
            Icon: Server,
            value: health.data?.status === "healthy",
            known: !!health.data,
            error: health.isError,
            loading: health.isFetching,
            description: "Liveness: the API process is responding.",
          },
          {
            name: "PostgreSQL",
            Icon: Database,
            value: ready.data?.checks.postgres,
            known: !!ready.data,
            error: ready.isError,
            loading: ready.isFetching,
            description: "Readiness: a database connection and SELECT 1.",
          },
          {
            name: "Redis",
            Icon: Activity,
            value: ready.data?.checks.redis,
            known: !!ready.data,
            error: ready.isError,
            loading: ready.isFetching,
            description: "Readiness: a successful Redis ping.",
          },
        ].map(({ name, Icon, value, known, error, loading, description }) => (
          <article className="panel system-card" key={name}>
            <Icon size={25} />
            <h2>{name}</h2>
            <Badge
              tone={
                error
                  ? "warn"
                  : known && !loading
                    ? value
                      ? "good"
                      : "warn"
                    : "neutral"
              }
            >
              {loading
                ? "Checking"
                : error
                  ? "Check unavailable"
                  : known
                    ? value
                      ? "Responding"
                      : "Unreachable"
                    : "Not checked"}
            </Badge>
            <p>{description}</p>
          </article>
        ))}
      </div>
      <ErrorNotice error={health.error} />
      <ErrorNotice error={ready.error} />
      {ready.data && (
        <section className="panel">
          <div className="section-label">
            <span>READINESS REPORT</span>
            <Badge tone={ready.data.status === "ready" ? "good" : "warn"}>
              {ready.data.status}
            </Badge>
          </div>
          <h2>{ready.data.service}</h2>
          <p>
            Version {ready.data.version} · Last successful response{" "}
            {new Date(ready.dataUpdatedAt).toLocaleTimeString()}
          </p>
          <JsonDetails value={ready.data} />
        </section>
      )}
      <div className="notice neutral">
        These checks do not test the embedding model, reranker, pgvector index,
        or LLM provider. Their health is not exposed by the backend.
      </div>
    </>
  );
}
