import { css, html, LitElement } from 'lit'
import { customElement, state } from 'lit/decorators.js'
import { Router, RouterLocation } from '@vaadin/router'
import { getRealm } from '../util'

interface BreadcrumbPart {
    path: string
    name: string
}

@customElement('breadcrumb-nav')
export class BreadcrumbNav extends LitElement {
    static get styles() {
        return css`
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
    }

    @state()
    private parts: BreadcrumbPart[] = []

    @state()
    private readonly realm: string = getRealm()

    private readonly HOME_LINK = {
        path: `/service/${this.realm}/configs`,
        name: 'ML Forecast Service'
    }

    private readonly handleLocationChange = (event: CustomEvent<{ location: RouterLocation }>) => {
        this.updateBreadcrumbs(event.detail.location)
    }

    // Add the event listener when the component is connected
    connectedCallback() {
        super.connectedCallback()
        window.addEventListener('vaadin-router-location-changed', this.handleLocationChange)
    }

    // Remove the event listener when the component is disconnected
    disconnectedCallback() {
        window.removeEventListener('vaadin-router-location-changed', this.handleLocationChange)
        super.disconnectedCallback()
    }

    private updateBreadcrumbs(location: RouterLocation) {
        const pathParts = location.pathname.split('/').filter(Boolean)

        // slice the first two parts as they are the realm and the service
        this.parts = pathParts.slice(2).reduce<BreadcrumbPart[]>((parts, part) => {
            const path = `/service/${this.realm}/${parts.length ? parts[parts.length - 1].path.slice(1) + '/' : ''}${part}`
            const name = this.formatPartName(part)
            return [...parts, { path, name }]
        }, [])
    }

    private formatPartName(part: string): string {
        return part.charAt(0).toUpperCase() + part.slice(1)
    }

    private truncateText(text: string, maxLength: number = 20): string {
        return text.length > maxLength ? text.substring(0, maxLength) + '...' : text
    }

    private renderBreadcrumbItem(part: BreadcrumbPart, isLast: boolean) {
        const truncatedName = this.truncateText(part.name)
        return html`
            <span aria-hidden="true"> &gt; </span>
            ${isLast
                ? html`<span aria-current="page">${truncatedName}</span>`
                : html`<a href="${part.path}" @click=${(e: MouseEvent) => this.handleNavigation(e, part.path)}
                      ><span class="truncate">${truncatedName}</span></a
                  >`}
        `
    }

    private handleNavigation(event: MouseEvent, path: string) {
        event.preventDefault()
        Router.go(path)
    }

    render() {
        const truncatedHomeName = this.truncateText(this.HOME_LINK.name)
        return html`
            <nav aria-label="breadcrumb">
                <a href="${this.HOME_LINK.path}" @click=${(e: MouseEvent) => this.handleNavigation(e, this.HOME_LINK.path)}>
                    <or-icon icon="puzzle"></or-icon> <span class="truncate">${truncatedHomeName}</span>
                </a>
                ${this.parts.map((part, index) => this.renderBreadcrumbItem(part, index === this.parts.length - 1))}
            </nav>
        `
    }
}
