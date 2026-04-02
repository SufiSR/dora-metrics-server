"use client";

import { PeriodSelector } from "./PeriodSelector";
import { SyncStatusPill } from "./SyncStatusPill";
import { ThemeToggle } from "../ui/ThemeToggle";

export function HeaderBar() {
  return (
    <header className="bg-surface-container-lowest/80 backdrop-blur-xl w-full top-0 sticky z-50 border-b border-outline-variant/10 transition-colors duration-200">
      <div className="flex items-center justify-between px-6 py-3 w-full max-w-[1440px] mx-auto">
        {/* Left: Brand + Period selector */}
        <div className="flex items-center gap-8">
          <span className="text-xl font-editorial font-bold tracking-tighter text-primary select-none">
            DORA Metrics
          </span>
          <PeriodSelector />
        </div>

        {/* Right: Sync status + Theme toggle */}
        <div className="flex items-center gap-3">
          <SyncStatusPill />
          <ThemeToggle />
        </div>
      </div>
    </header>
  );
}
