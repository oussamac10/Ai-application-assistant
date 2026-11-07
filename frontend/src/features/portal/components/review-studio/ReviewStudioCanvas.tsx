"use client";

import React from "react";
import {
  ChevronLeft,
  ChevronRight,
  ExternalLink,
  Target,
  Trash2,
  ZoomIn,
  ZoomOut,
} from "lucide-react";
import { getFormPagePreviewUrl } from "../../services/portalClient";
import type { FormFieldItem } from "../../types";

export type InteractionType = "draw" | "move" | "resize";
export type ResizeHandle = "nw" | "ne" | "se" | "sw" | "e" | "s";

export interface CanvasInteraction {
  type: InteractionType;
  fieldId?: string;
  handle?: ResizeHandle;
  initialBbox?: [number, number, number, number];
  startClientX: number;
  startClientY: number;
  currentClientX: number;
  currentClientY: number;
}

export interface ReviewStudioCanvasProps {
  paneView: "split" | "canvas" | "fields";
  templateId: string;
  activePage: number;
  setActivePage: (p: number) => void;
  pageCount: number;
  zoomScale: number;
  setZoomScale: React.Dispatch<React.SetStateAction<number>>;
  pdfUrl: string;
  pdfContainerRef: React.RefObject<HTMLDivElement>;
  pdfImgRef: React.RefObject<HTMLImageElement>;
  canEdit: boolean;
  pickingFieldForLocation: "new" | string | null;
  onCancelPickingLocation: () => void;
  fields: FormFieldItem[];
  highlightedFieldId: string | null;
  onSelectField: (id: string) => void;
  onDeleteField: (id: string) => void;
  pageDimensions?: Array<{ page: number; width: number; height: number }>;
  interaction: CanvasInteraction | null;
  onStartDraw: (e: React.MouseEvent<HTMLDivElement>) => void;
  onStartMove: (
    e: React.MouseEvent,
    fieldId: string,
    initialBbox: [number, number, number, number]
  ) => void;
  onStartResize: (
    e: React.MouseEvent,
    fieldId: string,
    handle: ResizeHandle,
    initialBbox: [number, number, number, number]
  ) => void;
}

