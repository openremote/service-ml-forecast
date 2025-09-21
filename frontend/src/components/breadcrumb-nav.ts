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

import { css, html, LitElement } from 'lit';
import { customElement, property, state } from 'lit/decorators.js';
import { Router, RouterLocation } from '@vaadin/router';
import { getRootPath } from '../common/util';
import { IS_EMBEDDED } from '../common/constants';

/**
 * Represents a part of the breadcrumb navigation
 */
interface BreadcrumbPart {
    path: string;
    name: string;
    icon?: string;
}

/**
 * A navigation component that displays the current location in a hierarchical structure
 */
@customElement('breadcrumb-nav')
export class BreadcrumbNav extends LitElement {
    @property({ type: String })
    realm = '';

    static styles = css`
        nav {
            display: flex;
            align-items: center;
            gap: 8px;
            margin-bottom: 16px;
            width: 100%;
            justify-content: space-between;
        }

        .breadcrumb-container {
            display: flex;
            align-items: center;
            gap: 8px;
        }

        .realm-badge {
            background-color: var(--or-app-color4);
            color: white;
            padding: 4px 12px;
            border-radius: 16px;
            font-size: 12px;
            font-weight: 500;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-left: auto;
            min-width: 60px;
            text-align: center;
            display: flex;
            align-items: center;
            justify-content: center;
        }

        a {
            color: var(--or-app-color4);
            text-decoration: none;
            display: inline-flex;
            align-items: center;
            gap: 4px;
            --or-icon-width: 16px;
            --or-icon-height: 16px;
            max-width: 300px;
        }

        a:hover {
            color: var(--or-app-color3);
        }

        span[aria-current='page'] {
            color: rgba(0, 0, 0, 0.87);
            font-weight: 500;
            max-width: 300px;
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
    `;

    @state()
    protected parts: BreadcrumbPart[] = [];

    protected readonly rootPath = getRootPath();

    protected readonly MAX_TEXT_LENGTH = 40;

    willUpdate(changedProperties: Map<string, any>) {
        if (changedProperties.has('realm') && this.realm) {
            const location: Partial<RouterLocation> = {
                pathname: `${this.rootPath}/${this.realm}/configs`,
                params: {
                    realm: this.realm
                }
            };

            this.updateBreadcrumbs(location as RouterLocation);
        }
    }

    /**
     * Handles location changes in the router
     */
    protected readonly handleLocationChange = (event: CustomEvent<{ location: RouterLocation }>) => {
        const location = event.detail.location;
        this.updateBreadcrumbs(location);
    };

    connectedCallback(): void {
        super.connectedCallback();
        window.addEventListener('vaadin-router-location-changed', this.handleLocationChange);
    }

    disconnectedCallback(): void {
        window.removeEventListener('vaadin-router-location-changed', this.handleLocationChange);
        super.disconnectedCallback();
    }

    /**
     * Updates the breadcrumb parts based on the current location
     */
    protected updateBreadcrumbs(location: RouterLocation): void {
        const parts: BreadcrumbPart[] = [];
        const { pathname, params } = location;

        const homePart = {
            path: `${this.rootPath}/${this.realm}/configs`,
            name: 'ML Forecast Service',
            icon: 'puzzle'
        };

        // If we are not embedded, add the home part
        if (!IS_EMBEDDED) {
            parts.push(homePart);
        }

        const configsPart = {
            path: `${this.rootPath}/${this.realm}/configs`,
            name: 'Configurations'
        };

        // Add Configs part
        if (pathname.includes('/configs')) {
            parts.push(configsPart);

            // Handle config editor page
            const isExistingConfig = params.id && !pathname.includes('/new');
            if (isExistingConfig) {
                parts.push({
                    path: `${this.rootPath}/${this.realm}/configs/${params.id}`,
                    name: `${params.id}`
                });
            }

            const isNewConfig = pathname.includes('/new');
            if (isNewConfig) {
                parts.push({
                    path: `${this.rootPath}/${this.realm}/configs/new`,
                    name: 'New'
                });
            }
        }

        this.parts = parts;
    }

    /**
     * Truncates text to a specified length
     */
    protected truncateText(text: string): string {
        return text.length > this.MAX_TEXT_LENGTH ? `${text.substring(0, this.MAX_TEXT_LENGTH)}...` : text;
    }

    /**
     * Renders a single breadcrumb item
     */
    protected renderBreadcrumbItem(part: BreadcrumbPart, readonly: boolean, isFirst: boolean) {
        const truncatedName = this.truncateText(part.name);

        const icon = part.icon ? html`<or-icon icon=${part.icon}></or-icon>` : html``;

        return html`
            ${!isFirst ? html`<span aria-hidden="true">&gt;</span>` : html``}
            ${readonly
                ? html`<span aria-current="page">${truncatedName}</span>`
                : html`
                      <a href="${part.path}" @click=${(e: MouseEvent) => this.handleNavigation(e, part.path)}>
                          ${icon}
                          <span class="truncate">${truncatedName}</span>
                      </a>
                  `}
        `;
    }

    /**
     * Handles navigation clicks
     */
    protected handleNavigation(event: MouseEvent, path: string): void {
        event.preventDefault();
        Router.go(path);
    }

    render() {
        // Hide breadcrumbs if there's only one part
        const shouldShowBreadcrumbs = this.parts.length > 1;
        if (!shouldShowBreadcrumbs) {
            return html``;
        }

        const realmBadge = IS_EMBEDDED ? html`` : html`<div class="realm-badge">${this.realm}</div>`;

        return html`
            <nav aria-label="breadcrumb">
                <div class="breadcrumb-container">
                    ${this.parts.map((part, index) => this.renderBreadcrumbItem(part, index === this.parts.length - 1, index === 0))}
                </div>
                ${realmBadge}
            </nav>
        `;
    }
}
