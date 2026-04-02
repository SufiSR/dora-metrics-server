"use client";

import { create } from "zustand";

export type PeriodType = "30d" | "quarterly" | "yearly";
export type ThemeMode = "light" | "dark" | "system";

interface UIState {
  period: PeriodType;
  setPeriod: (p: PeriodType) => void;

  activeMetricModal: string | null;
  openMetricModal: (metricKey: string) => void;
  closeMetricModal: () => void;
}

export const useUIStore = create<UIState>()((set) => ({
  period: "30d",
  setPeriod: (p) => set({ period: p }),

  activeMetricModal: null,
  openMetricModal: (metricKey) => set({ activeMetricModal: metricKey }),
  closeMetricModal: () => set({ activeMetricModal: null }),
}));
