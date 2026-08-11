import { bindLatestTaggedReleaseDownload, setActiveNav } from "../router.js";

setActiveNav("esdk");

bindLatestTaggedReleaseDownload({
    tagPrefix: "ESDK",
    buttonId: "esdk-download-button",
    linkId: "esdk-latest-release-download"
});
