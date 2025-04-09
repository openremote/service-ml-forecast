import {
    IconSet,
    createSvgIconSet,
    IconSets,
    OrIconSet,
} from "@openremote/or-icon";
import { html } from "lit";

/**
 * Get the realm from the path
 * @param path - The path to get the realm from
 * @returns The realm
 */
export function getRealm(path: string): string {
    // TODO: We need to eventually move this to actually check the realm from the backend
    // ApiService.getRealm() should be used instead of this function
    return path.split("/")[1]; // Realm is always the first part of the path
}

/**
 * Setup the OR icons
 * Overrides the default createMdiIconSet with a function that uses the static fonts part of the build
 */
export function setupORIcons() {
    function createMdiIconSet(): IconSet {
        return {
            getIconTemplate(icon: string) {
                return html`<span style="font-family: 'Material Design Icons';" class="mdi-${icon}"></span>`;
            },
            onAdd(): void {
                const style = document.createElement("style");
                style.id = "mdiFontStyle";
                style.textContent = `
                    @font-face {
                        font-family: "Material Design Icons";
                        src: url("/static/fonts/materialdesignicons-webfont.eot") format("embedded-opentype"),
                             url("/static/fonts/materialdesignicons-webfont.woff2") format("woff2"),
                             url("/static/fonts/materialdesignicons-webfont.woff") format("woff"),
                             url("/static/fonts/materialdesignicons-webfont.ttf") format("truetype");
                        font-weight: normal;
                        font-style: normal;
                    }
                `;
                document.head.appendChild(style);
            },
        };
    }

    IconSets.addIconSet("mdi", createMdiIconSet());
    IconSets.addIconSet("or", createSvgIconSet(OrIconSet.size, OrIconSet.icons));
}
