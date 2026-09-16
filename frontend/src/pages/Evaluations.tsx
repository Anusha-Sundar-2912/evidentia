import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { FlaskConical, ArrowUpRight } from "lucide-react";
import { api } from "../api/client";
import type { Dataset, Difficulty, EvaluationReport } from "../types/api";
import { useWorkspace, updateWorkspace } from "../store/workspace";
import {
  PageHeading,
  Pending,
  ErrorNotice,
  Badge,
  JsonDetails,
  percent,
  ms,
} from "../components/ui/Common";
const metrics: [string, string, string][] = [
  [
    "hit_rate_at_k",
    "Hit@K",
    "Fraction of cases with at least one relevant retrieved chunk.",
  ],
  [
    "precision_at_k",
    "Precision@K",
    "Relevant chunks divided by the number actually returned, up to K.",
  ],
  [
    "recall_at_k",
    "Recall@K",
    "Fraction of judged relevant chunks found in the top K.",
  ],
  ["mrr", "MRR", "Average reciprocal rank of the first relevant chunk."],
  ["ndcg_at_k", "nDCG@K", "Ranking quality weighted by graded relevance."],
  [
    "faithfulness",
    "Faithfulness",
    "Fraction of extracted claims judged supported by evidence.",
  ],
  [
    "citation_correctness",
    "Citation correctness",
    "Fraction of answer citations that support an extracted claim.",
  ],
  [
    "citation_coverage",
    "Citation coverage",
    "Fraction of supported claims covered by a supporting answer citation.",
  ],
];
export default function Evaluations() {
  const client = useQueryClient();
  const { operation, taskError } = useWorkspace();
  const [size, setSize] = useState(3);
  const [difficulty, setDifficulty] = useState<Difficulty>("paraphrase");
  const [topK, setTopK] = useState(5);
  const [ack, setAck] = useState(false);
  const { data: report } = useQuery<EvaluationReport>({
    queryKey: ["evaluation-report"],
    enabled: false,
  });
  const { data: dataset } = useQuery<Dataset>({
    queryKey: ["generated-dataset"],
    enabled: false,
  });
  const mutation = useMutation({
    mutationKey: ["evaluation"],
    mutationFn: async (action: "generate" | "run") => {
      const p = { sample_size: size, difficulty, top_k: topK };
      if (action === "generate") {
        const data = await api.generate(p);
        client.setQueryData(["generated-dataset"], data);
      } else {
        const data = await api.evaluate(p);
        client.setQueryData(["evaluation-report"], data);
      }
    },
    onMutate: () =>
      updateWorkspace({
        taskError: undefined,
        operation: "evaluation",
        evi: "thinking",
      }),
    onSuccess: () => updateWorkspace({ evi: "success" }),
    onError: (e) =>
      updateWorkspace({
        evi: "error",
        taskError: { task: "evaluation", error: e },
      }),
    onSettled: () => updateWorkspace({ operation: undefined }),
  });
  return (
    <>
      <PageHeading
        eyebrow="EVALUATION LAB"
        title="Put your knowledge to the test."
      >
        Can your system answer questions about its own data?
      </PageHeading>
      <section className="evaluation-intro panel">
        <div className="evaluation-icon">
          <FlaskConical size={28} />
        </div>
        <div>
          <span className="eyebrow">EVIDENCE, UNDER EXAMINATION</span>
          <h2>A test built from your knowledge.</h2>
          <p>
            Sample evidence, generate questions and hidden reference answers,
            then measure the production retrieval and answering pipeline.
          </p>
        </div>
      </section>
      <section className="panel eval-controls">
        <div className="form-row">
          <label>
            Requested cases
            <input
              type="number"
              min={1}
              max={25}
              value={size}
              onChange={(e) => setSize(Number(e.target.value))}
            />
          </label>
          <label>
            Difficulty
            <select
              value={difficulty}
              onChange={(e) => setDifficulty(e.target.value as Difficulty)}
            >
              <option value="direct">Direct</option>
              <option value="paraphrase">Paraphrase</option>
              <option value="deep_retrieval">Deep retrieval</option>
            </select>
          </label>
          <label>
            Retrieval K
            <input
              type="number"
              min={1}
              max={20}
              value={topK}
              onChange={(e) => setTopK(Number(e.target.value))}
            />
          </label>
        </div>
        <label className="checkbox-label">
          <input
            type="checkbox"
            checked={ack}
            onChange={(e) => setAck(e.target.checked)}
          />
          I understand this uses LLM tokens and may take several minutes.
        </label>
        <div className="form-row">
          <button
            className="button primary"
            disabled={
              !ack ||
              !!operation ||
              !Number.isInteger(size) ||
              size < 1 ||
              size > 25 ||
              !Number.isInteger(topK) ||
              topK < 1 ||
              topK > 20
            }
            onClick={() => mutation.mutate("run")}
          >
            Generate & evaluate <ArrowUpRight size={16} />
          </button>
          <button
            className="button ghost"
            disabled={
              !ack ||
              !!operation ||
              !Number.isInteger(size) ||
              size < 1 ||
              size > 25
            }
            onClick={() => mutation.mutate("generate")}
          >
            Generate questions only
          </button>
        </div>
        <p className="caption">
          Each action creates a new dataset. “Generate & evaluate” does not
          reuse a previously generated preview. No automatic runs or retries.
        </p>
      </section>
      {operation === "evaluation" && (
        <Pending text="Your knowledge is under examination" long />
      )}
      <ErrorNotice
        error={
          taskError?.task === "evaluation" ? taskError.error : mutation.error
        }
      />
      {report && (
        <section className="evaluation-report">
          <div className="section-label">
            <span>LATEST COMPLETED RUN · THIS SESSION</span>
            <Badge tone={report.dataset.complete ? "good" : "warn"}>
              {report.dataset.generated_cases}/{report.dataset.requested_cases}{" "}
              cases
            </Badge>
          </div>
          {report.dataset.generated_cases === 0 ? (
            <div className="notice warning">
              No evaluation cases were generated. Upload readable knowledge and
              check the provider before trying again. Zero-case metrics are not
              shown as quality scores.
            </div>
          ) : (
            <>
              <p className="caption">
                {report.dataset.difficulty} · K={report.dataset.top_k} ·
                Evaluator: {report.evaluation_configuration.evaluator_model} ·
                Average case latency {ms(report.summary.average_latency_ms)}
              </p>
              {!report.dataset.complete && (
                <p className="notice warning">
                  This run is incomplete. Metrics describe only the returned
                  cases.
                </p>
              )}
              <div className="metric-grid">
                {metrics.map(([key, label, description]) => (
                  <article className="metric-card" key={key}>
                    <span>{label}</span>
                    <strong>
                      {report.summary[key] === undefined
                        ? "Not reported"
                        : percent(report.summary[key])}
                    </strong>
                    <p>{description}</p>
                  </article>
                ))}
              </div>
              <p className="notice neutral">
                {report.summary.faithfulness >= 0.9
                  ? "Most extracted claims were judged supported in this run."
                  : "Some generated claims need closer inspection. Start with the individual cases below."}{" "}
                These are model-assisted evaluations, not guarantees of factual
                correctness.
              </p>
              <div className="section-label">
                <span>INDIVIDUAL INVESTIGATIONS</span>
                <span>{report.results.length} cases</span>
              </div>
              {report.results.map((c, i) => (
                <details className="case-card" key={`${c.case_id}-${i}`}>
                  <summary>
                    <span className="source-number">{i + 1}</span>
                    <strong>{c.question}</strong>
                    <Badge
                      tone={c.production_validation.valid ? "good" : "warn"}
                    >
                      {c.production_validation.valid
                        ? "Validator passed"
                        : "Review"}
                    </Badge>
                  </summary>
                  <div className="case-body">
                    <div className="case-answers">
                      <article>
                        <span className="eyebrow">REFERENCE ANSWER</span>
                        <p>{c.reference_answer}</p>
                      </article>
                      <article>
                        <span className="eyebrow">GENERATED ANSWER</span>
                        <p>{c.answer}</p>
                      </article>
                    </div>
                    <p>
                      <strong>Origin:</strong>{" "}
                      {c.ground_truth.originating_document} · Pages{" "}
                      {c.ground_truth.originating_pages.join(", ") ||
                        "not reported"}{" "}
                      · {ms(c.latency_ms)}
                    </p>
                    <h3>Claim judgments</h3>
                    {c.semantic_evaluation.claim_judgments.map((j, n) => (
                      <div className="claim-row" key={n}>
                        <Badge tone={j.supported ? "good" : "warn"}>
                          {j.supported ? "Supported" : "Unsupported"}
                        </Badge>
                        <p>{j.claim}</p>
                        <small>
                          Supporting source numbers:{" "}
                          {j.supporting_sources.join(", ") || "None"}
                        </small>
                      </div>
                    ))}
                    {!c.semantic_evaluation.claim_judgments.length && (
                      <p>No claim judgments returned.</p>
                    )}
                    <h3>Graded relevance</h3>
                    <div className="table-scroll">
                      <table>
                        <thead>
                          <tr>
                            <th>Chunk ID</th>
                            <th>Relevance grade</th>
                            <th>Relevant set</th>
                          </tr>
                        </thead>
                        <tbody>
                          {Object.entries(
                            c.ground_truth.relevance_judgments,
                          ).map(([id, grade]) => (
                            <tr key={id}>
                              <td>{id}</td>
                              <td>{grade}</td>
                              <td>
                                {c.ground_truth.relevant_chunk_ids.includes(id)
                                  ? "Included"
                                  : "Excluded"}
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                    <JsonDetails
                      label="All returned case metrics and source identifiers"
                      value={c}
                    />
                  </div>
                </details>
              ))}
            </>
          )}
          <JsonDetails label="Full evaluation report" value={report} />
        </section>
      )}
      {dataset && (
        <section className="panel">
          <div className="section-label">
            <span>LATEST GENERATED QUESTION PREVIEW</span>
            <Badge>
              {dataset.generated_cases}/{dataset.requested_cases}
            </Badge>
          </div>
          <p className="caption">
            This preview is separate from the evaluation run above.
          </p>
          {!dataset.cases.length && <p>No questions were generated.</p>}
          {dataset.cases.map((c, i) => (
            <details className="case-card" key={`${c.id}-${i}`}>
              <summary>{c.question}</summary>
              <div className="case-body">
                <h3>Reference answer</h3>
                <p>{c.reference_answer}</p>
                <h3>Originating evidence</h3>
                <p>
                  {c.source_document} · Pages{" "}
                  {c.source_pages.join(", ") || "not reported"}
                </p>
                {c.evidence.map((e, n) => (
                  <blockquote key={n}>{e}</blockquote>
                ))}
                <JsonDetails value={c} />
              </div>
            </details>
          ))}
        </section>
      )}
      {!report && !dataset && operation !== "evaluation" && (
        <div className="quiet-empty">
          <FlaskConical size={22} />
          <p>No evaluations yet. Quality starts with a real test.</p>
        </div>
      )}
    </>
  );
}
