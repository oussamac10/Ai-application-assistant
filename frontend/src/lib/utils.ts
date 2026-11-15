/**
 * Utility functions for frontend UI components and class merging.
 */

export type ClassValue =
  | ClassValue[]
  | string
  | number
  | boolean
  | null
  | undefined
  | { [key: string]: boolean | number | string | null | undefined };

/**
 * Clean, lightweight class combiner that flattens arrays, evaluates object
 * flags, and filters out falsy values (null, undefined, false, empty strings).
 *
 * @param inputs - List of class names, conditional objects, or nested arrays.
 * @returns Space-separated concatenated class string.
 */
export function cn(...inputs: ClassValue[]): string {
  const classes: string[] = [];

  function parse(val: ClassValue): void {
    if (!val) return;

    if (typeof val === "string" || typeof val === "number") {
      classes.push(String(val));
    } else if (Array.isArray(val)) {
      for (const item of val) {
        parse(item);
      }
    } else if (typeof val === "object") {
      for (const [key, condition] of Object.entries(val)) {
        if (condition) {
          classes.push(key);
        }
      }
    }
  }

  for (const input of inputs) {
    parse(input);
  }

  return classes.filter(Boolean).join(" ");
}
