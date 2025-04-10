import {
    IconSet,
    createSvgIconSet,
    IconSets,
    OrIconSet,
} from "@openremote/or-icon";
import { html } from "lit";
import * as Core from "@openremote/core";

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


// TODO: Get colors from OR so we can use the managers theme
export const Theme = {
    color1: Core.DefaultColor1,
    color2: Core.DefaultColor2,
    color3: Core.DefaultColor3,
    color4: Core.DefaultColor4,
    color5: Core.DefaultColor5,
    color6: Core.DefaultColor6,
    color7: Core.DefaultColor7,
    color8: Core.DefaultColor8,
    color9: Core.DefaultColor9,
    color10: Core.DefaultColor10,
    color11: Core.DefaultColor11,
}

