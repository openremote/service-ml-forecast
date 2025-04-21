import { Router } from '@vaadin/router'
import './pages/pages-config-list'
import './pages/pages-config-editor'
import './pages/pages-not-found'
import './pages/app-layout'
import { setupORIcons, getRootPath } from './util'

async function init() {
    const outlet = document.querySelector('#outlet') as HTMLElement

    // Setup OR icons
    setupORIcons()

    // Setup the router -- Vaadin expects a trailing slash in the baseUrl
    const router = new Router(outlet, { baseUrl: getRootPath() + '/' })

    initRouter(router)
}

function initRouter(router: Router) {
    // Setup the routes
    const routes = [
        {
            path: '',
            component: 'app-layout',
            children: [
                {
                    path: `/:realm`,
                    redirect: `/:realm/configs`
                },
                {
                    path: `/:realm/configs`,
                    component: 'page-config-list',
                    title: 'Configs'
                },
                {
                    path: `/:realm/configs/new`,
                    component: 'page-config-editor',
                    title: 'New Config'
                },
                {
                    path: `/:realm/configs/:id`,
                    component: 'page-config-editor',
                    title: 'Edit Config'
                },
                {
                    path: '(.*)',
                    component: 'page-not-found'
                }
            ]
        }
    ]

    // Set the routes
    router.setRoutes(routes)
}

// Entry point
await init()
