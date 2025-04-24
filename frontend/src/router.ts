import { Router } from '@vaadin/router'
import { getRootPath } from './common/util'
import { APP_OUTLET } from './common/constants'
import './pages/pages-config-list'
import './pages/pages-config-editor'
import './pages/pages-not-found'
import './components/loading-spinner'
import './pages/app-layout'

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

export function setupRouter() {
    // Setup the router -- Vaadin expects a trailing slash in the baseUrl
    const router = new Router(APP_OUTLET, { baseUrl: getRootPath() + '/' })
    router.setRoutes(routes)
}
