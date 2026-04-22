"use client";

import { useMemo, useState } from "react";

import { adminApiClient } from "@/lib/admin-api-client";
import type { AdminConfigResponse, AdminConfigPatch } from "@/types/admin";

interface WebhookConfigSectionProps {
  config: AdminConfigResponse;
  patch: AdminConfigPatch;
  onPatch: (updates: AdminConfigPatch) => void;
}

export function WebhookConfigSection({
  config,
  patch,
  onPatch,
}: WebhookConfigSectionProps) {
  const [testState, setTestState] = useState<"idle" | "sending" | "success" | "error">("idle");
  const [testMessage, setTestMessage] = useState<string | null>(null);
  const url =
    patch.notifications_webhook_url !== undefined
      ? (patch.notifications_webhook_url ?? "")
      : (config.notifications_webhook_url ?? "");
  const samplePayload = useMemo(
    () => ({
      event: "SYNC_SUCCESS",
      status: "success",
      trigger: "scheduled",
      sent_at: "2026-04-22T13:00:00Z",
      records_processed: 128,
      duration_seconds: 47,
      started_at: "2026-04-22T12:59:13Z",
      finished_at: "2026-04-22T13:00:00Z",
      snapshots_generated: 3,
      collectors: {
        gitlab: {
          status: "SUCCESS",
          records_processed: {
            repositories: 12,
            releases: 62,
            merge_requests: 392,
          },
        },
        jira: {
          status: "SUCCESS",
          records_processed: {
            bugs: 81,
            mttr_alpha_resolved: 33,
          },
        },
      },
      errors: [],
      metadata: {},
    }),
    []
  );

  const handleSendTestWebhook = async () => {
    setTestState("sending");
    setTestMessage(null);
    try {
      const body =
        url.trim().length > 0
          ? { webhook_url: url.trim() }
          : { webhook_url: null };
      const res = await adminApiClient.testWebhook(body);
      setTestState("success");
      if (res.delivered) {
        setTestMessage(`Test webhook delivered to ${res.effective_webhook_url}`);
      } else {
        setTestMessage(`Webhook request sent but endpoint returned a non-2xx response`);
      }
    } catch (error) {
      setTestState("error");
      setTestMessage(error instanceof Error ? error.message : "Failed to send test webhook");
    }
  };

  return (
    <section className="bg-surface-container-low p-8 rounded-2xl">
      <div className="flex items-start gap-6">
        <div className="w-12 h-12 bg-surface-container-lowest rounded-xl flex items-center justify-center shrink-0 shadow-sm">
          <span className="material-symbols-outlined text-primary text-2xl leading-none">
            webhook
          </span>
        </div>
        <div className="flex-1 min-w-0">
          <h2 className="text-lg font-editorial font-bold tracking-tight text-on-surface mb-1">
            Notifications Webhook
          </h2>
          <p className="text-sm text-on-surface-variant mb-6">
            Optional URL to receive sync completion and failure notifications.
          </p>
          <div className="space-y-2">
            <label
              htmlFor="notifications_webhook_url"
              className="text-[10px] font-editorial font-bold uppercase tracking-[0.1em] text-outline px-1 block"
            >
              Webhook URL
            </label>
            <input
              id="notifications_webhook_url"
              type="url"
              value={url}
              onChange={(e) =>
                onPatch({
                  notifications_webhook_url: e.target.value || null,
                })
              }
              placeholder="https://hooks.slack.com/services/…"
              className="w-full px-4 py-3 bg-surface-container border-b-2 border-transparent focus:bg-surface-container-lowest focus:border-primary focus:outline-none transition-all font-body text-sm text-on-surface placeholder:text-outline"
            />
          </div>
          <div className="mt-6 space-y-3">
            <div className="flex items-center justify-between gap-3">
              <h3 className="text-xs font-editorial font-bold uppercase tracking-[0.1em] text-outline">
                Sample Payload
              </h3>
              <button
                type="button"
                onClick={handleSendTestWebhook}
                disabled={testState === "sending"}
                className="flex items-center gap-2 px-4 py-2 rounded-lg bg-primary text-on-primary text-xs font-editorial font-bold uppercase tracking-wider hover:opacity-90 disabled:opacity-50 disabled:cursor-not-allowed transition-all"
              >
                <span
                  className={`material-symbols-outlined text-sm leading-none ${testState === "sending" ? "animate-spin" : ""}`}
                >
                  {testState === "sending" ? "autorenew" : "send"}
                </span>
                {testState === "sending" ? "Sending..." : "Send Test Webhook"}
              </button>
            </div>
            <pre className="w-full overflow-auto rounded-xl bg-surface-container-lowest p-4 text-xs text-on-surface font-mono leading-relaxed border border-outline-variant">
              {JSON.stringify(samplePayload, null, 2)}
            </pre>
            {testMessage && (
              <p
                className={`text-xs font-editorial ${testState === "error" ? "text-error" : "text-on-surface-variant"}`}
                role={testState === "error" ? "alert" : "status"}
              >
                {testMessage}
              </p>
            )}
          </div>
        </div>
      </div>
    </section>
  );
}
