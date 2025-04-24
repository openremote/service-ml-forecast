import { IconSet, createSvgIconSet, IconSets, OrIconSet } from '@openremote/or-icon'
import { html } from 'lit'
import * as Core from '@openremote/core'
import { APIService } from './services/api-service'

/**
 * Get the root path of the application
 * @returns The full root path of the application
 * @remarks This is a workaround to have consistent full root path, rather than relative via the ENV variable.
 * @remarks Neglible performance impact, sub millisecond lookup
 */
export function getRootPath() {
    const scriptElement = document.querySelector('script[src*="bundle"]')

    if (scriptElement && scriptElement.getAttribute('src')) {
        const scriptPath = new URL(scriptElement.getAttribute('src')!, window.location.href).pathname

        // Positive lookahead to match everything up to bundle.js
        const match = scriptPath.match(/(.*?)(?=bundle)/)
        // Remove trailing slash if present
        return match ? (match[1].endsWith('/') ? match[1].slice(0, -1) : match[1]) : ''
    }

    return ''
}

/**
 * Check if the environment is development
 * @returns True if the environment is development, false otherwise
 */
export function isDevelopment(): boolean {
    return process.env.NODE_ENV === 'development'
}

/**
 * Setup the OR icons
 * Overrides the default createMdiIconSet with a function that uses the static fonts part of the build
 */
export function setupORIcons() {
    function createMdiIconSet(): IconSet {
        return {
            getIconTemplate(icon: string) {
                return html`<span style="font-family: 'Material Design Icons';" class="mdi-${icon}"></span>`
            },
            onAdd(): void {
                const style = document.createElement('style')
                const rootPath = getRootPath()

                style.id = 'mdiFontStyle'
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
                `
                document.head.appendChild(style)
            }
        }
    }

    IconSets.addIconSet('mdi', createMdiIconSet())
    IconSets.addIconSet('or', createSvgIconSet(OrIconSet.size, OrIconSet.icons))
}

// THEME UTILITIES
export interface ThemeSettings {
    color1: string
    color2: string
    color3: string
    color4: string
    color5: string
    color6: string
}

/**
 * Set the realm theme based on realm config from the service backend
 */
export async function setRealmTheme(realm: string) {
    // Default theme settings
    const theme: ThemeSettings = {
        color1: Core.DefaultColor1,
        color2: Core.DefaultColor2,
        color3: Core.DefaultColor3,
        color4: Core.DefaultColor4,
        color5: Core.DefaultColor5,
        color6: Core.DefaultColor6
    }

    // If no realm is provided, use the default theme
    if (!realm || realm === 'undefined') {
        setTheme(theme)
        return
    }

    try {
        const config = await APIService.getOpenRemoteRealmConfig(realm)
        if (config && config.styles) {
            const cssString = config.styles
            const colorRegex = /--or-app-color(\d+):\s*(#[0-9a-fA-F]{6})/g
            let match: RegExpExecArray | null

            while ((match = colorRegex.exec(cssString)) !== null) {
                const colorIndex = parseInt(match[1], 10)
                const colorValue = match[2]

                switch (colorIndex) {
                    case 1:
                        theme.color1 = colorValue
                        break
                    case 2:
                        theme.color2 = colorValue
                        break
                    case 3:
                        theme.color3 = colorValue
                        break
                    case 4:
                        theme.color4 = colorValue
                        break
                    case 5:
                        theme.color5 = colorValue
                        break
                    case 6:
                        theme.color6 = colorValue
                        break
                }
            }
        }
    } catch {
        console.warn('Was unable to retrieve realm specific theme settings, falling back to default')
    }

    // Set the theme with any settings that were retrieved
    setTheme(theme)
}

/**
 * Helper function to update the color variables in the document body
 * @param theme - The theme to set
 */
export function setTheme(theme: ThemeSettings) {
    document.body.style.setProperty('--or-app-color1', theme.color1 || Core.DefaultColor1)
    document.body.style.setProperty('--or-app-color2', theme.color2 || Core.DefaultColor2)
    document.body.style.setProperty('--or-app-color3', theme.color3 || Core.DefaultColor3)
    document.body.style.setProperty('--or-app-color4', theme.color4 || Core.DefaultColor4)
    document.body.style.setProperty('--or-app-color5', theme.color5 || Core.DefaultColor5)
    document.body.style.setProperty('--or-app-color6', theme.color6 || Core.DefaultColor6)
}
