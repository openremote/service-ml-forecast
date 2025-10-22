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

interface BreadcrumbPart {
    path: string;
    label: string;
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
            display: inline-flex;
            align-items: center;
            gap: 4px;
            --or-icon-width: 16px;
            --or-icon-height: 16px;
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
    protected readonly MAX_TEXT_LENGTH = 20;

    willUpdate(changedProperties: Map<string, any>) {
        if (changedProperties.has('realm') && this.realm) {
            // Trigger location change event
            const location: Partial<RouterLocation> = {
                pathname: `${this.rootPath}/${this.realm}/configs`,
                params: {
                    realm: this.realm
                }
            };

            // Update the breadcrumbs and title
            this.updateBreadcrumbs(location as RouterLocation);
        }
    }

    /**
     * Handles location changes in the router
     */
    protected readonly handleLocationChange = (event: CustomEvent<{ location: RouterLocation }>) => {
        const location = event.detail.location;
        // Update the breadcrumbs and title
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
     * Builds breadcrumb trail from URL segments
     */
    protected updateBreadcrumbs(location: RouterLocation): void {
        const parts: BreadcrumbPart[] = [];
        const segments = location.pathname.split('/').filter(Boolean);
        
        // Remove base path segments if present
        const rootSegments = this.rootPath.split('/').filter(Boolean);
        const pathSegments = segments.slice(rootSegments.length);

        // Add base breadcrumbs (non-embedded only)
        if (!IS_EMBEDDED) {
            const realmPath = `${this.rootPath}/${this.realm}`;
            parts.push(
                { path: `${realmPath}/configs`, label: 'ML Forecast Service', icon: 'puzzle' },
                { path: `${realmPath}/configs`, label: this.capitalizeRealm() }
            );
        }

        // Build breadcrumbs from path segments
        let accumulatedPath = this.rootPath;
        for (const segment of pathSegments) {
            accumulatedPath += `/${segment}`;

            if (segment === this.realm) continue; // Skip realm in path (already in base)
            
            const label = this.getLabelForSegment(segment, location.params);
            if (label) {
                parts.push({ path: accumulatedPath, label });
            }
        }

        this.parts = parts;
    }

    /**
     * Gets human-readable label for a path segment
     */
    protected getLabelForSegment(segment: string, params: RouterLocation['params']): string | null {
        const segmentMap: Record<string, string> = {
            'configs': 'Configs',
            'new': 'New Config'
        };

        // Check if segment is a known label
        if (segmentMap[segment]) {
            return segmentMap[segment];
        }

        // Check if segment matches a route parameter
        if (params.id && segment === params.id) {
            return segment;
        }

        return null;
    }

    /**
     * Capitalizes the realm name
     */
    protected capitalizeRealm(): string {
        return this.realm.charAt(0).toUpperCase() + this.realm.slice(1);
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
    protected renderBreadcrumbItem(part: BreadcrumbPart, readonly: boolean, showSeparator: boolean) {
        const truncatedLabel = this.truncateText(part.label);
        const iconTemplate = part.icon ? html`<or-icon icon="${part.icon}"></or-icon>` : html``;

        return html`
            ${showSeparator ? html`<span aria-hidden="true">&gt;</span>` : html``}
            ${readonly
                ? html`<span aria-current="page"> ${iconTemplate} ${truncatedLabel} </span>`
                : html`
                      <a href="${part.path}" @click=${(e: MouseEvent) => this.handleNavigation(e, part.path)}>
                          ${iconTemplate}
                          <span class="truncate">${truncatedLabel}</span>
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
        // No need to render a singular breadcrumb item
        if (this.parts.length <= 1) {
            return html``;
        }

        return html`
            <nav aria-label="breadcrumb">
                ${this.parts.map((part, index) => this.renderBreadcrumbItem(part, index === this.parts.length - 1, index > 0))}
            </nav>
        `;
    }
}
