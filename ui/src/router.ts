import { html, LitElement, TemplateResult } from "lit";
import { state, customElement } from "lit/decorators.js";
import { PageConfigDetails } from "./pages/pages-config-details";
import { PageConfigList } from "./pages/pages-config-list";
import { unsafeHTML } from 'lit/directives/unsafe-html.js';

type ComponentConstructor = new () => LitElement;

interface RouteConfig {
    path: string;
    redirect?: string;
    component: ComponentConstructor;
}

// Routes
const routes: RouteConfig[] = [
    {
        path: "/",
        redirect: "/configs",
        component: PageConfigList
    },
    {
        path: "/configs",
        component: PageConfigList
    },
    {
        path: "/configs/:id",
        component: PageConfigDetails
    },
];

// --- Helper Functions ---

function createRouteRegex(routePath: string): { regex: RegExp; paramNames: string[] } {
    const paramNames: string[] = [];

    const regexPattern = routePath
        .replace(/:[^/]+/g, (match) => {
            const paramName = match.substring(1);
            paramNames.push(paramName);
            return '([^\\/]+)';
        });

    const regex = new RegExp(`^${regexPattern}$`);

    return { regex, paramNames };
}

function findMatchingRoute(path: string, definedRoutes: RouteConfig[]): { route: RouteConfig; params: Record<string, string> | null } | null {
    for (const route of definedRoutes) {
        const { regex, paramNames } = createRouteRegex(route.path);
        const match = path.match(regex);

        if (match) {
             if (paramNames.length === 0 || match.length > 1) {
                const params: Record<string, string> = {};
                paramNames.forEach((name, i) => {
                    params[name] = match[i + 1];
                });

                return { route, params: paramNames.length > 0 ? params : null };
             }
        }
    }
    return null;
}


function createComponentInstance(route: RouteConfig, params: Record<string, string> | null): LitElement {
    const element = new route.component();
    if (params) {
        Object.entries(params).forEach(([key, value]) => {
            try {
                 (element as any)[key] = value;
             } catch (e) {
                 console.warn(`Failed to set property '${key}' on component ${route.component.name}`, e);
             }
        });
    }
    return element;
}

function getBreadcrumb(): string {
    const pathParts = window.location.pathname.split('/').filter(part => part.length > 0); // Filter empty parts
    let currentPath = '';
    const breadcrumbParts = pathParts.map((part, index) => {
        currentPath += `/${part}`;
        const displayPart = part.charAt(0).toUpperCase() + part.slice(1);
        if (index === pathParts.length - 1) {
            return `<span>${displayPart}</span>`;
        } else {
            return `<a href="${currentPath}">${displayPart}</a>`;
        }
    });
    return breadcrumbParts.join(' &gt; ');
}


// --- Router Component ---

@customElement('app-router')
export class Router extends LitElement {

    @state()
    public activeComponent: TemplateResult | null;

    constructor() {
        super();
        this.activeComponent = null;
    }

    connectedCallback() {
        super.connectedCallback();
        window.addEventListener('popstate', this.handleRouteChange);
        this.handleRouteChange(); // Initial route handling
    }

    disconnectedCallback() {
        window.removeEventListener('popstate', this.handleRouteChange);
        super.disconnectedCallback();
    }

    handleRouteChange = () => {
        const path = window.location.pathname;
        const match = findMatchingRoute(path, routes);

        if (match) {
            const { route, params } = match;

            // Redirect if the route has a redirect property set
            if (route.redirect) {
                Router.navigate(route.redirect);
                return;
            }

            const element = createComponentInstance(route, params);
            this.activeComponent = html`${element}`;
        } else {
            // Fallback to a 404 page if no route is found
            this.activeComponent = html`<div>Page Not Found</div>`;
        }
    }

    static navigate(path: string) {
        window.history.pushState({}, "", path);
        window.dispatchEvent(new PopStateEvent('popstate'));
    }

    protected render() {
        const breadcrumbHTML = getBreadcrumb(); 

        return html`
            <div class="breadcrumb">
                 <a href="/">ML Forecast Service</a> ${breadcrumbHTML ? html`&gt; ${unsafeHTML(breadcrumbHTML)}` : ''}
            </div>
            ${this.activeComponent}
        `;
    }
}