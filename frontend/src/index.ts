import { Router } from '@vaadin/router'
import './pages/pages-config-list'
import './pages/pages-config-editor'
import './components/breadcrumb'
import './pages/pages-not-found'
import './pages/pages-service-unavailable'
import { html, render } from 'lit'
import { setRealmTheme, setupORIcons } from './util'
import { ApiService } from './services/api-service'

const apiService = new ApiService()
const outlet = document.querySelector('#outlet') as HTMLElement
const router = new Router(outlet)

async function init() {
    setupORIcons()

    const backendIsAvailable = await apiService.isServiceAvailable()
    if (!backendIsAvailable) {
        render(html`<page-service-unavailable></page-service-unavailable>`, outlet)
        return
    }

    // Load realm theme
    await setRealmTheme()

    // Render breadcrumb component
    render(html`<breadcrumb-nav></breadcrumb-nav>`, outlet)

    initRouter()
}

function initRouter() {
    const routes = [
        {
            path: '/:realm/configs',
            component: 'page-config-list'
        },
        {
            path: '/:realm/configs/new',
            component: 'page-config-viewer'
        },
        {
            path: '/:realm/configs/:id',
            component: 'page-config-viewer'
        },
        {
            path: '(.*)',
            component: 'page-not-found'
        }
    ]
    router.setRoutes(routes)
}

// Entry point
await init()
