import { UIThemeConfig } from "../types";

export const BRAND_THEME_STORAGE_KEY = "formflow-brand-theme";

export interface RgbColor {
  r: number;
  g: number;
  b: number;
}

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

/** Normalizes `#RGB` or `#RRGGBB` input into uppercase `#RRGGBB`, falling back safely. */
export function normalizeHexColor(
  raw?: string | null,
  fallback = DEFAULT_THEME_CONFIG.primary_color,
): string {
  const cleanFallback = /^#[0-9A-Fa-f]{6}$/.test(fallback) ? fallback.toUpperCase() : "#10B981";
  if (!raw || typeof raw !== "string") return cleanFallback;
  const trimmed = raw.trim().replace(/^#/, "");
  if (/^[0-9A-Fa-f]{3}$/.test(trimmed)) {
    const expanded = trimmed
      .split("")
      .map((c) => c + c)
      .join("");
    return `#${expanded.toUpperCase()}`;
  }
  if (/^[0-9A-Fa-f]{6}$/.test(trimmed)) {
    return `#${trimmed.toUpperCase()}`;
  }
  return cleanFallback;
}

export function hexToRgb(hexColor: string): RgbColor {
  const normalized = normalizeHexColor(hexColor).slice(1);
  return {
    r: parseInt(normalized.slice(0, 2), 16),
    g: parseInt(normalized.slice(2, 4), 16),
    b: parseInt(normalized.slice(4, 6), 16),
  };
}

export function rgbToHex({ r, g, b }: RgbColor): string {
  const clamp = (n: number) => Math.max(0, Math.min(255, Math.round(n)));
  return (
    "#" +
    [clamp(r), clamp(g), clamp(b)]
      .map((v) => v.toString(16).padStart(2, "0"))
      .join("")
      .toUpperCase()
  );
}

export function rgbToCssChannels({ r, g, b }: RgbColor): string {
  const clamp = (n: number) => Math.max(0, Math.min(255, Math.round(n)));
  return `${clamp(r)} ${clamp(g)} ${clamp(b)}`;
}

export function mixRgb(a: RgbColor, b: RgbColor, weightA: number): RgbColor {
  const wA = Math.max(0, Math.min(1, weightA));
  const wB = 1 - wA;
  return {
    r: Math.round(a.r * wA + b.r * wB),
    g: Math.round(a.g * wA + b.g * wB),
    b: Math.round(a.b * wA + b.b * wB),
  };
}

export function rgbToHsl({ r, g, b }: RgbColor): { h: number; s: number; l: number } {
  const rn = r / 255;
  const gn = g / 255;
  const bn = b / 255;
  const max = Math.max(rn, gn, bn);
  const min = Math.min(rn, gn, bn);
  const l = (max + min) / 2;

  if (max === min) {
    return { h: 0, s: 0, l };
  }

  const d = max - min;
  const s = l > 0.5 ? d / (2 - max - min) : d / (max + min);
  let h = 0;
  if (max === rn) {
    h = (gn - bn) / d + (gn < bn ? 6 : 0);
  } else if (max === gn) {
    h = (bn - rn) / d + 2;
  } else {
    h = (rn - gn) / d + 4;
  }
  return { h: h * 60, s, l };
}

export function hslToRgb(h: number, s: number, l: number): RgbColor {
  const hue = ((h % 360) + 360) % 360;
  const sat = Math.max(0, Math.min(1, s));
  const light = Math.max(0, Math.min(1, l));

  if (sat === 0) {
    const val = Math.round(light * 255);
    return { r: val, g: val, b: val };
  }

  const q = light < 0.5 ? light * (1 + sat) : light + sat - light * sat;
  const p = 2 * light - q;
  const hue2rgb = (tInput: number) => {
    let t = tInput;
    if (t < 0) t += 1;
    if (t > 1) t -= 1;
    if (t < 1 / 6) return p + (q - p) * 6 * t;
    if (t < 1 / 2) return q;
    if (t < 2 / 3) return p + (q - p) * (2 / 3 - t) * 6;
    return p;
  };

  const hNorm = hue / 360;
  return {
    r: Math.round(hue2rgb(hNorm + 1 / 3) * 255),
    g: Math.round(hue2rgb(hNorm) * 255),
    b: Math.round(hue2rgb(hNorm - 1 / 3) * 255),
  };
}

/** Computes standard WCAG 2.x relative luminance in [0, 1]. */
export function getRelativeLuminance({ r, g, b }: RgbColor): number {
  const toLinear = (c: number) => {
    const s = c / 255;
    return s <= 0.03928 ? s / 12.92 : Math.pow((s + 0.055) / 1.055, 2.4);
  };
  return 0.2126 * toLinear(r) + 0.7152 * toLinear(g) + 0.0722 * toLinear(b);
}

/** Computes standard WCAG 2.x contrast ratio in [1, 21]. */
export function getContrastRatio(rgbA: RgbColor, rgbB: RgbColor): number {
  const lumA = getRelativeLuminance(rgbA);
  const lumB = getRelativeLuminance(rgbB);
  const lighter = Math.max(lumA, lumB);
  const darker = Math.min(lumA, lumB);
  return (lighter + 0.05) / (darker + 0.05);
}

export function getContrastTextColor(hexColor: string): string {
  const rgb = hexToRgb(normalizeHexColor(hexColor));
  return getRelativeLuminance(rgb) > 0.3 ? "#0f172a" : "#ffffff";
}

/** Shifts lightness via binary search until `rgb` satisfies `minRatio` against `backgroundRgb`. */
export function adjustColorForContrast(
  rgb: RgbColor,
  backgroundRgb: RgbColor,
  minRatio: number,
  direction: "lighter" | "darker",
): RgbColor {
  if (getContrastRatio(rgb, backgroundRgb) >= minRatio) {
    return rgb;
  }

  const { h, s, l } = rgbToHsl(rgb);
  let targetH = h;
  let targetS = s;
  if (direction === "darker" && h >= 44 && h <= 64) {
    targetH = Math.max(42, h - 6);
    targetS = Math.max(s, 0.85);
  }

  let best: RgbColor = hslToRgb(
    targetH,
    targetS,
    direction === "lighter" ? 0.95 : 0.08,
  );

  if (direction === "lighter") {
    let low = Math.min(l, 0.95);
    let high = 0.95;
    for (let i = 0; i < 20; i += 1) {
      const mid = (low + high) / 2;
      const candidate = hslToRgb(targetH, targetS, mid);
      if (getContrastRatio(candidate, backgroundRgb) >= minRatio) {
        best = candidate;
        high = mid;
      } else {
        low = mid;
      }
    }
  } else {
    let low = 0.08;
    let high = Math.max(l, 0.08);
    for (let i = 0; i < 20; i += 1) {
      const mid = (low + high) / 2;
      const candidate = hslToRgb(targetH, targetS, mid);
      if (getContrastRatio(candidate, backgroundRgb) >= minRatio) {
        best = candidate;
        low = mid;
      } else {
        high = mid;
      }
    }
  }

  return best;
}

const CANONICAL_EMERALD_VARS: Record<string, string> = {
  "--brand-50-rgb": "236 253 245",
  "--brand-100-rgb": "209 250 229",
  "--brand-200-rgb": "167 243 208",
  "--brand-300-rgb": "110 231 183",
  "--brand-400-rgb": "52 211 153",
  "--brand-500-rgb": "16 185 129",
  "--brand-600-rgb": "5 150 105",
  "--brand-700-rgb": "4 120 87",
  "--brand-800-rgb": "6 95 70",
  "--brand-900-rgb": "6 78 59",
  "--brand-950-rgb": "2 44 34",
  "--brand-border-light-rgb": "5 150 105",
  "--brand-on-solid": "#0f172a",
};

/** Generates a full WCAG 2.2 AA brand scale of CSS variables from an organization theme config. */
export function generateBrandCssVariables(
  config?: UIThemeConfig | null,
): Record<string, string> {
  if (!config?.primary_color) {
    return { ...CANONICAL_EMERALD_VARS };
  }
  const primaryHex = normalizeHexColor(config.primary_color);
  if (primaryHex === "#10B981") {
    return { ...CANONICAL_EMERALD_VARS };
  }

  const baseRgb = hexToRgb(primaryHex);
  const darkSurface: RgbColor = { r: 15, g: 21, b: 34 };
  const white: RgbColor = { r: 255, g: 255, b: 255 };
  const deepDark: RgbColor = { r: 2, g: 6, b: 23 };

  const shade400 = adjustColorForContrast(
    mixRgb(baseRgb, white, 0.82),
    darkSurface,
    5.0,
    "lighter",
  );
  const shade300 = adjustColorForContrast(
    mixRgb(shade400, white, 0.78),
    darkSurface,
    6.5,
    "lighter",
  );
  const borderLight = adjustColorForContrast(baseRgb, white, 3.0, "darker");
  const shade600 = adjustColorForContrast(
    mixRgb(baseRgb, deepDark, 0.88),
    white,
    3.5,
    "darker",
  );
  const shade700 = adjustColorForContrast(
    mixRgb(baseRgb, deepDark, 0.8),
    white,
    4.7,
    "darker",
  );
  const shade800 = adjustColorForContrast(
    mixRgb(shade700, deepDark, 0.85),
    white,
    5.8,
    "darker",
  );
  const shade900 = mixRgb(shade800, deepDark, 0.8);
  const shade950 = mixRgb(baseRgb, deepDark, 0.18);
  const shade50 = mixRgb(baseRgb, white, 0.08);
  const shade100 = mixRgb(baseRgb, white, 0.16);
  const shade200 = mixRgb(baseRgb, white, 0.28);

  return {
    "--brand-50-rgb": rgbToCssChannels(shade50),
    "--brand-100-rgb": rgbToCssChannels(shade100),
    "--brand-200-rgb": rgbToCssChannels(shade200),
    "--brand-300-rgb": rgbToCssChannels(shade300),
    "--brand-400-rgb": rgbToCssChannels(shade400),
    "--brand-500-rgb": rgbToCssChannels(baseRgb),
    "--brand-600-rgb": rgbToCssChannels(shade600),
    "--brand-700-rgb": rgbToCssChannels(shade700),
    "--brand-800-rgb": rgbToCssChannels(shade800),
    "--brand-900-rgb": rgbToCssChannels(shade900),
    "--brand-950-rgb": rgbToCssChannels(shade950),
    "--brand-border-light-rgb": rgbToCssChannels(borderLight),
    "--brand-on-solid": getContrastTextColor(primaryHex),
  };
}

/** Applies the brand CSS variables to `:root` (`document.documentElement`) and optionally persists. */
export function applyBrandThemeToDocument(
  config?: UIThemeConfig | null,
  options?: { persist?: boolean },
): void {
  const vars = generateBrandCssVariables(config);
  const primaryHex = config?.primary_color
    ? normalizeHexColor(config.primary_color)
    : "#10B981";
  const isCustom = Boolean(config?.primary_color) && primaryHex !== "#10B981";

  if (typeof document !== "undefined") {
    const root = document.documentElement;
    Object.entries(vars).forEach(([key, value]) => {
      root.style.setProperty(key, value);
    });
    root.dataset.brandCustom = isCustom ? "true" : "false";
  }

  if (options?.persist && typeof window !== "undefined") {
    try {
      if (isCustom && config) {
        window.localStorage.setItem(
          BRAND_THEME_STORAGE_KEY,
          JSON.stringify({
            primary_color: primaryHex,
            accent_color: config.accent_color
              ? normalizeHexColor(config.accent_color, primaryHex)
              : undefined,
            sidebar_theme: config.sidebar_theme,
            vars,
          }),
        );
      } else {
        window.localStorage.removeItem(BRAND_THEME_STORAGE_KEY);
      }
    } catch {
      // Ignore storage quota or privacy-mode errors
    }
  }
}

/** Hydrates brand CSS variables from localStorage without mutating stored preference. */
export function hydratePersistedBrandTheme(): void {
  if (typeof window === "undefined") {
    applyBrandThemeToDocument(null, { persist: false });
    return;
  }
  try {
    const raw = window.localStorage.getItem(BRAND_THEME_STORAGE_KEY);
    if (raw) {
      const parsed = JSON.parse(raw) as UIThemeConfig;
      if (parsed && typeof parsed.primary_color === "string") {
        applyBrandThemeToDocument(parsed, { persist: false });
        return;
      }
    }
  } catch {
    // Ignore malformed JSON or storage errors
  }
  applyBrandThemeToDocument(null, { persist: false });
}

/** Clears persisted brand theme and resets `:root` CSS variables to Aikido Emerald. */
export function clearPersistedBrandTheme(): void {
  if (typeof window !== "undefined") {
    try {
      window.localStorage.removeItem(BRAND_THEME_STORAGE_KEY);
    } catch {
      // Ignore storage errors
    }
  }
  applyBrandThemeToDocument(null, { persist: false });
}

