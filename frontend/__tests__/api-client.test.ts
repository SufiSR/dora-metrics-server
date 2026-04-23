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
      expect.stringContaining("/metrics/current?period_type=WEEK"),
      expect.any(Object)
    );
    expect(result.generated_at).toEqual(mockData.generated_at);
    expect(result).toHaveProperty("deployment_frequency");
    expect(result).toHaveProperty("lead_time_for_changes");
  });

  it("getMetricsHistory calls correct endpoint with period", async () => {
    const mockData = { period: "quarterly", data_points: [] };
    global.fetch = jest.fn().mockResolvedValue({
      ok: true,
      json: async () => mockData,
    } as Response);

    const result = await apiClient.getMetricsHistory("quarterly");

    expect(global.fetch).toHaveBeenCalledWith(
      expect.stringContaining("/metrics/history?period_type=MONTH"),
      expect.any(Object)
    );
    expect(result).toEqual(mockData);
  });

  it("maps lead-time split fields from history minutes to hours", async () => {
    global.fetch = jest.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        data: [
          {
            period_end: "2026-04-20",
            lead_time_minutes: 240,
            dev_review_median_minutes: 90,
            release_wait_median_minutes: 150,
          },
        ],
      }),
    } as Response);

    const result = await apiClient.getMetricsHistory("30d");
    expect(result.data_points[0].lead_time_for_changes).toBe(4);
    expect(result.data_points[0].lead_time_dev_review_hours).toBe(1.5);
    expect(result.data_points[0].lead_time_release_wait_hours).toBe(2.5);
  });

  it("scales stacked dev/wait so hours sum to median total lead (DEVOPS-515)", async () => {
    global.fetch = jest.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        data: [
          {
            period_end: "2026-04-20",
            lead_time_minutes: 300,
            dev_review_median_minutes: 60,
            release_wait_median_minutes: 60,
          },
        ],
      }),
    } as Response);

    const result = await apiClient.getMetricsHistory("30d");
    expect(result.data_points[0].lead_time_for_changes).toBe(5);
    expect(result.data_points[0].lead_time_dev_review_hours).toBeCloseTo(2.5);
    expect(result.data_points[0].lead_time_release_wait_hours).toBeCloseTo(2.5);
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

  it("includes pipeline_runtime when sync status provides it", async () => {
    const mockData = {
      last_sync: null,
      last_successful_sync_at: null,
      next_scheduled_sync: null,
      sync_schedule_cron: "0 2 * * *",
      pipeline_in_progress: true,
      pipeline_run_started_at: "2026-04-14T09:21:14.010690Z",
      pipeline_run_trigger: "manual",
      pipeline_runtime: {
        current_phase: "jira",
        phase_started_at: "2026-04-14T09:22:00Z",
        phases: {
          gitlab: { status: "success", records_processed: {} },
          jira: { status: "running", records_processed: {} },
          derivations: { status: "pending", records_processed: {} },
          snapshots: { status: "pending", records_processed: {} },
          complete: { status: "pending", records_processed: {} },
        },
        errors: [],
      },
    };
    global.fetch = jest.fn().mockResolvedValue({
      ok: true,
      json: async () => mockData,
    } as Response);

    const result = await apiClient.getSyncStatus();
    expect(result.pipeline_runtime?.current_phase).toBe("jira");
    expect(result.pipeline_runtime?.phases.jira.status).toBe("running");
  });

  it("uses release wait as primary lead-time KPI and keeps split context", async () => {
    global.fetch = jest.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        generated_at: "2026-04-23T09:00:00Z",
        period_end: "2026-04-23",
        lead_time: { value: 240, performance_level: "HIGH", trend_percentage: 0 },
        release_wait_time: { value: 180, performance_level: "HIGH", trend_percentage: 0 },
        dev_review_time: { value: 60, performance_level: "HIGH", trend_percentage: 0 },
      }),
    } as Response);

    const result = await apiClient.getMetricsCurrent("30d");
    expect(result.lead_time_for_changes.value).toBe(3);
    expect(result.lead_time_for_changes.secondary_text).toContain("Total lead 4.0h");
    expect(result.lead_time_for_changes.secondary_text).toContain("dev/review 1.0h");
  });
});
