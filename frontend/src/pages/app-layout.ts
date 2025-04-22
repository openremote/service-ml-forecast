// main-layout.ts

import { createContext, provide } from '@lit/context'
import { Router, RouterLocation } from '@vaadin/router'
import { html, LitElement } from 'lit'
import { customElement, state } from 'lit/decorators.js'
import { setRealmTheme } from '../util'
import '../components/breadcrumb-nav'
import { AuthService } from '../services/auth-service'

export interface AppContext {
    realm: string
}

export const context = createContext<AppContext>(Symbol('app'))

@customElement('app-layout')
export class AppLayout extends LitElement {
    @provide({ context })
    @state()
    app: AppContext = {
        realm: ''
    }

    defaultRealm = 'master'

    @state()
    private authenticated = false

    async onBeforeEnter(location: RouterLocation) {
        const realm = location.params.realm as string
        this.app.realm = realm

        if (!this.app.realm) {
            console.log('No realm found, redirecting to master')
            Router.go(`/master`)
        }
        this.app = {
            realm: this.app.realm
        }

        // Update the app theme with the realm
        setRealmTheme(this.app.realm)

        this.authenticated = AuthService.authenticated
        AuthService.subscribe(() => {
            this.authenticated = AuthService.authenticated
        })
    }

    render() {
        if (!this.authenticated) {
            return html` <div>Unauthenticated</div> `
        }

        return html`
            <breadcrumb-nav realm=${this.app.realm}></breadcrumb-nav>
            <slot></slot>
        `
    }
}
