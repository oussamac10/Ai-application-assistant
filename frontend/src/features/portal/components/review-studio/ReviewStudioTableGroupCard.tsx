"use client";

import React, { useState } from "react";
import {
  ChevronDown,
  ChevronRight,
  CopyCheck,
  Loader2,
  Table2,
} from "lucide-react";
import type { FormFieldItem } from "../../types";

export interface TableGroupRow {
  rowIndex: number;
  rowLabel: string;
  fields: Array<{ field: FormFieldItem; globalIndex: number }>;
}

export interface ReviewStudioTableGroupCardProps {
  tableKey: string;
  tableTitle: string;
  tableDescription?: string | null;
  rows: TableGroupRow[];
  activeRowIndex: number;
  canEdit: boolean;
  syncing?: boolean;
  onSelectRow: (tableKey: string, rowIndex: number) => void;
  onSyncColumns: (tableKey: string, sourceRowIndex: number) => void;
  renderFieldCard: (field: FormFieldItem, globalIndex: number) => React.ReactNode;
}

export function ReviewStudioTableGroupCard({
  tableKey,
  tableTitle,
  tableDescription,
  rows,
  activeRowIndex,
  canEdit,
  syncing = false,
  onSelectRow,
  onSyncColumns,
  renderFieldCard,
}: ReviewStudioTableGroupCardProps) {
  const [collapsed, setCollapsed] = useState(false);

  const activeRow =
    rows.find((r) => r.rowIndex === activeRowIndex) || rows[0] || null;
  const maxCols = rows.reduce(
    (max, r) => Math.max(max, r.fields.length),
    0
  );

  return (
    <div
      data-testid={`review-table-group-${tableKey}`}
      className="rounded-2xl border border-[var(--border-subtle)] bg-[var(--bg-elevated)] shadow-card overflow-hidden"
    >
      {/* Table Header */}
      <div className="px-4 py-3 border-b border-[var(--border-subtle)] bg-[var(--bg-muted)] flex flex-wrap items-center justify-between gap-2.5">
        <button
          type="button"
          onClick={() => setCollapsed((prev) => !prev)}
          className="flex items-center gap-2.5 min-w-0 text-start cursor-pointer group"
        >
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-emerald-500/10 border border-emerald-500/30 text-emerald-600 dark:text-emerald-400 shrink-0">
            <Table2 className="w-4 h-4" />
          </div>
          <div className="min-w-0">
            <div className="flex items-center gap-2 flex-wrap">
              <span className="text-sm font-bold text-[var(--text-primary)] truncate">
                {tableTitle}
              </span>
              <span className="inline-flex items-center rounded-full border border-[var(--border-subtle)] bg-[var(--bg-elevated)] px-2 py-0.5 text-[11px] font-semibold text-[var(--text-secondary)]">
                {rows.length} {rows.length === 1 ? "row" : "rows"} · {maxCols}{" "}
                {maxCols === 1 ? "column" : "columns"}
              </span>
            </div>
            {tableDescription && (
              <p className="text-[11px] text-[var(--text-secondary)] truncate max-w-md mt-0.5">
                {tableDescription}
              </p>
            )}
          </div>
          {collapsed ? (
            <ChevronRight className="w-4 h-4 text-[var(--text-muted)] shrink-0" />
          ) : (
            <ChevronDown className="w-4 h-4 text-[var(--text-muted)] shrink-0" />
          )}
        </button>

        {canEdit && rows.length > 1 && (
          <button
            type="button"
            disabled={syncing}
            onClick={() => onSyncColumns(tableKey, rows[0]?.rowIndex ?? 1)}
            className="inline-flex items-center gap-1.5 rounded-lg border border-emerald-500/30 bg-emerald-500/10 hover:bg-emerald-500/20 px-2.5 py-1.5 text-xs font-semibold text-emerald-700 dark:text-emerald-300 transition-colors cursor-pointer disabled:opacity-50 shrink-0"
            title="Copy column types, labels, and choices from Row 1 to all rows in this table"
          >
            {syncing ? (
              <Loader2 className="w-3.5 h-3.5 animate-spin" />
            ) : (
              <CopyCheck className="w-3.5 h-3.5" />
            )}
            <span>Apply Row 1 settings to all rows</span>
          </button>
        )}
      </div>

      {!collapsed && (
        <div className="p-4 space-y-3.5">
          {/* Interactive Row Tabs */}
          <div
            className="flex flex-wrap gap-1.5"
            role="tablist"
            aria-label={`${tableTitle} rows`}
          >
            {rows.map((row) => {
              const isActive = activeRow?.rowIndex === row.rowIndex;
              return (
                <button
                  key={row.rowIndex}
                  type="button"
                  role="tab"
                  aria-selected={isActive}
                  onClick={() => onSelectRow(tableKey, row.rowIndex)}
                  className={`inline-flex items-center gap-1.5 rounded-lg border px-3 py-1.5 text-xs font-semibold transition-all cursor-pointer ${
                    isActive
                      ? "border-emerald-500 bg-emerald-500/15 text-emerald-700 dark:text-emerald-300 ring-1 ring-emerald-500/30"
                      : "border-[var(--border-subtle)] bg-[var(--bg-muted)] text-[var(--text-secondary)] hover:border-emerald-500/40 hover:text-[var(--text-primary)]"
                  }`}
                >
                  <span>
                    Row {row.rowIndex}
                    {row.rowLabel ? ` · ${row.rowLabel}` : ""}
                  </span>
                  <span className="text-[10px] opacity-75">
                    ({row.fields.length})
                  </span>
                </button>
              );
            })}
          </div>

          {/* Active Row Field Cards */}
          {activeRow && (
            <div className="space-y-3">
              {activeRow.fields.map(({ field, globalIndex }) =>
                renderFieldCard(field, globalIndex)
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
