import { useSyncExternalStore } from "react";
import type { AskResponse, InputGuardrail } from "../types/api";
export type EviState =
  | "idle"
  | "greeting"
  | "guiding"
  | "listening"
  | "thinking"
  | "searching"
  | "retrieving"
  | "reranking"
  | "verifying"
  | "success"
  | "curious"
  | "warning"
  | "blocked"
  | "error"
  | "sleeping";
interface Workspace {
  result?: AskResponse;
  blocked?: InputGuardrail;
  conversationId?: string;
  evi: EviState;
  operation?: "upload" | "query" | "evaluation";
  selectedCitation?: number;
  taskError?: { task: "query" | "upload" | "evaluation"; error: Error };
}
let state: Workspace = { evi: "idle" };
const listeners = new Set<() => void>();
export function updateWorkspace(patch: Partial<Workspace>) {
  state = { ...state, ...patch };
  listeners.forEach((fn) => fn());
}
export function useWorkspace() {
  return useSyncExternalStore(
    (fn) => {
      listeners.add(fn);
      return () => listeners.delete(fn);
    },
    () => state,
  );
}
export function newInvestigation() {
  updateWorkspace({
    result: undefined,
    blocked: undefined,
    conversationId: undefined,
    selectedCitation: undefined,
    taskError: undefined,
    evi: "curious",
  });
}
