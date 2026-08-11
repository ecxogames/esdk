import { bindLatestTaggedReleaseDownload, setActiveNav } from "./router.js";

setActiveNav("ewdk");

bindLatestTaggedReleaseDownload({
    tagPrefix: "EWDK",
    buttonId: "ewdk-download-button",
    linkId: "ewdk-latest-release-download"
});
