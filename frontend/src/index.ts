import { Router } from '@vaadin/router'
import './pages/pages-config-list'
import './pages/pages-config-editor'
import './pages/pages-not-found'
import './pages/pages-service-unavailable'
import './pages/app-layout'
import { html, render } from 'lit'
import { setupORIcons, getRootPath } from './util'
import { APIService } from './services/api-service'

async function init() {
    const outlet = document.querySelector('#outlet') as HTMLElement

    const backendIsAvailable = await APIService.isServiceAvailable()
    if (!backendIsAvailable) {
        render(html`<page-service-unavailable></page-service-unavailable>`, outlet)
        return
    }

    // Setup OR icons
    setupORIcons()

    const router = new Router(outlet, { baseUrl: getRootPath() })

    initRouter(router)
}

function initRouter(router: Router) {
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
    router.setRoutes(routes)
}

// Entry point
await init()
