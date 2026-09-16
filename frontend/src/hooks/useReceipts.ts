import { useQuery, useQueryClient } from "@tanstack/react-query";
import type { DocumentReceipt } from "../types/api";
import { API_BASE } from "../api/client";
const key = `evidentia.upload-receipts.v1:${API_BASE}`;
function read(): DocumentReceipt[] {
  try {
    const value = JSON.parse(localStorage.getItem(key) || "[]");
    return Array.isArray(value)
      ? value.filter(
          (v) =>
            typeof v.id === "string" &&
            typeof v.filename === "string" &&
            typeof v.chunk_count === "number",
        )
      : [];
  } catch {
    return [];
  }
}
export function useReceipts() {
  const client = useQueryClient();
  const { data: receipts = [] } = useQuery({
    queryKey: ["upload-receipts", API_BASE],
    queryFn: read,
    staleTime: Infinity,
  });
  function add(receipt: DocumentReceipt) {
    const next = [receipt, ...read().filter((x) => x.id !== receipt.id)];
    try {
      localStorage.setItem(key, JSON.stringify(next));
    } catch {
      /* In-memory receipt remains usable when storage is unavailable. */
    }
    client.setQueryData(["upload-receipts", API_BASE], next);
  }
  return { receipts, add };
}
