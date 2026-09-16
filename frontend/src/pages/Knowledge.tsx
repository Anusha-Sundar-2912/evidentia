import { useRef, useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { Upload, FileText, ArrowUpRight } from "lucide-react";
import { api } from "../api/client";
import { useReceipts } from "../hooks/useReceipts";
import { useWorkspace, updateWorkspace } from "../store/workspace";
import {
  Badge,
  PageHeading,
  ErrorNotice,
  Pending,
} from "../components/ui/Common";
export default function Knowledge() {
  const { receipts, add } = useReceipts();
  const { operation, taskError } = useWorkspace();
  const input = useRef<HTMLInputElement>(null);
  const [drag, setDrag] = useState(false);
  const [invalid, setInvalid] = useState<string>();
  const [name, setName] = useState("");
  const mutation = useMutation({
    mutationKey: ["upload"],
    mutationFn: api.upload,
    onMutate: (f) => {
      setName(f.name);
      updateWorkspace({
        taskError: undefined,
        operation: "upload",
        evi: "thinking",
      });
    },
    onSuccess: (r) => {
      add(r);
      updateWorkspace({ evi: "success" });
    },
    onError: (e) =>
      updateWorkspace({
        evi: "error",
        taskError: { task: "upload", error: e },
      }),
    onSettled: () => updateWorkspace({ operation: undefined }),
  });
  function upload(files: FileList | null) {
    if (operation || !files?.length) return;
    setInvalid(undefined);
    if (files.length > 1) {
      setInvalid("Please upload one document at a time.");
      return;
    }
    const file = files[0];
    if (!/\.(pdf|docx)$/i.test(file.name)) {
      setInvalid("Choose a PDF or DOCX document.");
      return;
    }
    mutation.mutate(file);
  }
  return (
    <>
      <PageHeading
        eyebrow="THE KNOWLEDGE COLLECTION"
        title="A place for what you know."
      >
        Your knowledge, structured for retrieval.
      </PageHeading>
      <section
        className={`upload-zone ${drag ? "dragging" : ""}`}
        onDragOver={(e) => {
          e.preventDefault();
          setDrag(true);
        }}
        onDragLeave={() => setDrag(false)}
        onDrop={(e) => {
          e.preventDefault();
          setDrag(false);
          upload(e.dataTransfer.files);
        }}
      >
        <div className="upload-orbit">
          <Upload size={27} />
        </div>
        <span className="eyebrow">THE BEGINNING OF EVERY ANSWER</span>
        <h2>Drop a little knowledge here.</h2>
        <p>Reports, research, policies. Bring the context that matters.</p>
        <button
          className="button primary"
          disabled={!!operation}
          onClick={() => input.current?.click()}
        >
          Choose a document <ArrowUpRight size={16} />
        </button>
        <input
          className="sr-only"
          tabIndex={-1}
          aria-label="Upload document"
          ref={input}
          type="file"
          accept=".pdf,.docx"
          onChange={(e) => {
            upload(e.target.files);
            e.target.value = "";
          }}
        />
        <small>PDF or DOCX · One document at a time</small>
      </section>
      {invalid && <ErrorNotice error={new Error(invalid)} />}
      <ErrorNotice
        error={taskError?.task === "upload" ? taskError.error : mutation.error}
      />
      {operation === "upload" && (
        <Pending
          text={
            name
              ? `Uploading and processing ${name}`
              : "Uploading and processing your document"
          }
        />
      )}{" "}
      {mutation.isSuccess && (
        <div className="notice good">
          <div>
            <strong>Knowledge indexed.</strong>
            <p>
              {mutation.data.filename} · {mutation.data.chunk_count} chunks
            </p>
          </div>
          <Link to="/ask" className="text-link">
            Ask your first question ↗
          </Link>
        </div>
      )}
      <div className="section-label">
        <span>CONFIRMED UPLOADS IN THIS BROWSER</span>
        <span>{receipts.length} receipts</span>
      </div>
      <p className="caption">
        These are saved upload receipts, not a live inventory. Documents
        uploaded elsewhere may still be available to Ask. Current backend status
        cannot be refreshed.
      </p>
      {receipts.length ? (
        <div className="document-list">
          {receipts.map((r) => (
            <article className="document-row" key={r.id}>
              <div className="file-icon">
                <FileText />
              </div>
              <div>
                <h3>{r.filename}</h3>
                <p>
                  {r.source_type.toUpperCase()} · {r.chunk_count} chunks ·{" "}
                  {new Date(r.created_at).toLocaleString()}
                </p>
              </div>
              <Badge tone={r.status === "ready" ? "good" : "warn"}>
                {r.status} at upload
              </Badge>
            </article>
          ))}
        </div>
      ) : (
        <div className="quiet-empty">
          <FileText size={20} />
          <p>
            No upload receipts yet. Your first document starts the collection.
          </p>
        </div>
      )}
    </>
  );
}
