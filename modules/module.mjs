/** Formats a label for display in the example application. */
export function formatTitle(value) {
    return value.trim().replace(/[-_]+/g, " ").replace(/\b\w/g, (letter) => letter.toUpperCase());
}