export function ReviewStudioCanvas({
  paneView,
  templateId,
  activePage,
  setActivePage,
  pageCount,
  zoomScale,
  setZoomScale,
  pdfUrl,
  pdfContainerRef,
  pdfImgRef,
  canEdit,
  pickingFieldForLocation,
  onCancelPickingLocation,
  fields,
  highlightedFieldId,
  onSelectField,
  onDeleteField,
  pageDimensions,
  interaction,
  onStartDraw,
  onStartMove,
  onStartResize,
}: ReviewStudioCanvasProps) {
  return (
    <div
      className={`${
        paneView === "fields"
          ? "hidden"
          : paneView === "canvas"
          ? "w-full"
          : "w-1/2"
      } border-r border-slate-200 bg-slate-950 flex flex-col min-w-0 transition-all duration-200 relative overflow-hidden`}
    >
      {/* Canvas Top Bar */}
      <div className="bg-slate-900 border-b border-slate-800 px-4 py-2 flex items-center justify-between shrink-0 text-white text-xs select-none gap-2">
        {/* Left: Page Navigator */}
        <div className="flex items-center gap-1.5 shrink-0">
          <button
            type="button"
            disabled={activePage <= 1}
            onClick={() => setActivePage(Math.max(1, activePage - 1))}
            className="p-1 rounded hover:bg-slate-700 disabled:opacity-30 text-slate-300 hover:text-white cursor-pointer"
            title="Previous Page"
          >
            <ChevronLeft className="w-4 h-4" />
          </button>
          <span className="font-semibold text-xs tracking-wide">
            Page {activePage} of {pageCount}
          </span>
          <button
            type="button"
            disabled={activePage >= pageCount}
            onClick={() => setActivePage(Math.min(pageCount, activePage + 1))}
            className="p-1 rounded hover:bg-slate-700 disabled:opacity-30 text-slate-300 hover:text-white cursor-pointer"
            title="Next Page"
          >
            <ChevronRight className="w-4 h-4" />
          </button>
        </div>

        {/* Middle: Canvas interaction hint */}
        {paneView === "canvas" && (
          <div className="hidden sm:flex items-center gap-2 text-xs text-slate-300 font-medium truncate">
            <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse shrink-0" />
            <span className="truncate">
              Drag empty space to create • Drag boxes to move or resize
            </span>
          </div>
        )}
        {paneView === "split" && (
          <div className="hidden 2xl:flex items-center gap-1.5 text-[11px] text-slate-400 truncate">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 shrink-0" />
            <span className="truncate">Drag to place or move</span>
          </div>
        )}

        {/* Right: Zoom & Open PDF */}
        <div className="flex items-center gap-1.5 shrink-0">
          <button
            type="button"
            onClick={() =>
              setZoomScale((z) =>
                Math.max(0.7, Math.round((z - 0.15) * 100) / 100)
              )
            }
            className="p-1 rounded hover:bg-slate-700 text-slate-400 hover:text-white cursor-pointer"
            title="Zoom Out"
          >
            <ZoomOut className="w-3.5 h-3.5" />
          </button>
          <span className="font-mono text-[11px] text-slate-400 w-10 text-center">
            {Math.round(zoomScale * 100)}%
          </span>
          <button
            type="button"
            onClick={() =>
              setZoomScale((z) =>
                Math.min(1.8, Math.round((z + 0.15) * 100) / 100)
              )
            }
            className="p-1 rounded hover:bg-slate-700 text-slate-400 hover:text-white cursor-pointer"
            title="Zoom In"
          >
            <ZoomIn className="w-3.5 h-3.5" />
          </button>
          <a
            href={pdfUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="p-1 rounded hover:bg-slate-700 text-slate-400 hover:text-white ml-1 cursor-pointer"
            title="Open PDF in New Window"
          >
            <ExternalLink className="w-3.5 h-3.5" />
          </a>
        </div>
      </div>

      {/* Explicit Pick Location Guidance Banner */}
      {pickingFieldForLocation && (
        <div className="px-4 py-2 bg-[#6551f3] text-white text-xs font-semibold flex items-center justify-between shrink-0 shadow-md">
          <span className="flex items-center gap-2">
            <Target className="w-4 h-4 animate-spin text-white" />
            {pickingFieldForLocation === "new"
              ? "Click or drag directly on the PDF to choose the place for the new field."
              : `Click or drag directly on the PDF to set the position for "${
                  fields.find((f) => f.id === pickingFieldForLocation)
                    ?.translations?.[0]?.label || "field"
                }"`}
          </span>
          <button
            type="button"
            onClick={onCancelPickingLocation}
            className="text-xs bg-indigo-700 hover:bg-indigo-800 text-white px-2.5 py-1 rounded underline font-medium cursor-pointer"
          >
            Cancel
          </button>
        </div>
      )}

      {/* Canvas Viewport */}
      <div
        ref={pdfContainerRef}
        className="flex-1 overflow-auto p-4 flex items-start justify-center bg-slate-900 select-none"
      >
        <div
          className="relative bg-white rounded shadow-2xl transition-transform origin-top cursor-crosshair select-none"
          style={{
            transform: `scale(${zoomScale})`,
            width: "100%",
            maxWidth: "600px",
          }}
          onMouseDown={onStartDraw}
        >
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            ref={pdfImgRef}
            src={getFormPagePreviewUrl(templateId, activePage)}
            alt={`Official PDF Page ${activePage}`}
            className="w-full h-auto block select-none pointer-events-none"
            draggable={false}
          />

          {/* Render field bounding boxes for active page */}
          {fields
            .map((field, idx) => ({ field, idx }))
            .filter(({ field }) => {
              const fPage =
                typeof field.configuration?.page === "number"
                  ? field.configuration.page
                  : 1;
              return (
                fPage === activePage && Array.isArray(field.configuration?.bbox)
              );
            })
            .map(({ field, idx }) => {
              const bbox = field.configuration.bbox as [
                number,
                number,
                number,
                number,
              ];
              const curPageDims = pageDimensions?.find(
                (p) => p.page === activePage
              ) || {
                width: 595,
                height: 842,
              };
              const topPct = (bbox[1] / curPageDims.height) * 100;
              const leftPct = (bbox[0] / curPageDims.width) * 100;
              const widthPct = ((bbox[2] - bbox[0]) / curPageDims.width) * 100;
              const heightPct =
                ((bbox[3] - bbox[1]) / curPageDims.height) * 100;
              const isHighlighted = highlightedFieldId === field.id;
              const isCurrentlyMoving =
                interaction?.type === "move" &&
                interaction?.fieldId === field.id;
              const primaryLabel = field.translations?.[0]?.label || field.key;
              const isSmallBox =
                field.fieldType === "boolean" ||
                widthPct < 8 ||
                heightPct < 3.5;

              return (
                <div
                  key={field.id}
                  onMouseDown={(e) => {
                    if (!canEdit) return;
                    e.stopPropagation();
                    onSelectField(field.id);
                    document
                      .getElementById(`field-card-${field.id}`)
                      ?.scrollIntoView({
                        behavior: "smooth",
                        block: "center",
                      });

                    onStartMove(e, field.id, [...bbox]);
                  }}
                  style={{
                    top: `${topPct}%`,
                    left: `${leftPct}%`,
                    width: `${widthPct}%`,
                    height: `${heightPct}%`,
                  }}
                  className={`absolute transition-colors select-none group ${
                    isSmallBox
                      ? "rounded-xs border-[1.5px]"
                      : "rounded border-2 p-0.5 overflow-hidden flex items-start"
                  } ${
                    isCurrentlyMoving
                      ? "border-[#6551f3] bg-[#6551f3]/35 shadow-lg z-30 cursor-grabbing"
                      : isHighlighted
                      ? "border-[#6551f3] bg-[#6551f3]/25 shadow-[0_0_0_3px_rgba(101,81,243,0.35)] z-20 cursor-grab"
                      : isSmallBox
                      ? "border-indigo-500/80 bg-indigo-500/10 hover:border-indigo-600 hover:bg-indigo-500/25 z-10 cursor-grab"
                      : "border-indigo-500/80 bg-indigo-500/15 hover:border-indigo-600 hover:bg-indigo-500/25 z-10 cursor-grab"
                  }`}
                  title={`[${idx + 1}] ${primaryLabel} (Drag to move, use handles to resize)`}
                >
                  {isSmallBox ? (
                    <>
                      <span
                        className={`absolute -top-3.5 -start-1 text-[8px] font-mono font-bold px-1 py-0.2 rounded-xs shadow-2xs pointer-events-none select-none transition-all z-20 ${
                          isHighlighted
                            ? "bg-[#6551f3] text-white ring-1 ring-white/50"
                            : "bg-slate-900/85 text-white group-hover:bg-indigo-600"
                        }`}
                      >
                        {idx + 1}
                      </span>

                      <div
                        className={`absolute -top-7 start-0 whitespace-nowrap rounded px-1.5 py-0.5 text-[10px] font-medium shadow-md pointer-events-none select-none z-40 transition-all ${
                          isHighlighted
                            ? "flex items-center gap-1 bg-[#6551f3] text-white"
                            : "hidden group-hover:flex items-center gap-1 bg-slate-900/90 text-white"
                        }`}
                      >
                        <span className="font-mono font-bold">[{idx + 1}]</span>
                        <span className="max-w-[180px] truncate">
                          {primaryLabel}
                        </span>
                      </div>
                    </>
                  ) : (
                    <span
                      className={`text-[9px] font-mono font-bold px-1 rounded shadow-xs truncate max-w-full leading-tight select-none pointer-events-none ${
                        isHighlighted
                          ? "bg-[#6551f3] text-white"
                          : "bg-indigo-900/80 text-white group-hover:bg-indigo-600"
                      }`}
                    >
                      [{idx + 1}] {primaryLabel}
                    </span>
                  )}

                  {/* Delete button on highlighted box */}
                  {isHighlighted && canEdit && (
                    <button
                      type="button"
                      onMouseDown={(e) => e.stopPropagation()}
                      onClick={(e) => {
                        e.stopPropagation();
                        onDeleteField(field.id);
                      }}
                      className={`absolute ${
                        isSmallBox
                          ? "-top-2.5 -right-2.5 w-4 h-4"
                          : "-top-3 -right-3 w-5 h-5"
                      } rounded-full bg-red-600 hover:bg-red-700 text-white flex items-center justify-center shadow-lg z-50 cursor-pointer transition-transform hover:scale-125`}
                      title="Delete Field (or press Delete/Backspace)"
                    >
                      <Trash2
                        className={isSmallBox ? "w-2.5 h-2.5" : "w-3 h-3"}
                      />
                    </button>
                  )}

                  {/* Resize handles */}
                  {isHighlighted && canEdit && (
                    <>
                      <div
                        onMouseDown={(e) => {
                          e.stopPropagation();
                          onStartResize(e, field.id, "se", [...bbox]);
                        }}
                        className={`absolute -bottom-1 -right-1 ${
                          isSmallBox ? "w-2 h-2" : "w-3 h-3"
                        } bg-white border-2 border-[#6551f3] rounded-xs cursor-se-resize shadow-md z-30 hover:scale-125 transition-transform`}
                        title="Drag to resize width and height"
                      />
                      {!isSmallBox && (
                        <>
                          <div
                            onMouseDown={(e) => {
                              e.stopPropagation();
                              onStartResize(e, field.id, "e", [...bbox]);
                            }}
                            className="absolute top-1/2 -right-1.5 -translate-y-1/2 w-2 h-4 bg-white border-2 border-[#6551f3] rounded-xs cursor-ew-resize shadow-md z-30 hover:scale-125 transition-transform"
                            title="Drag to adjust width"
                          />
                          <div
                            onMouseDown={(e) => {
                              e.stopPropagation();
                              onStartResize(e, field.id, "s", [...bbox]);
                            }}
                            className="absolute -bottom-1.5 left-1/2 -translate-x-1/2 w-4 h-2 bg-white border-2 border-[#6551f3] rounded-xs cursor-ns-resize shadow-md z-30 hover:scale-125 transition-transform"
                            title="Drag to adjust height"
                          />
                          <div
                            onMouseDown={(e) => {
                              e.stopPropagation();
                              onStartResize(e, field.id, "nw", [...bbox]);
                            }}
                            className="absolute -top-1.5 -left-1.5 w-3 h-3 bg-white border-2 border-[#6551f3] rounded-xs cursor-nw-resize shadow-md z-30 hover:scale-125 transition-transform"
                            title="Drag to resize"
                          />
                          <div
                            onMouseDown={(e) => {
                              e.stopPropagation();
                              onStartResize(e, field.id, "ne", [...bbox]);
                            }}
                            className="absolute -top-1.5 -right-1.5 w-3 h-3 bg-white border-2 border-[#6551f3] rounded-xs cursor-ne-resize shadow-md z-30 hover:scale-125 transition-transform"
                            title="Drag to resize"
                          />
                          <div
                            onMouseDown={(e) => {
                              e.stopPropagation();
                              onStartResize(e, field.id, "sw", [...bbox]);
                            }}
                            className="absolute -bottom-1.5 -left-1.5 w-3 h-3 bg-white border-2 border-[#6551f3] rounded-xs cursor-sw-resize shadow-md z-30 hover:scale-125 transition-transform"
                            title="Drag to resize"
                          />
                        </>
                      )}
                    </>
                  )}
                </div>
              );
            })}

          {/* Active Drawing Dragging Box Indicator */}
          {interaction?.type === "draw" &&
            pdfImgRef.current &&
            (() => {
              const rect = pdfImgRef.current.getBoundingClientRect();
              const leftPx =
                Math.min(
                  interaction.startClientX,
                  interaction.currentClientX
                ) - rect.left;
              const topPx =
                Math.min(
                  interaction.startClientY,
                  interaction.currentClientY
                ) - rect.top;
              const widthPx = Math.abs(
                interaction.currentClientX - interaction.startClientX
              );
              const heightPx = Math.abs(
                interaction.currentClientY - interaction.startClientY
              );

              return (
                <div
                  style={{
                    top: `${topPx}px`,
                    left: `${leftPx}px`,
                    width: `${widthPx}px`,
                    height: `${heightPx}px`,
                  }}
                  className="absolute border-2 border-dashed border-[#6551f3] bg-[#6551f3]/25 pointer-events-none z-30 flex items-center justify-center"
                >
                  <span className="bg-[#6551f3] text-white text-[9px] font-mono font-bold px-1.5 py-0.5 rounded shadow">
                    New Input Box
                  </span>
                </div>
              );
            })()}
        </div>
      </div>
    </div>
  );
}
