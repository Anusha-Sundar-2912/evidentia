import { useState } from "react";
import { ShieldCheck, LockKeyhole, ScanText } from "lucide-react";
import { useWorkspace } from "../store/workspace";
import {
  PageHeading,
  Badge,
  JsonDetails,
  Empty,
} from "../components/ui/Common";
export default function Guardrails() {
  const { result, blocked } = useWorkspace();
  const [demo, setDemo] = useState(
    "Please contact test@example.com about this report.",
  );
  const redacted = demo.replace(
    /\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b/g,
    "[REDACTED_EMAIL]",
  );
  return (
    <>
      <PageHeading eyebrow="GUARDRAILS" title="Trust requires boundaries.">
        See the checks around your question and its answer.
      </PageHeading>
      <div className="capability-grid">
        {[
          [
            ShieldCheck,
            "Input protection",
            "Known prompt-injection patterns are checked before retrieval.",
          ],
          [
            LockKeyhole,
            "Privacy",
            "Input patterns cover email, Indian phone numbers, Aadhaar, PAN and IPv4.",
          ],
          [
            ScanText,
            "Answer validation",
            "Citation references and a word-overlap grounding heuristic are checked.",
          ],
        ].map(([Icon, title, copy]) => {
          const I = Icon as typeof ShieldCheck;
          return (
            <article className="panel capability" key={String(title)}>
              <I size={23} />
              <h3>{String(title)}</h3>
              <p>{String(copy)}</p>
              <span className="caption">
                Implemented capability · not a live status
              </span>
            </article>
          );
        })}
      </div>
      {blocked ? (
        <section className="panel">
          <Badge tone="warn">Latest request blocked</Badge>
          <h2>A boundary held.</h2>
          <p>{blocked.reasons.join(", ").replaceAll("_", " ")}</p>
          <JsonDetails value={blocked} />
        </section>
      ) : result ? (
        <section className="panel">
          <div className="section-label">
            <span>LATEST ANSWER / ACTUAL CHECKS</span>
            <Badge tone={result.guardrails.output.safe ? "good" : "warn"}>
              {result.guardrails.output.safe
                ? "Output privacy check passed"
                : "Output privacy flag"}
            </Badge>
          </div>
          <h2>{result.query}</h2>
          <dl className="checks">
            <div>
              <dt>Input allowed</dt>
              <dd>{result.guardrails.input.allowed ? "Yes" : "No"}</dd>
            </div>
            <div>
              <dt>Prompt injection detected</dt>
              <dd>
                {result.guardrails.input.prompt_injection_detected
                  ? "Yes"
                  : "No"}
              </dd>
            </div>
            <div>
              <dt>Input PII redacted</dt>
              <dd>{result.guardrails.input.pii_redacted ? "Yes" : "No"}</dd>
            </div>
            <div>
              <dt>Detected input types</dt>
              <dd>{result.guardrails.input.pii_types.join(", ") || "None"}</dd>
            </div>
            <div>
              <dt>Output PII types</dt>
              <dd>{result.guardrails.output.pii_types.join(", ") || "None"}</dd>
            </div>
            <div>
              <dt>Production validator</dt>
              <dd>{result.validation.valid ? "Passed" : "Needs review"}</dd>
            </div>
          </dl>
          {!result.guardrails.output.safe && (
            <p className="notice warning">
              The returned answer was flagged for sensitive content and is
              hidden by this interface. The backend currently returns the
              original answer; this is not confirmation of server-side output
              redaction.
            </p>
          )}
          <JsonDetails
            value={{
              guardrails: result.guardrails,
              validation: result.validation,
            }}
          />
        </section>
      ) : (
        <Empty title="Nothing checked yet." to="/ask" label="Ask a question">
          A real query report will appear here once an answer or a blocked
          request is returned.
        </Empty>
      )}
      <section className="panel privacy-demo">
        <Badge>DEMO · LOCAL ONLY</Badge>
        <h2>A small privacy demonstration.</h2>
        <p>
          Try the email pattern. Nothing entered here is sent to the backend or
          a model.
        </p>
        <label>
          Example text
          <textarea
            value={demo}
            onChange={(e) => setDemo(e.target.value)}
            maxLength={2000}
          />
        </label>
        <span className="eyebrow">AFTER EMAIL REDACTION</span>
        <output>{redacted}</output>
        <p className="caption">
          This demonstrates one deterministic pattern, not comprehensive PII
          detection.
        </p>
      </section>
    </>
  );
}
