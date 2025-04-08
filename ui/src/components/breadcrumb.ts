import { LitElement, html } from 'lit';
import { customElement, state } from 'lit/decorators.js';
import { Router, RouterLocation } from '@vaadin/router';

interface BreadcrumbPart {
  path: string;
  name: string;
}

@customElement('breadcrumb-nav')
export class BreadcrumbNav extends LitElement {
  @state()
  private parts: BreadcrumbPart[] = [];

  private readonly HOME_LINK = {
    path: '/',
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
    this.parts = pathParts.reduce<BreadcrumbPart[]>((parts, part) => {
      const path = `/${parts.length ? parts[parts.length - 1].path.slice(1) + '/' : ''}${part}`;
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
          ${this.HOME_LINK.name}
        </a>
        ${this.parts.map((part, index) => 
          this.renderBreadcrumbItem(part, index === this.parts.length - 1)
        )}
      </nav>
    `;
  }
}
