import { appBridge } from "../classes/bridge.js";
import { showModal } from "../functions/Modal.js";
import { formatTitle } from "../modules/module.mjs";

const openButton = document.querySelector<HTMLButtonElement>("#open-modal");
const status = document.querySelector<HTMLElement>("#modal-status");

appBridge.on<boolean>("modal:closed", (accepted) => {
    if (status) status.textContent = accepted ? "The modal was confirmed." : "The modal was dismissed.";
});

openButton?.addEventListener("click", async () => {
    const accepted = await showModal({
        title: formatTitle("custom_html_modal"),
        html: `
            <p class="mb-4 text-slate-300">This content is supplied by <code>scripts/main.ts</code>.</p>
            <label class="grid gap-2">
                Example value
                <input id="modal-example-input" value="EWDK" class="rounded-lg border border-slate-600 bg-slate-900 px-3 py-2 text-white">
            </label>`,
        confirmText: "Looks good",
        cancelText: "Not yet",
    });
    appBridge.emit("modal:closed", accepted);
});
