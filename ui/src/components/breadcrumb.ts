import { LitElement, css, html } from 'lit';
import { customElement, state } from 'lit/decorators.js';
import { Router, RouterLocation } from '@vaadin/router';
import { getRealm } from '../util';

interface BreadcrumbPart {
    path: string;
    name: string;
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
      }

      a {
        color: var(--or-app-color4);
        text-decoration: none;
        display: inline-flex;
        align-items: center;
        gap: 4px;
        --or-icon-width: 16px;
        --or-icon-height: 16px;
      }

      a:hover {
        color: var(--or-app-color3); 
      }

      span[aria-current="page"] {
        color: rgba(0, 0, 0, 0.87); 
        font-weight: 500; 
      }

      span[aria-hidden="true"] {
        color: rgba(0, 0, 0, 0.38);
        user-select: none;
      }
    `;
    }


    @state()
    private parts: BreadcrumbPart[] = [];

    @state()
    private readonly realm: string = getRealm(window.location.pathname);

    private readonly HOME_LINK = {
        path: `/${this.realm}/configs`,
        name: 'ML Forecast Service'
    };

    private readonly handleLocationChange = (event: CustomEvent<{ location: RouterLocation }>) => {
        this.updateBreadcrumbs(event.detail.location);
    };

    connectedCallback() {
        super.connectedCallback();
        window.addEventListener('vaadin-router-location-changed', this.handleLocationChange);
    }

    disconnectedCallback() {
        window.removeEventListener('vaadin-router-location-changed', this.handleLocationChange);
        super.disconnectedCallback();
    }

    private updateBreadcrumbs(location: RouterLocation) {
        const pathParts = location.pathname.split('/').filter(Boolean);

     
     
        // slice the first part as it is the realm and not part of the breadcrumb
        this.parts = pathParts.slice(1).reduce<BreadcrumbPart[]>((parts, part) => {
            const path = `/${this.realm}/${parts.length ? parts[parts.length - 1].path.slice(1) + '/' : ''}${part}`;
            const name = this.formatPartName(part);
            return [...parts, { path, name }];
        }, []);
    }

    private formatPartName(part: string): string {
        return part.charAt(0).toUpperCase() + part.slice(1);
    }

    private renderBreadcrumbItem(part: BreadcrumbPart, isLast: boolean) {
        return html`
      <span aria-hidden="true"> &gt; </span>
      ${isLast
                ? html`<span aria-current="page">${part.name}</span>`
                : html`<a href="${part.path}" @click=${(e: MouseEvent) => this.handleNavigation(e, part.path)}>${part.name}</a>`
            }
    `;
    }

    private handleNavigation(event: MouseEvent, path: string) {
        event.preventDefault();
        Router.go(path);
    }

    render() {
        return html`
      <nav aria-label="breadcrumb">
        <a href="${this.HOME_LINK.path}"
           @click=${(e: MouseEvent) => this.handleNavigation(e, this.HOME_LINK.path)}>
          <or-icon icon="puzzle"></or-icon> ${this.HOME_LINK.name}
        </a>
        ${this.parts.map((part, index) =>
            this.renderBreadcrumbItem(part, index === this.parts.length - 1)
        )}
      </nav>
    `;
    }
}
