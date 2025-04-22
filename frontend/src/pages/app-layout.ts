// main-layout.ts

import { createContext, provide } from '@lit/context'
import { Router, RouterLocation } from '@vaadin/router'
import { html, LitElement } from 'lit'
import { customElement, state } from 'lit/decorators.js'
import { getRootPath, setRealmTheme as updateRealmTheme } from '../util'
import '../components/breadcrumb-nav'
import '../components/loading-spinner'
import { AuthService } from '../services/auth-service'

export const context = createContext<string>(Symbol('realm'))

@customElement('app-layout')
export class AppLayout extends LitElement {
    @provide({ context })
    @state()
    realm = undefined

    @state()
    private authenticated = false

    private readonly rootPath = getRootPath()

    async onBeforeEnter(location: RouterLocation) {
        // Try and get realm via location params before entering the route
        const realm = location.params.realm as string
        this.realm = realm

        // Fallback to authservice if param is not provided
        if (!this.realm) {
            this.realm = AuthService.realm
            console.log('No realm param provided, falling back to auth realm:', this.realm)
            Router.go(`${this.rootPath}/${this.realm}`)
        }

        // Update the app with the realm theme
        await updateRealmTheme(this.realm)

        // Listen for auth changes
        this.authenticated = AuthService.authenticated
        AuthService.subscribe(() => {
            this.authenticated = AuthService.authenticated
        })
    }

    render() {
        if (!this.authenticated) {
            return html` <loading-spinner></loading-spinner> `
        }

        return html`
            <breadcrumb-nav realm=${this.realm}></breadcrumb-nav>
            <slot></slot>
        `
    }
}
