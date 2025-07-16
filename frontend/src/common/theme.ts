// Copyright 2025, OpenRemote Inc.
//
// This program is free software: you can redistribute it and/or modify
// it under the terms of the GNU Affero General Public License as
// published by the Free Software Foundation, either version 3 of the
// License, or (at your option) any later version.
//
// This program is distributed in the hope that it will be useful,
// but WITHOUT ANY WARRANTY; without even the implied warranty of
// MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
// GNU Affero General Public License for more details.
//
// You should have received a copy of the GNU Affero General Public License
// along with this program. If not, see <https://www.gnu.org/licenses/>.
//
// SPDX-License-Identifier: AGPL-3.0-or-later

import { IconSet, IconSets, OrIconSet, createSvgIconSet } from '@openremote/or-icon';
import { html } from 'lit';
import * as Core from '@openremote/core';
import { getRootPath } from './util';
import { manager } from '@openremote/core';

/**
 * Base theme settings
 */
const BASE_THEME = {
    color1: Core.DefaultColor1,
    color2: Core.DefaultColor2,
    color3: Core.DefaultColor3,
    color4: Core.DefaultColor4,
    color5: Core.DefaultColor5,
    color6: Core.DefaultColor6
};

/**
 * Setup the OR icons
 * Overrides the default createMdiIconSet with a function that uses the static fonts part of the build
 * Setup the MDI-Icons for or-icon element
 */
export function setupORIcons() {
    function createMdiIconSet(): IconSet {
        return {
            getIconTemplate(icon: string) {
                return html`<span style="font-family: 'Material Design Icons';" class="mdi-${icon}"></span>`;
            },
            onAdd(): void {
                const style = document.createElement('style');
                const rootPath = getRootPath();

                style.id = 'mdiFontStyle';
                style.textContent = `
                    @font-face {
                        font-family: "Material Design Icons";
                        src: url("${rootPath}/assets/fonts/materialdesignicons-webfont.eot") format("embedded-opentype"),
                             url("${rootPath}/assets/fonts/materialdesignicons-webfont.woff2") format("woff2"),
                             url("${rootPath}/assets/fonts/materialdesignicons-webfont.woff") format("woff"),
                             url("${rootPath}/assets/fonts/materialdesignicons-webfont.ttf") format("truetype");
                        font-weight: normal;
                        font-style: normal;
                    }
                `;
                document.head.appendChild(style);
            }
        };
    }

    IconSets.addIconSet('mdi', createMdiIconSet());
    IconSets.addIconSet('or', createSvgIconSet(OrIconSet.size, OrIconSet.icons));
}

/**
 * Theme settings
 */
interface ThemeSettings {
    color1: string;
    color2: string;
    color3: string;
    color4: string;
    color5: string;
    color6: string;
}

/**
 * Set the realm theme based on realm config from the service backend
 * @param realm - The realm to set the theme for
 */
export async function setRealmTheme(realm: string) {
    const theme = BASE_THEME;

    if (!realm || realm === 'undefined') {
        setTheme(theme);
        return;
    }

    try {
        const config = (await manager.rest.api.ConfigurationResource.getManagerConfig()).data;
        const styles = config.realms?.[realm]?.styles;

        if (styles) {
            const cssString = styles;
            const colorRegex = /--or-app-color(\d+):\s*(#[0-9a-fA-F]{6})/g;
            let match: RegExpExecArray | null;

            while ((match = colorRegex.exec(cssString)) !== null) {
                const colorIndex = parseInt(match[1], 10);
                const colorValue = match[2];

                // Set the color value based on the index
                switch (colorIndex) {
                    case 1:
                        theme.color1 = colorValue;
                        break;
                    case 2:
                        theme.color2 = colorValue;
                        break;
                    case 3:
                        theme.color3 = colorValue;
                        break;
                    case 4:
                        theme.color4 = colorValue;
                        break;
                    case 5:
                        theme.color5 = colorValue;
                        break;
                    case 6:
                        theme.color6 = colorValue;
                        break;
                }
            }
        }
    } catch {
        console.warn('Was unable to retrieve realm specific theme settings, falling back to default');
    }

    setTheme(theme);
}

/**
 * Helper function to update the color variables in the document body
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
