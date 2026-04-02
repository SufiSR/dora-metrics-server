import { apiClient } from "@/lib/api-client";

describe("apiClient", () => {
  const originalFetch = global.fetch;

  afterEach(() => {
    global.fetch = originalFetch;
    jest.resetAllMocks();
  });

  it("getMetricsCurrent calls correct endpoint with period", async () => {
    const mockData = { generated_at: "2026-04-02T00:00:00Z" };
    global.fetch = jest.fn().mockResolvedValue({
      ok: true,
      json: async () => mockData,
    } as Response);

    const result = await apiClient.getMetricsCurrent("30d");

    expect(global.fetch).toHaveBeenCalledWith(
      expect.stringContaining("/metrics/current?period=30d"),
      expect.any(Object)
    );
    expect(result).toEqual(mockData);
  });

  it("getMetricsHistory calls correct endpoint with period", async () => {
    const mockData = { period: "quarterly", data_points: [] };
    global.fetch = jest.fn().mockResolvedValue({
      ok: true,
      json: async () => mockData,
    } as Response);

    const result = await apiClient.getMetricsHistory("quarterly");

    expect(global.fetch).toHaveBeenCalledWith(
      expect.stringContaining("/metrics/history?period=quarterly"),
      expect.any(Object)
    );
    expect(result).toEqual(mockData);
  });

  it("throws on non-OK response with detail", async () => {
    global.fetch = jest.fn().mockResolvedValue({
      ok: false,
      status: 503,
      json: async () => ({ detail: "Service unavailable" }),
    } as Response);

    await expect(apiClient.getSyncStatus()).rejects.toThrow("Service unavailable");
  });

  it("throws HTTP status message when body parse fails", async () => {
    global.fetch = jest.fn().mockResolvedValue({
      ok: false,
      status: 500,
      json: async () => { throw new Error("no body"); },
    } as unknown as Response);

    await expect(apiClient.getSyncStatus()).rejects.toThrow("HTTP 500");
  });
});
