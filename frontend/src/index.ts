import { Router } from '@vaadin/router'
import './pages/pages-config-list'
import './pages/pages-config-editor'
import './pages/pages-not-found'
import './pages/app-layout'
import { setupORIcons, getRootPath } from './util'
import { AuthService } from './services/auth-service'

async function init() {
    const outlet = document.querySelector('#outlet') as HTMLElement

    // Initialize the auth service
    await initAuthService()

    // Setup OR icons
    setupORIcons()

    // Setup the router -- Vaadin expects a trailing slash in the baseUrl
    const router = new Router(outlet, { baseUrl: getRootPath() + '/' })

    initRouter(router)
}

async function initAuthService() {
    // Realm is provided via the query params, if not provided we will use master as fallback
    let authRealm = new URLSearchParams(window.location.search).get('realm')

    if (!authRealm) {
        authRealm = 'master' // Fallback
    }

    // Initialize the auth service - This will trigger a login if required, prefers SSO if available
    const authenticated = await AuthService.init(authRealm)
    if (!authenticated) {
        AuthService.login()
        return
    }
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
