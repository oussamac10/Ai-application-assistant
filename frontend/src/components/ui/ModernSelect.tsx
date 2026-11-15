"use client";

import React, { useState, useRef, useEffect, useMemo } from "react";
import { ChevronDown, Check, Search, X } from "lucide-react";

export interface ModernSelectOption<T extends string = string> {
  value: T;
  label: string;
  sublabel?: string;
  icon?: React.ReactNode;
  badge?: React.ReactNode;
  disabled?: boolean;
}

export interface ModernSelectProps<T extends string = string> {
  id?: string;
  value: T;
  onChange: (value: T) => void;
  options: ModernSelectOption<T>[];
  placeholder?: string;
  disabled?: boolean;
  className?: string;
  searchable?: boolean;
  searchPlaceholder?: string;
  "aria-label"?: string;
  size?: "sm" | "md";
}

export function ModernSelect<T extends string = string>({
  id,
  value,
  onChange,
  options,
  placeholder = "Select an option...",
  disabled = false,
  className = "",
  searchable = false,
  searchPlaceholder = "Search options...",
  "aria-label": ariaLabel,
  size = "md",
}: ModernSelectProps<T>) {
  const [isOpen, setIsOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const containerRef = useRef<HTMLDivElement>(null);
  const searchInputRef = useRef<HTMLInputElement>(null);

  // Close when clicking outside
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (
        containerRef.current &&
        !containerRef.current.contains(event.target as Node)
      ) {
        setIsOpen(false);
      }
    }
    if (isOpen) {
      document.addEventListener("mousedown", handleClickOutside);
    }
    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
    };
  }, [isOpen]);

  // Focus search input on open
  useEffect(() => {
    if (isOpen && (searchable || options.length > 8)) {
      setTimeout(() => {
        searchInputRef.current?.focus();
      }, 50);
    } else {
      setSearchQuery("");
    }
  }, [isOpen, searchable, options.length]);

  // Keyboard navigation: Escape closes
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Escape") {
      setIsOpen(false);
    }
  };

  const selectedOption = useMemo(
    () => options.find((opt) => opt.value === value),
    [options, value]
  );

  const shouldShowSearch = searchable || options.length > 8;

  const filteredOptions = useMemo(() => {
    if (!searchQuery.trim()) return options;
    const q = searchQuery.toLowerCase();
    return options.filter(
      (opt) =>
        opt.label.toLowerCase().includes(q) ||
        (opt.sublabel && opt.sublabel.toLowerCase().includes(q)) ||
        opt.value.toLowerCase().includes(q)
    );
  }, [options, searchQuery]);

  return (
    <div
      ref={containerRef}
      onKeyDown={handleKeyDown}
      className={`relative w-full text-start ${className}`}
    >
      {/* Hidden native select for form serialization, accessibility, and automation */}
      <select
        id={id}
        name={id}
        value={value}
        onChange={(e) => onChange(e.target.value as T)}
        aria-label={!id ? (ariaLabel || placeholder) : undefined}
        tabIndex={-1}
        className="sr-only pointer-events-none"
        aria-hidden="true"
      >
        {options.map((opt) => (
          <option key={opt.value} value={opt.value}>
            {opt.label}
          </option>
        ))}
      </select>

      {/* Modern Trigger Button */}
      <button
        id={id ? `${id}-trigger` : undefined}
        type="button"
        disabled={disabled}
        onClick={() => !disabled && setIsOpen((prev) => !prev)}
        aria-haspopup="listbox"
        aria-expanded={isOpen}
        aria-label={!id ? (ariaLabel || placeholder) : undefined}
        className={`w-full flex items-center justify-between border font-medium transition-all duration-150 outline-none select-none cursor-pointer ${
          size === "sm" ? "px-2.5 py-1.5 rounded-lg text-xs" : "px-3.5 py-2.5 rounded-xl text-xs"
        } ${
          disabled
            ? "bg-[#0A0E17]/60 border-white/[0.06] text-slate-500 cursor-not-allowed"
            : isOpen
            ? "bg-[#0F1522] border-emerald-500 ring-2 ring-emerald-500/20 shadow-xs text-white"
            : "bg-[#0A0E17] border-white/10 text-slate-100 hover:border-emerald-500/40 hover:bg-[#0F1522] shadow-2xs"
        }`}
      >
        <div className="flex items-center gap-2.5 min-w-0 flex-1">
          {selectedOption?.icon && (
            <span className="shrink-0 text-slate-400">{selectedOption.icon}</span>
          )}
          <div className="min-w-0 flex-1 truncate">
            {selectedOption ? (
              <span className="font-semibold text-white truncate">
                {selectedOption.label}
              </span>
            ) : (
              <span className="text-slate-500">{placeholder}</span>
            )}
            {selectedOption?.sublabel && (
              <span className="text-slate-400 font-normal ms-1.5 text-[11px] truncate">
                {selectedOption.sublabel}
              </span>
            )}
          </div>
          {selectedOption?.badge && (
            <span className="shrink-0">{selectedOption.badge}</span>
          )}
        </div>

        <ChevronDown
          className={`w-4 h-4 text-slate-400 shrink-0 ms-2 transition-transform duration-200 ${
            isOpen ? "rotate-180 text-emerald-400" : ""
          }`}
        />
      </button>

      {/* Dropdown Popover */}
      {isOpen && (
        <div
          role="listbox"
          tabIndex={-1}
          className="absolute z-50 inset-x-0 mt-1.5 bg-[#0F1522] rounded-2xl border border-white/15 shadow-2xl overflow-hidden animate-in fade-in zoom-in-95 duration-100"
        >
          {/* Search box if enabled or many items */}
          {shouldShowSearch && (
            <div className="p-2 border-b border-white/10 bg-[#0A0E17]">
              <div className="relative">
                <Search className="w-3.5 h-3.5 text-slate-400 absolute start-2.5 top-1/2 -translate-y-1/2 pointer-events-none" />
                <input
                  ref={searchInputRef}
                  type="text"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  placeholder={searchPlaceholder}
                  className="w-full ps-8 pe-7 py-1.5 rounded-lg border border-white/10 text-xs bg-[#0F1522] text-slate-100 placeholder-slate-500 focus:outline-none focus:border-emerald-500 focus:ring-1 focus:ring-emerald-500/30"
                />
                {searchQuery && (
                  <button
                    type="button"
                    onClick={() => setSearchQuery("")}
                    className="absolute end-2 top-1/2 -translate-y-1/2 text-slate-400 hover:text-white p-0.5"
                  >
                    <X className="w-3 h-3" />
                  </button>
                )}
              </div>
            </div>
          )}

          {/* Options List */}
          <div className="max-h-60 overflow-y-auto p-1.5 space-y-0.5">
            {filteredOptions.length === 0 ? (
              <div className="p-3 text-center text-xs text-slate-400">
                No matching options found
              </div>
            ) : (
              filteredOptions.map((opt) => {
                const isSelected = opt.value === value;
                return (
                  <button
                    key={opt.value}
                    type="button"
                    role="option"
                    aria-selected={isSelected}
                    disabled={opt.disabled}
                    onClick={() => {
                      if (!opt.disabled) {
                        onChange(opt.value);
                        setIsOpen(false);
                      }
                    }}
                    className={`w-full flex items-center justify-between px-3 py-2 rounded-xl text-xs transition-colors cursor-pointer text-left ${
                      opt.disabled
                        ? "opacity-40 cursor-not-allowed"
                        : isSelected
                        ? "bg-emerald-500/15 text-emerald-300 font-semibold border border-emerald-500/30"
                        : "text-slate-300 hover:bg-[#151D2E] hover:text-white border border-transparent"
                    }`}
                  >
                    <div className="flex items-center gap-2.5 min-w-0 flex-1">
                      {opt.icon && (
                        <span className={`shrink-0 ${isSelected ? "text-emerald-400" : "text-slate-400"}`}>
                          {opt.icon}
                        </span>
                      )}
                      <div className="min-w-0 flex-1">
                        <div className="flex items-center gap-1.5">
                          <span className="truncate">{opt.label}</span>
                          {opt.badge && <span className="shrink-0">{opt.badge}</span>}
                        </div>
                        {opt.sublabel && (
                          <p className="text-[10px] text-slate-400 font-normal truncate mt-0.5">
                            {opt.sublabel}
                          </p>
                        )}
                      </div>
                    </div>

                    {isSelected && (
                      <Check className="w-4 h-4 text-emerald-400 shrink-0 ms-2" />
                    )}
                  </button>
                );
              })
            )}
          </div>
        </div>
      )}
    </div>
  );
}
