export interface ModalOptions {
    title?: string;
    html: string;
    confirmText?: string;
    cancelText?: string;
    showCancel?: boolean;
    closeOnBackdrop?: boolean;
}

const STYLE_ID = "ewdk-modal-styles";

function installStyles(): void {
    if (document.getElementById(STYLE_ID)) return;
    const style = document.createElement("style");
    style.id = STYLE_ID;
    style.textContent = `
        .ewdk-modal-backdrop{position:fixed;inset:0;z-index:1000;display:grid;place-items:center;padding:1.25rem;background:#0f172acc;backdrop-filter:blur(6px)}
        .ewdk-modal{width:min(32rem,100%);overflow:hidden;border:1px solid #ffffff1f;border-radius:1rem;background:#111827;color:#f8fafc;box-shadow:0 24px 80px #0008;animation:ewdk-modal-in .18s ease-out}
        .ewdk-modal__header{display:flex;align-items:center;justify-content:space-between;padding:1.1rem 1.25rem;border-bottom:1px solid #ffffff17}
        .ewdk-modal__title{margin:0;font-size:1.1rem}.ewdk-modal__close{border:0;background:transparent;color:#94a3b8;font-size:1.6rem;cursor:pointer}
        .ewdk-modal__content{padding:1.25rem;line-height:1.6}.ewdk-modal__actions{display:flex;justify-content:flex-end;gap:.75rem;padding:1rem 1.25rem;background:#0b1220}
        .ewdk-modal__button{border:1px solid #ffffff24;border-radius:.6rem;padding:.65rem 1rem;background:#1e293b;color:#f8fafc;cursor:pointer}.ewdk-modal__button--confirm{border-color:#6366f1;background:#6366f1}
        @keyframes ewdk-modal-in{from{opacity:0;transform:translateY(10px) scale(.98)}}
    `;
    document.head.append(style);
}

/** Displays a modal containing caller-provided HTML and resolves with the user's choice. */
export function showModal(options: ModalOptions): Promise<boolean> {
    installStyles();
    return new Promise((resolve) => {
        const backdrop = document.createElement("div");
        backdrop.className = "ewdk-modal-backdrop";
        backdrop.innerHTML = `
            <section class="ewdk-modal" role="dialog" aria-modal="true" aria-labelledby="ewdk-modal-title">
                <header class="ewdk-modal__header">
                    <h2 class="ewdk-modal__title" id="ewdk-modal-title"></h2>
                    <button class="ewdk-modal__close" type="button" aria-label="Close">&times;</button>
                </header>
                <div class="ewdk-modal__content"></div>
                <footer class="ewdk-modal__actions">
                    <button class="ewdk-modal__button ewdk-modal__cancel" type="button"></button>
                    <button class="ewdk-modal__button ewdk-modal__button--confirm ewdk-modal__confirm" type="button"></button>
                </footer>
            </section>`;

        const title = backdrop.querySelector<HTMLElement>(".ewdk-modal__title")!;
        const content = backdrop.querySelector<HTMLElement>(".ewdk-modal__content")!;
        const cancel = backdrop.querySelector<HTMLButtonElement>(".ewdk-modal__cancel")!;
        const confirm = backdrop.querySelector<HTMLButtonElement>(".ewdk-modal__confirm")!;
        title.textContent = options.title ?? "Notice";
        content.innerHTML = options.html;
        cancel.textContent = options.cancelText ?? "Cancel";
        confirm.textContent = options.confirmText ?? "Continue";
        cancel.hidden = options.showCancel === false;

        const finish = (accepted: boolean): void => {
            document.removeEventListener("keydown", onKeyDown);
            backdrop.remove();
            resolve(accepted);
        };
        const onKeyDown = (event: KeyboardEvent): void => {
            if (event.key === "Escape") finish(false);
        };
        backdrop.querySelector(".ewdk-modal__close")!.addEventListener("click", () => finish(false));
        cancel.addEventListener("click", () => finish(false));
        confirm.addEventListener("click", () => finish(true));
        backdrop.addEventListener("click", (event) => {
            if (event.target === backdrop && options.closeOnBackdrop !== false) finish(false);
        });
        document.addEventListener("keydown", onKeyDown);
        document.body.append(backdrop);
        confirm.focus();
    });
}

/**
 * Namespace-style API for pages that prefer `Modal.showModal(...)`.
 * Accepts either the full options object or a title and HTML string.
 */
function showModalFromNamespace(title: string, html: string): Promise<boolean>;
function showModalFromNamespace(options: ModalOptions): Promise<boolean>;
function showModalFromNamespace(titleOrOptions: string | ModalOptions, html = ""): Promise<boolean> {
    const options = typeof titleOrOptions === "string"
        ? { title: titleOrOptions, html }
        : titleOrOptions;
    return showModal(options);
}

export const Modal = Object.freeze({ showModal: showModalFromNamespace });
