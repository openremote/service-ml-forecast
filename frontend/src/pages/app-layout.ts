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
    @provide({ context: realmContext })
    @state()
    realm = ''

    onBeforeEnter(location: RouterLocation) {
        this.realm = location.params.realm as string
        setRealmTheme(this.realm)
    }

    render() {
        return html`
            <breadcrumb-nav realm=${this.realm}></breadcrumb-nav>
            <slot></slot>
        `
    }
}
