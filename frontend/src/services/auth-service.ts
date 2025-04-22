import Keycloak from 'keycloak-js'

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

    async init(realm: string, force = false): Promise<boolean> {
        if (this.initializing && !force) {
            return this.initPromise!
        }
        if (this.keycloak && this.realm === realm && !force) {
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

export const AuthService = new AuthServiceClass()
