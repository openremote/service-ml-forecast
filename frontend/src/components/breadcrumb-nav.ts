import { css, html, LitElement } from 'lit'
import { customElement, property, state } from 'lit/decorators.js'
import { Router, RouterLocation } from '@vaadin/router'
import { getRootPath } from '../util'

/**
 * Represents a part of the breadcrumb navigation
 */
interface BreadcrumbPart {
    path: string
    name: string
}

/**
 * A navigation component that displays the current location in a hierarchical structure
 */
@customElement('breadcrumb-nav')
export class BreadcrumbNav extends LitElement {
    @property({ type: String })
    realm = ''

    static styles = css`
        nav {
            display: flex;
            align-items: center;
            gap: 8px;
            margin-bottom: 16px;
            width: fit-content;
        }

        a {
            color: var(--or-app-color4);
            text-decoration: none;
            display: inline-flex;
            align-items: center;
            gap: 4px;
            --or-icon-width: 16px;
            --or-icon-height: 16px;
            max-width: 200px;
        }

        a:hover {
            color: var(--or-app-color3);
        }

        span[aria-current='page'] {
            color: rgba(0, 0, 0, 0.87);
            font-weight: 500;
            max-width: 200px;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
        }

        span[aria-hidden='true'] {
            color: rgba(0, 0, 0, 0.38);
            user-select: none;
        }

        .truncate {
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
        }
    `

    @state()
    private parts: BreadcrumbPart[] = []

    private readonly rootPath = getRootPath()

    private get HOME_LINK(): BreadcrumbPart {
        return {
            path: `${this.rootPath}${this.realm}/configs`,
            name: 'ML Forecast Service'
        }
    }

    private readonly MAX_TEXT_LENGTH = 20

    updated(changedProperties: Map<string, any>) {
        if (changedProperties.has('realm') && this.realm) {
            // Trigger location change event
            const location: Partial<RouterLocation> = {
                pathname: `${this.rootPath}${this.realm}/configs`,
                params: {
                    realm: this.realm
                }
            }

            // Update the breadcrumbs and title
            this.updateBreadcrumbs(location as RouterLocation)
        }
    }

    /**
     * Handles location changes in the router
     */
    private readonly handleLocationChange = (event: CustomEvent<{ location: RouterLocation }>) => {
        const location = event.detail.location
        // Update the breadcrumbs and title
        this.updateBreadcrumbs(location)
    }

    connectedCallback(): void {
        super.connectedCallback()
        window.addEventListener('vaadin-router-location-changed', this.handleLocationChange)
    }

    disconnectedCallback(): void {
        window.removeEventListener('vaadin-router-location-changed', this.handleLocationChange)
        super.disconnectedCallback()
    }

    /**
     * Updates the breadcrumb parts based on the current location
     */
    private updateBreadcrumbs(location: RouterLocation): void {
        const parts: BreadcrumbPart[] = []
        const { pathname, params } = location

        // Add Smartcity part (realm)
        if (this.realm) {
            parts.push({
                path: `${this.rootPath}${this.realm}/configs`,
                name: this.realm.charAt(0).toUpperCase() + this.realm.slice(1)
            })
        }

        // Add Configs part
        if (pathname.includes('/configs')) {
            parts.push({
                path: `${this.rootPath}${this.realm}/configs`,
                name: 'Configs'
            })

            // Add specific config part if we're on a config page
            if (params.id) {
                parts.push({
                    path: `${this.rootPath}${this.realm}/configs/${params.id}`,
                    name: params.id === 'new' ? 'New Config' : `${params.id}`
                })
            }
        }

        this.parts = parts
    }

    /**
     * Truncates text to a specified length
     */
    private truncateText(text: string): string {
        return text.length > this.MAX_TEXT_LENGTH ? `${text.substring(0, this.MAX_TEXT_LENGTH)}...` : text
    }

    /**
     * Renders a single breadcrumb item
     */
    private renderBreadcrumbItem(part: BreadcrumbPart, isLast: boolean) {
        const truncatedName = this.truncateText(part.name)

        return html`
            <span aria-hidden="true">&gt;</span>
            ${isLast
                ? html`<span aria-current="page">${truncatedName}</span>`
                : html`
                      <a href="${part.path}" @click=${(e: MouseEvent) => this.handleNavigation(e, part.path)}>
                          <span class="truncate">${truncatedName}</span>
                      </a>
                  `}
        `
    }

    /**
     * Handles navigation clicks
     */
    private handleNavigation(event: MouseEvent, path: string): void {
        event.preventDefault()
        Router.go(path)
    }

    render() {
        const truncatedHomeName = this.truncateText(this.HOME_LINK.name)

        return html`
            <nav aria-label="breadcrumb">
                <a href="${this.HOME_LINK.path}" @click=${(e: MouseEvent) => this.handleNavigation(e, this.HOME_LINK.path)}>
                    <or-icon icon="puzzle"></or-icon>
                    <span class="truncate">${truncatedHomeName}</span>
                </a>
                ${this.parts.map((part, index) => this.renderBreadcrumbItem(part, index === this.parts.length - 1))}
            </nav>
        `
    }
}
