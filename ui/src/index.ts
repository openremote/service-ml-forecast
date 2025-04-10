import { Router } from '@vaadin/router';
import "./pages/pages-config-list";
import "./pages/pages-config-viewer";
import "./components/breadcrumb";
import { html, render } from 'lit';
import { setRealmTheme, setupORIcons } from './util';

const outlet = document.querySelector('#outlet') as HTMLElement;
const router = new Router(outlet);

// Important, these setup the MDI icons for the or-icon component
setupORIcons();


// Set theme to body
await setRealmTheme();

// Define the routes
const routes = [
    {
        path: '/:realm/configs',
        component: 'page-config-list',
    },
    {
        path: '/:realm/configs/new',
        component: 'page-config-viewer',
    },
    {
        path: '/:realm/configs/:id',
        component: 'page-config-viewer',
    },
    {
        path: '/:pathMatch(.*)*',
        action: () => {
            render(html`<div>404</div>`, outlet);
        }
    },
]

// Render the breadcrumb component
render(html`<breadcrumb-nav></breadcrumb-nav>`, outlet);

// Set the routes -- Vaadin will then handle these paths
router.setRoutes(routes);
