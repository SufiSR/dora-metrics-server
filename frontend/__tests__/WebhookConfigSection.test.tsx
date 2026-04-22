import React from "react";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";

import { WebhookConfigSection } from "@/app/components/admin/WebhookConfigSection";
import { adminApiClient } from "@/lib/admin-api-client";

jest.mock("@/lib/admin-api-client", () => ({
  adminApiClient: {
    testWebhook: jest.fn(),
  },
}));

const testWebhookMock = adminApiClient.testWebhook as jest.Mock;

describe("WebhookConfigSection", () => {
  const baseConfig = {
    notifications_webhook_url: "https://hooks.example.test/saved",
  };

  it("renders sample payload preview", () => {
    render(
      <WebhookConfigSection
        config={baseConfig as any}
        patch={{}}
        onPatch={() => {}}
      />
    );
    expect(screen.getByText(/Sample Payload/i)).toBeTruthy();
    expect(screen.getByText(/SYNC_SUCCESS/)).toBeTruthy();
  });

  it("sends test webhook with typed URL", async () => {
    testWebhookMock.mockResolvedValueOnce({
      delivered: true,
      effective_webhook_url: "https://hooks.example.test/draft",
      payload: { event: "SYNC_TEST" },
    });
    const onPatch = jest.fn();
    render(
      <WebhookConfigSection
        config={baseConfig as any}
        patch={{ notifications_webhook_url: "https://hooks.example.test/draft" }}
        onPatch={onPatch}
      />
    );

    fireEvent.click(screen.getByRole("button", { name: /send test webhook/i }));
    await waitFor(() => expect(testWebhookMock).toHaveBeenCalledTimes(1));
    expect(testWebhookMock).toHaveBeenCalledWith({
      webhook_url: "https://hooks.example.test/draft",
    });
  });
});
