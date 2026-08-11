const releasesApi = "https://api.github.com/repos/ecxogames/edk/releases?per_page=100";

const routes = {
	home: { path: "/" },
	esdk: { path: "/esdk" },
	ewdk: { path: "/ewdk" }
};

function supportsCleanUrls() {
	return window.location.protocol === "http:" || window.location.protocol === "https:";
}

function initializeRouting(pageKey) {
	const currentRoute = routes[pageKey];
	if (!currentRoute || !supportsCleanUrls()) {
		return;
	}

	if (window.location.pathname !== currentRoute.path) {
		window.history.replaceState({ page: pageKey }, "", `${currentRoute.path}${window.location.search}${window.location.hash}`);
	}

	document.addEventListener("click", event => {
		const link = event.target.closest("a[data-nav], a[data-route]");
		const routeKey = link?.dataset.route || link?.dataset.nav;
		const destination = routes[routeKey];

		if (!destination || event.defaultPrevented || event.button !== 0 || event.ctrlKey || event.metaKey || event.shiftKey || event.altKey) {
			return;
		}

		event.preventDefault();
		window.location.assign(destination.path);
	});
}

export function setActiveNav(pageKey) {
	const activeClasses = ["text-blue-400", "font-semibold"];
	document.querySelectorAll("[data-nav]").forEach(link => {
		if (link.dataset.nav === pageKey) {
			link.classList.add(...activeClasses);
		} else {
			link.classList.remove(...activeClasses);
		}
	});

	initializeRouting(pageKey);
}

function findTaggedRelease(releases, prefix) {
	const pattern = new RegExp(`^${prefix}\\.`, "i");
	return releases.find(release => pattern.test(release.tag_name || ""));
}

function getBestAssetDownloadUrl(release) {
	if (!release) {
		return null;
	}

	const zipAsset = release.assets?.find(asset => /\.zip$/i.test(asset.name) && asset.browser_download_url);
	if (zipAsset) {
		return zipAsset.browser_download_url;
	}

	return release.assets?.[0]?.browser_download_url || release.zipball_url || null;
}

export async function bindLatestTaggedReleaseDownload({
	tagPrefix,
	buttonId,
	linkId,
	fallbackUrl = "https://github.com/ecxogames/edk/releases"
}) {
	const button = document.getElementById(buttonId);
	const link = document.getElementById(linkId);

	if (!button || !link) {
		return;
	}

	button.href = fallbackUrl;
	link.href = fallbackUrl;

	try {
		const response = await fetch(releasesApi, {
			headers: { Accept: "application/vnd.github+json" }
		});

		if (!response.ok) {
			throw new Error(`GitHub API returned ${response.status}`);
		}

		const releases = await response.json();
		const taggedRelease = findTaggedRelease(releases, tagPrefix);

		if (!taggedRelease) {
			throw new Error(`No releases found for tag prefix ${tagPrefix}.`);
		}

		const downloadUrl = getBestAssetDownloadUrl(taggedRelease);
		if (!downloadUrl) {
			throw new Error("No downloadable URL found in matching release.");
		}

		button.href = downloadUrl;
		link.href = downloadUrl;
		link.textContent = `Directly download ${taggedRelease.tag_name}`;
	} catch {
		link.textContent = `View ${tagPrefix.toUpperCase()} releases`;
	}
}
