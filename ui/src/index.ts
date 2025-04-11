import { Router } from '@vaadin/router';
import "./pages/pages-config-list";
import "./pages/pages-config-editor";
import "./components/breadcrumb";
import "./pages/pages-not-found";

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
    // 404 page -- should be the last route
    {
        path: '(.*)',
        component: 'page-not-found',
    },
]

// Breadcrumb component (navigational component)
render(html`<breadcrumb-nav></breadcrumb-nav>`, outlet);

// Set the routes -- Vaadin will then handle these paths
router.setRoutes(routes);
