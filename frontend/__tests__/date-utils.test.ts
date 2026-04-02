import { formatDistanceToNow, isOlderThan, formatDateTime } from "@/lib/date-utils";

describe("formatDistanceToNow", () => {
  beforeEach(() => {
    jest.useFakeTimers();
    jest.setSystemTime(new Date("2026-04-02T12:00:00Z").getTime());
  });
  afterEach(() => jest.useRealTimers());

  it("returns seconds ago", () => {
    expect(formatDistanceToNow("2026-04-02T11:59:30Z")).toBe("30s ago");
  });

  it("returns minutes ago", () => {
    expect(formatDistanceToNow("2026-04-02T11:55:00Z")).toBe("5m ago");
  });

  it("returns hours ago", () => {
    expect(formatDistanceToNow("2026-04-02T09:00:00Z")).toBe("3h ago");
  });

  it("returns days ago", () => {
    expect(formatDistanceToNow("2026-03-31T12:00:00Z")).toBe("2d ago");
  });
});

describe("isOlderThan", () => {
  beforeEach(() => {
    jest.useFakeTimers();
    jest.setSystemTime(new Date("2026-04-02T12:00:00Z").getTime());
  });
  afterEach(() => jest.useRealTimers());

  it("returns true when older than threshold", () => {
    const threshold = 1000 * 60 * 60; // 1 hour
    expect(isOlderThan("2026-04-02T10:00:00Z", threshold)).toBe(true);
  });

  it("returns false when within threshold", () => {
    const threshold = 1000 * 60 * 60; // 1 hour
    expect(isOlderThan("2026-04-02T11:30:00Z", threshold)).toBe(false);
  });
});

describe("formatDateTime", () => {
  it("returns a non-empty string for a valid ISO date", () => {
    const result = formatDateTime("2026-04-02T12:00:00Z");
    expect(typeof result).toBe("string");
    expect(result.length).toBeGreaterThan(0);
  });
});
