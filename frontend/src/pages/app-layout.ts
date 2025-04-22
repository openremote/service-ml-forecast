// main-layout.ts

import { createContext, provide } from '@lit/context'
import { Router, RouterLocation } from '@vaadin/router'
import { html, LitElement } from 'lit'
import { customElement, state } from 'lit/decorators.js'
import { setRealmTheme } from '../util'
import '../components/breadcrumb-nav'
import { AuthService } from '../services/auth-service'

export const context = createContext<string>(Symbol('realm'))

@customElement('app-layout')
export class AppLayout extends LitElement {
    @provide({ context })
    @state()
    realm = undefined

    @state()
    private authenticated = false

    async onBeforeEnter(location: RouterLocation) {
        const realm = location.params.realm as string
        this.realm = realm

        // Try authservice if param is not provided
        if (!this.realm) {
            this.realm = AuthService.realm
            Router.go(`/${this.realm}`)
        }

        // Update the app theme with the realm
        setRealmTheme(this.realm)

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
            <breadcrumb-nav realm=${this.realm}></breadcrumb-nav>
            <slot></slot>
        `
    }
}
