/** Small shared state container for desktop and web pages. */
export class DataStore {
    constructor(initial = {}) {
        this.value = { ...initial };
    }

    get(key) { return this.value[key]; }
    set(key, value) { this.value[key] = value; return value; }
}
