import { useUIStore } from "@/lib/store";

describe("useUIStore", () => {
  beforeEach(() => {
    useUIStore.setState({
      period: "30d",
      activeMetricModal: null,
    });
  });

  it("defaults to 30d period", () => {
    expect(useUIStore.getState().period).toBe("30d");
  });

  it("setPeriod updates period", () => {
    useUIStore.getState().setPeriod("yearly");
    expect(useUIStore.getState().period).toBe("yearly");
  });

  it("openMetricModal sets activeMetricModal", () => {
    useUIStore.getState().openMetricModal("deployment_frequency");
    expect(useUIStore.getState().activeMetricModal).toBe("deployment_frequency");
  });

  it("closeMetricModal clears activeMetricModal", () => {
    useUIStore.getState().openMetricModal("mttr_alpha");
    useUIStore.getState().closeMetricModal();
    expect(useUIStore.getState().activeMetricModal).toBeNull();
  });
});
