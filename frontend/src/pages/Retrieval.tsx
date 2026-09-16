import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { useWorkspace } from "../store/workspace";
import { api } from "../api/client";
import { TraceExplorer } from "../components/retrieval/TraceExplorer";
import {
  PageHeading,
  Empty,
  ErrorNotice,
  Pending,
  Badge,
} from "../components/ui/Common";
export default function Retrieval() {
  const { result } = useWorkspace();
  const [query, setQuery] = useState("");
  const [mode, setMode] = useState<"semantic" | "bm25" | "hybrid">("hybrid");
  const search = useMutation({
    mutationFn: () => api.search(mode, { query, top_k: 5 }),
  });
  return (
    <>
      <PageHeading eyebrow="RETRIEVAL LAB" title="Every answer has a story.">
        Don’t just trust the answer. Inspect how it was found.
      </PageHeading>
      {result ? (
        <TraceExplorer result={result} />
      ) : (
        <Empty
          title="The trail begins with a question."
          to="/ask"
          label="Ask a question"
        >
          Your latest answer’s real retrieval trace will appear here.
        </Empty>
      )}
      <section className="panel search-lab">
        <span className="eyebrow">AN INDEPENDENT EXPERIMENT</span>
        <h2>Look directly into your knowledge.</h2>
        <p>
          Search returns real passages. This is a new retrieval request, not the
          candidate set behind your previous answer.
        </p>
        <form
          className="form-row"
          onSubmit={(e) => {
            e.preventDefault();
            search.mutate();
          }}
        >
          <label className="grow">
            Search query
            <input
              minLength={2}
              required
              value={query}
              onChange={(e) => setQuery(e.target.value)}
            />
          </label>
          <label>
            Method
            <select
              value={mode}
              onChange={(e) => setMode(e.target.value as typeof mode)}
            >
              <option value="hybrid">Hybrid + reranking</option>
              <option value="semantic">Semantic</option>
              <option value="bm25">BM25 keywords</option>
            </select>
          </label>
          <button className="button primary" disabled={search.isPending}>
            Search passages
          </button>
        </form>
        <ErrorNotice error={search.error} />
        {search.isPending && <Pending text="Searching passages" />}
        {search.data && (
          <div className="search-results">
            <p className="caption">
              Returned mode: {search.data.mode} · Query: {search.data.query}
            </p>
            {!search.data.results.length && (
              <p>No matching passages were returned.</p>
            )}
            {search.data.results.map((r, i) => (
              <article className="passage" key={r.chunk_id}>
                <header>
                  <strong>
                    {i + 1}. {r.filename}
                  </strong>
                  <Badge>
                    {r.page_number !== null
                      ? `Page ${r.page_number}`
                      : "No page"}
                  </Badge>
                </header>
                <p>{r.content}</p>
                <small>
                  Score {r.score}{" "}
                  {r.reranker_score !== null && r.reranker_score !== undefined
                    ? `· Reranker ${r.reranker_score}`
                    : ""}{" "}
                  · Chunk {r.chunk_id}
                </small>
              </article>
            ))}
          </div>
        )}
      </section>
    </>
  );
}
