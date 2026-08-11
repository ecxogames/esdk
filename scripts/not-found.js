const routeFiles = {
    "/esdk": "/esdk",
    "/ewdk": "/ewdk"
};

const destination = routeFiles[window.location.pathname.replace(/\/$/, "")];

if (destination) {
    window.location.replace(`${destination}${window.location.search}${window.location.hash}`);
}
