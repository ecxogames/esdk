export function formatLabel(value) {
    return String(value ?? "").trim();
}

export function formatTitle(value) {
    return formatLabel(value).replace(/[_-]+/g, " ").replace(/\b\w/g, letter => letter.toUpperCase());
}
