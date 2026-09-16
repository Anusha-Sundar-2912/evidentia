import { useEffect, useState, type ReactNode } from "react";
import { ArrowUpRight, CircleAlert, LoaderCircle } from "lucide-react";
import { Link } from "react-router-dom";
import { ApiError } from "../../api/client";
export function PageHeading({
  eyebrow,
  title,
  children,
  action,
}: {
  eyebrow: string;
  title: string;
  children?: ReactNode;
  action?: ReactNode;
}) {
  return (
    <header className="page-heading">
      <div>
        <span className="eyebrow">{eyebrow}</span>
        <h1>{title}</h1>
        <p>{children}</p>
      </div>
      {action}
    </header>
  );
}
export function Empty({
  title,
  children,
  to,
  label,
}: {
  title: string;
  children: ReactNode;
  to?: string;
  label?: string;
}) {
  return (
    <section className="empty panel">
      <div className="empty-symbol">✧</div>
      <h2>{title}</h2>
      <p>{children}</p>
      {to && (
        <Link className="button primary" to={to}>
          {label}
          <ArrowUpRight size={16} />
        </Link>
      )}
    </section>
  );
}
export function ErrorNotice({ error }: { error: unknown }) {
  if (!error) return null;
  const e = error as Error;
  return (
    <div role="alert" className="notice warning">
      <CircleAlert size={19} />
      <div>
        <strong>
          {error instanceof ApiError && error.guardrails
            ? "Request held by input protection"
            : "This request could not finish"}
        </strong>
        <p>{e.message || "An unexpected error occurred."}</p>
        {error instanceof ApiError && error.status > 0 && (
          <small>
            HTTP {error.status}
            {error.code ? ` · ${error.code}` : ""}
          </small>
        )}
      </div>
    </div>
  );
}
export function Pending({
  text = "Working with your knowledge",
  long = false,
}: {
  text?: string;
  long?: boolean;
}) {
  const [seconds, setSeconds] = useState(0);
  useEffect(() => {
    const id = setInterval(() => setSeconds((s) => s + 1), 1000);
    return () => clearInterval(id);
  }, []);
  return (
    <div className="notice pending" role="status">
      <LoaderCircle className="spin" size={22} />
      <div>
        <strong>{text}</strong>
        <p>
          {long
            ? "This may take several minutes. You can explore other pages; keep this tab open."
            : "The backend returns the complete result when processing finishes."}
        </p>
        <small>
          {seconds}s elapsed · No live stage information available
          {seconds > 90 ? " · Still waiting; avoid resubmitting." : ""}
        </small>
      </div>
    </div>
  );
}
export function JsonDetails({
  value,
  label = "Inspect returned data",
}: {
  value: unknown;
  label?: string;
}) {
  return (
    <details className="json-details">
      <summary>{label}</summary>
      <pre>{JSON.stringify(value, null, 2)}</pre>
    </details>
  );
}
export const percent = (n: number) => `${(n * 100).toFixed(1)}%`;
export const ms = (n: number | undefined) =>
  n === undefined
    ? "Not reported"
    : n >= 1000
      ? `${(n / 1000).toFixed(2)} s`
      : `${n.toFixed(1)} ms`;
export function Badge({
  children,
  tone = "neutral",
}: {
  children: ReactNode;
  tone?: "neutral" | "good" | "warn";
}) {
  return <span className={`badge ${tone}`}>{children}</span>;
}
