import { UIThemeConfig, SectionKey } from "../types";

export const DEFAULT_THEME_CONFIG: Required<UIThemeConfig> = {
  primary_color: "#10b981",
  accent_color: "#34d399",
  sidebar_theme: "dark",
  layout_density: "comfortable",
  show_metrics_strip: true,
  show_authority_metadata: true,
  show_portal_link: true,
  section_order: ["header", "metrics", "actions", "forms"],
  citizen_welcome_heading: "",
  citizen_welcome_text: "",
  citizen_notice_banner: "",
};

export const POPULAR_AUTHORITY_PALETTES = [
  { name: "Aikido Emerald", primary: "#10B981", accent: "#34D399" },
  { name: "Sovereign Emerald", primary: "#059669", accent: "#10B981" },
  { name: "Civic Navy", primary: "#1E3A8A", accent: "#3B82F6" },
  { name: "Atlantic Blue", primary: "#0066B2", accent: "#38BDF8" },
  { name: "Sovereign Gold", primary: "#FEDB00", accent: "#0F172A" },
  { name: "Crimson Seal", primary: "#E11D48", accent: "#9F1239" },
  { name: "Deep Slate", primary: "#334155", accent: "#94A3B8" },
  { name: "Royal Indigo", primary: "#4F46E5", accent: "#818CF8" },
];

export function resolveThemeConfig(config?: UIThemeConfig | null): Required<UIThemeConfig> {
  return {
    primary_color: config?.primary_color || DEFAULT_THEME_CONFIG.primary_color,
    accent_color: config?.accent_color || DEFAULT_THEME_CONFIG.accent_color,
    sidebar_theme: config?.sidebar_theme || DEFAULT_THEME_CONFIG.sidebar_theme,
    layout_density: config?.layout_density || DEFAULT_THEME_CONFIG.layout_density,
    show_metrics_strip: config?.show_metrics_strip !== false,
    show_authority_metadata: config?.show_authority_metadata !== false,
    show_portal_link: config?.show_portal_link !== false,
    section_order: (config?.section_order && config.section_order.length > 0)
      ? config.section_order
      : DEFAULT_THEME_CONFIG.section_order,
    citizen_welcome_heading: config?.citizen_welcome_heading || "",
    citizen_welcome_text: config?.citizen_welcome_text || "",
    citizen_notice_banner: config?.citizen_notice_banner || "",
  };
}

export function getContrastTextColor(hexColor: string): string {
  const hex = hexColor.replace("#", "");
  if (hex.length < 6) return "#ffffff";
  const r = parseInt(hex.substring(0, 2), 16) || 0;
  const g = parseInt(hex.substring(2, 4), 16) || 0;
  const b = parseInt(hex.substring(4, 6), 16) || 0;
  const yiq = (r * 299 + g * 587 + b * 114) / 1000;
  return yiq >= 150 ? "#0f172a" : "#ffffff";
}

