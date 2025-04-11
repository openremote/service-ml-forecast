import {
    IconSet,
    createSvgIconSet,
    IconSets,
    OrIconSet,
} from "@openremote/or-icon";
import { html } from "lit";
import * as Core from "@openremote/core";
import { ApiService } from "./services/api-service";

/**
 * Get the realm from the path
 * @param path - The path to get the realm from
 * @returns The realm
 */
export function getRealm(): string {
    return window.location.pathname.split("/")[1]; // Realm is always the first part of the path
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





// THEME UTILITIES
export interface ThemeSettings {
    color1: string;
    color2: string;
    color3: string;
    color4: string;
    color5: string;
    color6: string;
}


export async function setRealmTheme() {
    const apiService = new ApiService();

    // Default theme settings
    const theme: ThemeSettings = {
        color1: Core.DefaultColor1,
        color2: Core.DefaultColor2,
        color3: Core.DefaultColor3,
        color4: Core.DefaultColor4,
        color5: Core.DefaultColor5,
        color6: Core.DefaultColor6,
    };

    try {
        const config = await apiService.getRealmConfig(getRealm());
        if (config && config.styles) {
            const cssString = config.styles;
            const colorRegex = /--or-app-color(\d+):\s*(#[0-9a-fA-F]{6})/g;
            let match;
    
            while ((match = colorRegex.exec(cssString)) !== null) {
                const colorIndex = parseInt(match[1], 10);
                const colorValue = match[2];
                
                switch (colorIndex) {
                    case 1: theme.color1 = colorValue; break;
                    case 2: theme.color2 = colorValue; break;
                    case 3: theme.color3 = colorValue; break;
                    case 4: theme.color4 = colorValue; break;
                    case 5: theme.color5 = colorValue; break;
                    case 6: theme.color6 = colorValue; break;
                }
            }
        }
    } catch (error) {
        console.error("Error getting realm config", error);
    }

    setTheme(theme);
}

/**
 * Set the theme
 * @param theme - The theme to set
 */
export function setTheme(theme: ThemeSettings) {
    document.body.style.setProperty('--or-app-color1', theme.color1 || Core.DefaultColor1);
    document.body.style.setProperty('--or-app-color2', theme.color2 || Core.DefaultColor2);
    document.body.style.setProperty('--or-app-color3', theme.color3 || Core.DefaultColor3);
    document.body.style.setProperty('--or-app-color4', theme.color4 || Core.DefaultColor4);
    document.body.style.setProperty('--or-app-color5', theme.color5 || Core.DefaultColor5);
    document.body.style.setProperty('--or-app-color6', theme.color6 || Core.DefaultColor6);
}



