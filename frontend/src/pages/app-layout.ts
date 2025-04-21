// main-layout.ts

import { createContext, provide } from '@lit/context'
import { RouterLocation } from '@vaadin/router'
import { html, LitElement } from 'lit'
import { customElement, state } from 'lit/decorators.js'
import { setRealmTheme } from '../util'
import '../components/breadcrumb-nav'

export const realmContext = createContext<string>(Symbol('realm'))

@customElement('app-layout')
export class AppLayout extends LitElement {
    // Provide the realm context to all child elements
    @provide({ context: realmContext })
    @state()
    realm = ''

    // Set the realm when the route changes
    onBeforeEnter(location: RouterLocation) {
        this.realm = location.params.realm as string
        setRealmTheme(this.realm)
    }

    // Render the breadcrumb nav and slot
    render() {
        return html`
            <breadcrumb-nav realm=${this.realm}></breadcrumb-nav>
            <slot></slot>
        `
    }
}
