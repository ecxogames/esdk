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
        html: "<p>This modal is shared by desktop and web builds.</p>",
        confirmText: "Continue",
        cancelText: "Cancel",
    });
    appBridge.emit("modal:closed", accepted);
});
