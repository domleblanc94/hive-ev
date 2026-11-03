# Project logo in Home Assistant

The generated orange/white UNOFFICIAL HIVE EV image is bundled unchanged as custom_components/hive_ev/brand/icon.png and displayed in the project README. It is an original Codex-generated project mark, not the official Hive logo or a claim of endorsement.

Home Assistant 2026.3 and later can serve custom integration brand images directly from the integration's brand directory. A square icon is sufficient: Home Assistant falls back to it where a separate logo/dark image is absent. No manifest brand flag, external brands submission, new account or charging command is required. The source PNG is preserved at its original square resolution; Home Assistant scales it for display.

For an existing installation, copy the brand folder beside manifest.json, restart Home Assistant, and refresh the browser/app. A hard browser refresh may be needed if the previous missing icon is cached. Alternatively install the complete updated candidate with experimental controls disabled, following the existing upgrade instructions. Reuse the existing integration entry.

The icon does not automatically replace every sensor's Material Design icon; it brands the integration/device information where Home Assistant shows integration artwork. The standard framework decides its placement and fallbacks.

Official reference: https://contributors.home-assistant.io/blog/2026/02/24/brands-proxy-api/ . The image was made with the built-in image-generation tool; the original asset/prompt are preserved separately in the local design workspace.
