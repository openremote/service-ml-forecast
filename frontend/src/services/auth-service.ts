import Keycloak from 'keycloak-js'
import { isEmbedded } from '../util'

const keycloakUrl: string = (process.env.ML_KEYCLOAK_URL || '').replace(/\/$/, '')

type AuthChangeListener = () => void

class AuthServiceClass {
    token: string | undefined = ''
    authenticated: boolean = false
    user: string | undefined = ''
    realm: string = ''
    initializing: boolean = false
    initPromise: Promise<boolean> | null = null
    keycloak: Keycloak | undefined

    private listeners: AuthChangeListener[] = []
    private tokenRefreshInterval: NodeJS.Timeout | null = null

    async init(realm: string, force = false): Promise<boolean> {
        if (this.initializing && !force) {
            console.log('Already initializing', realm)
            return this.initPromise!
        }
        if (this.keycloak && this.realm === realm && !force) {
            console.log('Already initialized', realm)
            return this.authenticated
        }

        this.initializing = true
        this.realm = realm
        const keycloakInstance = new Keycloak({
            url: keycloakUrl,
            realm: realm,
            clientId: 'openremote'
        })

        this.initPromise = keycloakInstance
            .init({
                onLoad: 'check-sso',
                checkLoginIframe: false,
                silentCheckSsoFallback: true
            })
            .then((auth) => {
                this.keycloak = keycloakInstance
                this.authenticated = auth
                this.token = keycloakInstance.token
                this.user = keycloakInstance.tokenParsed?.preferred_username
                this.initializing = false
                this.notify()

                console.log('Initialized KC: ', realm)
                if (!isEmbedded()) {
                    this.startUpdateTokenInterval()
                }

                return auth
            })
            .catch((error) => {
                console.error(`KC initialization failed for realm ${realm}:`, error)
                this.keycloak = undefined
                this.authenticated = false
                this.token = undefined
                this.user = undefined
                this.initializing = false
                this.notify()
                return false
            })

        return this.initPromise
    }

    login() {
        this.keycloak?.login()
    }

    logout() {
        this.keycloak?.logout()
        this.stopUpdateTokenInterval()
    }

    private startUpdateTokenInterval() {
        console.log('Starting token refresh interval')
        if (this.tokenRefreshInterval) {
            clearInterval(this.tokenRefreshInterval)
        }
        this.tokenRefreshInterval = setInterval(() => this.updateToken(), 5000)
    }

    private stopUpdateTokenInterval() {
        console.log('Stopping token refresh interval')
        if (this.tokenRefreshInterval) {
            clearInterval(this.tokenRefreshInterval)
            this.tokenRefreshInterval = null
        }
    }

    async updateToken(): Promise<boolean> {
        if (!this.keycloak) {
            return false
        }
        try {
            const refreshed = await this.keycloak.updateToken(20)
            if (refreshed) {
                console.log('Token refreshed.')
                this.token = this.keycloak.token
                this.notify()
            }
            return refreshed
        } catch (error) {
            console.error('Manual token refresh failed.', error)
            return false
        }
    }

    async ensureAuthenticated(realm: string): Promise<boolean> {
        const authenticated = await this.init(realm)
        if (!authenticated) {
            console.info('Not authenticated, redirecting to login.')
            this.login()
            return false
        }
        return true
    }

    subscribe(listener: AuthChangeListener): () => void {
        this.listeners.push(listener)
        return () => {
            this.listeners = this.listeners.filter((l) => l !== listener)
        }
    }

    private notify(): void {
        this.listeners.forEach((listener) => listener())
    }
}

/**
 * Singleton for handling authentication
 */
export const AuthService = new AuthServiceClass()
