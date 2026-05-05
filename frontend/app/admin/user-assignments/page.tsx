"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { adminApiClient } from "@/lib/admin-api-client";
import type { AdminConfigResponse, WorklogAuthorListItem, WorklogRole } from "@/types/admin";

type RoleSelect = WorklogRole | "";

type DraftRow = { role: RoleSelect; team: string; jira_account_id: string | null; author: string | null };

function draftKey(accountId: string | null, author: string | null): string {
  if (accountId && accountId.trim()) return `aid:${accountId.trim()}`;
  if (author && author.trim()) return `author:${author.trim().toLowerCase()}`;
  return "unknown:";
}

export default function UserAssignmentsPage() {
  const router = useRouter();
  const [config, setConfig] = useState<AdminConfigResponse | null>(null);
  const [authors, setAuthors] = useState<WorklogAuthorListItem[]>([]);
  const [authorsError, setAuthorsError] = useState<string | null>(null);
  const [draftByKey, setDraftByKey] = useState<Record<string, DraftRow>>({});
  const [denylistText, setDenylistText] = useState("");
  const [saveState, setSaveState] = useState<"idle" | "saving" | "success" | "error">("idle");
  const [saveError, setSaveError] = useState<string | null>(null);

  useEffect(() => {
    (async () => {
      try {
        const me = await adminApiClient.me();
        if (me.role !== "admin") {
          router.push("/admin/login");
          return;
        }
        const cfg = await adminApiClient.getConfig();
        setConfig(cfg);
        const m: Record<string, DraftRow> = {};
        for (const a of cfg.jira_worklog_user_assignments) {
          const key = draftKey(a.jira_account_id ?? null, a.author ?? null);
          if (key !== "unknown:") {
            m[key] = {
              role: a.role,
              team: a.team,
              jira_account_id: a.jira_account_id ?? null,
              author: a.author ?? null,
            };
          }
        }
        setDraftByKey(m);
        setDenylistText(cfg.jira_worklog_author_denylist.join("\n"));
        try {
          const authorPage = await adminApiClient.getWorklogAuthors({ page: 0, size: 500 });
          setAuthors(authorPage.items);
          setAuthorsError(null);
        } catch (err) {
          setAuthorsError(err instanceof Error ? err.message : "Failed to load worklog authors");
        }
      } catch {
        router.push("/admin/login");
      }
    })();
  }, [router]);

  const updateDraft = useCallback((key: string, next: DraftRow) => {
    setDraftByKey((prev) => ({ ...prev, [key]: next }));
    setSaveState("idle");
  }, []);

  const tableRows = useMemo(() => {
    const keysFromAuthors = new Set(
      authors.map((a) => draftKey(a.jira_account_id ?? null, a.author ?? null)),
    );
    const orphanIds = Object.keys(draftByKey).filter((id) => !keysFromAuthors.has(id));
    const synthetic: WorklogAuthorListItem[] = orphanIds.map((id) => {
      const d = draftByKey[id];
      return { jira_account_id: d?.jira_account_id ?? null, author: d?.author ?? null };
    });
    const combined = [...authors, ...synthetic];
    combined.sort((a, b) => {
      const an = (a.author ?? "").toLowerCase();
      const bn = (b.author ?? "").toLowerCase();
      if (an !== bn) return an.localeCompare(bn);
      return (a.jira_account_id ?? "").localeCompare(b.jira_account_id ?? "");
    });
    return combined;
  }, [authors, draftByKey]);

  const handleSave = useCallback(async () => {
    if (!config) return;
    const assignments = Object.values(draftByKey)
      .filter(
        (row) =>
          row.role &&
          ((row.jira_account_id && row.jira_account_id.trim()) || (row.author && row.author.trim())),
      )
      .map((row) => ({
        jira_account_id: row.jira_account_id,
        author: row.author,
        role: row.role as WorklogRole,
        team: row.team.trim(),
      }));
    const denylist = denylistText
      .split("\n")
      .map((s) => s.trim())
      .filter(Boolean);
    setSaveState("saving");
    setSaveError(null);
    try {
      const updated = await adminApiClient.patchConfig({
        jira_worklog_user_assignments: assignments,
        jira_worklog_author_denylist: denylist,
      });
      setConfig(updated);
      const authorPage = await adminApiClient.getWorklogAuthors({ page: 0, size: 500 });
      setAuthors(authorPage.items);
      setAuthorsError(null);
      setSaveState("success");
      setTimeout(() => setSaveState("idle"), 2500);
    } catch (err) {
      setSaveState("error");
      setSaveError(err instanceof Error ? err.message : "Save failed");
    }
  }, [config, draftByKey, denylistText]);

  if (!config) {
    return (
      <main className="pl-72 pr-10 py-10 text-on-surface-variant text-sm font-editorial">
        Loading…
      </main>
    );
  }

  return (
    <main className="pl-72 pr-10 py-10 max-w-5xl space-y-8">
      <header>
        <h1 className="text-2xl font-editorial font-bold text-on-surface tracking-tight">
          User assignments
        </h1>
        <p className="text-sm text-on-surface-variant mt-2 max-w-2xl">
          Map Jira worklog authors (by account ID) to PM, DEV, or QA and a team label. Only rows with
          a Jira account ID can be persisted. Saved denylist IDs are excluded from author discovery and from
          public worklog aggregates.
        </p>
      </header>

      <section className="rounded-xl border border-outline-variant/50 bg-surface-container-lowest p-6 space-y-4">
        <h2 className="text-sm font-editorial font-semibold text-on-surface">Author denylist</h2>
        <p className="text-xs text-on-surface-variant">
          One Jira account ID per line (typically automation/service accounts).
        </p>
        <textarea
          className="w-full min-h-[100px] rounded-lg border border-outline-variant bg-surface-container px-3 py-2 text-sm font-mono text-on-surface"
          value={denylistText}
          onChange={(e) => setDenylistText(e.target.value)}
          spellCheck={false}
        />
      </section>

      <section className="rounded-xl border border-outline-variant/50 bg-surface-container-lowest p-6 space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <h2 className="text-sm font-editorial font-semibold text-on-surface">
            Assignments ({tableRows.length} rows)
          </h2>
          <button
            type="button"
            onClick={() => handleSave()}
            disabled={saveState === "saving"}
            className="px-4 py-2 rounded-lg bg-primary text-on-primary text-sm font-editorial font-medium disabled:opacity-50"
          >
            {saveState === "saving" ? "Saving…" : "Save"}
          </button>
        </div>
        {authorsError && <p className="text-xs text-error">{authorsError}</p>}
        {saveState === "success" && (
          <p className="text-xs text-secondary">Saved configuration.</p>
        )}
        {saveError && <p className="text-xs text-error">{saveError}</p>}
        <div className="overflow-x-auto">
          <table className="w-full text-xs text-left border-collapse">
            <thead>
              <tr className="border-b border-outline-variant/60 text-on-surface-variant uppercase tracking-wider">
                <th className="py-2 pr-3 font-medium">Account ID</th>
                <th className="py-2 pr-3 font-medium">Display name</th>
                <th className="py-2 pr-3 font-medium">Role</th>
                <th className="py-2 pr-3 font-medium">Team</th>
              </tr>
            </thead>
            <tbody>
              {tableRows.map((row) => {
                const aid = row.jira_account_id ?? null;
                const author = row.author ?? null;
                const key = draftKey(aid, author);
                const draft =
                  draftByKey[key] ??
                  ({
                    role: "" as RoleSelect,
                    team: "",
                    jira_account_id: aid,
                    author,
                  } satisfies DraftRow);
                const editable = key !== "unknown:";
                return (
                  <tr key={key} className="border-b border-outline-variant/30">
                    <td className="py-2 pr-3 font-mono text-[11px] break-all">{aid || "—"}</td>
                    <td className="py-2 pr-3">{row.author ?? "—"}</td>
                    <td className="py-2 pr-3">
                      {editable ? (
                        <select
                          className="rounded border border-outline-variant bg-surface-container px-2 py-1 text-on-surface"
                          value={draft.role}
                          onChange={(e) =>
                            updateDraft(key, {
                              role: e.target.value as RoleSelect,
                              team: draft.team,
                              jira_account_id: draft.jira_account_id,
                              author: draft.author,
                            })
                          }
                        >
                          <option value="">Unset</option>
                          <option value="pm">PM</option>
                          <option value="dev">DEV</option>
                          <option value="qa">QA</option>
                        </select>
                      ) : (
                        <span className="text-on-surface-variant">N/A</span>
                      )}
                    </td>
                    <td className="py-2 pr-3">
                      {editable ? (
                        <input
                          type="text"
                          className="w-full min-w-[120px] rounded border border-outline-variant bg-surface-container px-2 py-1 text-on-surface"
                          value={draft.team}
                          onChange={(e) =>
                            updateDraft(key, {
                              role: draft.role,
                              team: e.target.value,
                              jira_account_id: draft.jira_account_id,
                              author: draft.author,
                            })
                          }
                          placeholder="Team name"
                        />
                      ) : (
                        <span className="text-on-surface-variant">—</span>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </section>
    </main>
  );
}
