/**
 * Recognising an indexed row key, so repeated fields read as rows.
 *
 * The backend emits repeated table rows as flat indexed fields —
 * `children_1_family_name`, `children_2_gender` — because the guided flow asks
 * one question at a time and has no repeated-section UI. That is a sound
 * fallback for *storage*, but on screen it means a child's six details arrive
 * as six unrelated questions, and "männlich / weiblich" appears twice with
 * nothing saying which child each belongs to.
 *
 * This is presentation only. Keys are never rewritten: they are the contract
 * with the backend and with export, and a display concern must not touch them.
 */

/** A key parsed into its row parts, or null when it is not an indexed key. */
export interface RowKeyParts {
  /** The section, e.g. `children`. */
  section: string;
  /** 1-based row number. */
  index: number;
  /** The column within the row, e.g. `family_name`. */
  column: string;
  /** Everything up to and including the index, e.g. `children_1_`. */
  prefix: string;
}

// `<section>_<n>_<column>`. The section may itself contain underscores
// (`spouse_details_1_name`), so the *last* number-delimited group wins — a
// greedy leading match would swallow the index for a section named `row_2`.
const INDEXED_KEY = /^(.+)_(\d+)_(.+)$/;

export function parseRowKey(key: string): RowKeyParts | null {
  const match = INDEXED_KEY.exec(key);
  if (!match) return null;
  const [, section, index, column] = match;
  const rowIndex = Number(index);
  if (!Number.isInteger(rowIndex) || rowIndex < 1) return null;
  return {
    section,
    index: rowIndex,
    column,
    prefix: `${section}_${rowIndex}_`,
  };
}

export interface RowGroup<T> {
  section: string;
  index: number;
  /** Fields in the order the backend returned them, which is document order. */
  items: T[];
}

/**
 * Groups items by their row, preserving order.
 *
 * Rows come out in ascending index and fields keep their original sequence
 * within a row, so the display follows the document rather than the accident of
 * how a map iterated. Anything whose key is not indexed is returned separately
 * and untouched — most of a form is not a table.
 */
export function groupByRow<T>(
  items: T[],
  keyOf: (item: T) => string,
): { rows: RowGroup<T>[]; ungrouped: T[] } {
  const rows = new Map<string, RowGroup<T>>();
  const ungrouped: T[] = [];

  for (const item of items) {
    const parts = parseRowKey(keyOf(item));
    if (!parts) {
      ungrouped.push(item);
      continue;
    }
    const id = `${parts.section}#${parts.index}`;
    const existing = rows.get(id);
    if (existing) {
      existing.items.push(item);
    } else {
      rows.set(id, {
        section: parts.section,
        index: parts.index,
        items: [item],
      });
    }
  }

  return {
    rows: Array.from(rows.values()).sort(
      (a, b) => a.section.localeCompare(b.section) || a.index - b.index,
    ),
    ungrouped,
  };
}

/** A heading for one row: "Child 1", "Spouse 2".
 *
 * The section key comes from the document's own header (`children`), so this
 * only has to make it readable — singularising and capitalising — rather than
 * inventing a name for something it does not understand. */
export function rowHeading(section: string, index: number): string {
  const words = section.replace(/_/g, " ").trim();
  const singular = words.endsWith("ren")
    ? words.slice(0, -3) // children -> child
    : words.endsWith("ies")
      ? words.slice(0, -3) + "y"
      : words.endsWith("s")
        ? words.slice(0, -1)
        : words;
  const titled = singular.replace(/\b\w/g, (c) => c.toUpperCase());
  return `${titled} ${index}`;
}
