type Listener<T> = (detail: T) => void;

/** A small event bridge that lets otherwise independent components communicate. */
export class Bridge {
    private readonly events = new EventTarget();

    emit<T>(name: string, detail: T): void {
        this.events.dispatchEvent(new CustomEvent(name, { detail }));
    }

    on<T>(name: string, listener: Listener<T>): () => void {
        const handler = (event: Event): void => listener((event as CustomEvent<T>).detail);
        this.events.addEventListener(name, handler);
        return () => this.events.removeEventListener(name, handler);
    }
}

export const appBridge = new Bridge();
