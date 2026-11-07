import { UIThemeConfig, SectionKey } from "../types";

export const DEFAULT_THEME_CONFIG: Required<UIThemeConfig> = {
  primary_color: "#4f46e5",
  accent_color: "#6366f1",
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
  { name: "Stuttgart Gold & Black", primary: "#FEDB00", accent: "#000000" },
  { name: "Federal German Navy", primary: "#1E3A8A", accent: "#3B82F6" },
  { name: "Bavarian Blue", primary: "#0066B2", accent: "#38BDF8" },
  { name: "Berlin Red", primary: "#E2001A", accent: "#991B1B" },
  { name: "Hamburg Brick Red", primary: "#BA1C19", accent: "#1E293B" },
  { name: "Hessen Deep Blue", primary: "#0F2D59", accent: "#DC2626" },
  { name: "Sovereign Emerald", primary: "#059669", accent: "#10B981" },
  { name: "Municipal Indigo", primary: "#4F46E5", accent: "#818CF8" },
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

