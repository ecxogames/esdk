export interface ModalOptions {
    title?: string;
    html: string;
    confirmText?: string;
    cancelText?: string;
    showCancel?: boolean;
}

export function showModal(options: ModalOptions): Promise<boolean> {
    return new Promise((resolve) => {
        const backdrop = document.createElement("div");
        backdrop.style.cssText = "position:fixed;inset:0;z-index:1000;display:grid;place-items:center;background:#0009";
        backdrop.innerHTML = `<section role="dialog" aria-modal="true" style="width:min(32rem,90%);padding:1.25rem;border-radius:1rem;background:#111827;color:#fff">
            <h2></h2><div class="content"></div><footer style="display:flex;justify-content:flex-end;gap:.75rem;margin-top:1rem">
            <button class="cancel" type="button"></button><button class="confirm" type="button"></button></footer></section>`;
        backdrop.querySelector("h2")!.textContent = options.title ?? "Notice";
        backdrop.querySelector<HTMLElement>(".content")!.innerHTML = options.html;
        const cancel = backdrop.querySelector<HTMLButtonElement>(".cancel")!;
        const confirm = backdrop.querySelector<HTMLButtonElement>(".confirm")!;
        cancel.textContent = options.cancelText ?? "Cancel";
        confirm.textContent = options.confirmText ?? "Continue";
        cancel.hidden = options.showCancel === false;
        const finish = (answer: boolean) => { backdrop.remove(); resolve(answer); };
        cancel.onclick = () => finish(false);
        confirm.onclick = () => finish(true);
        document.body.append(backdrop);
        confirm.focus();
    });
}

function showModalApi(title: string, html: string): Promise<boolean>;
function showModalApi(options: ModalOptions): Promise<boolean>;
function showModalApi(value: string | ModalOptions, html = "") {
    return showModal(typeof value === "string" ? { title: value, html } : value);
}

export const Modal = Object.freeze({ showModal: showModalApi });
