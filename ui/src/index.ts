import { Router } from '@vaadin/router';
import "./pages/pages-config-list";
import "./pages/pages-config-details";
import "./components/breadcrumb";
import { IconSet, createSvgIconSet, IconSets, OrIconSet } from "@openremote/or-icon";
import { html, render } from 'lit';
const outlet = document.querySelector('#outlet') as HTMLElement;
const router = new Router(outlet);

function setupORIcons() {

    function createMdiIconSet(): IconSet {
        return {
            getIconTemplate(icon: string) {
                return html`<span style="font-family: 'Material Design Icons';" class="mdi-${icon}"></span>`;
            },
            onAdd(): void {
                const style = document.createElement("style");
                style.id = "mdiFontStyle";
                style.textContent = "@font-face {\n" +
                    "  font-family: \"Material Design Icons\";\n" +
                    "  src: url(\"/node_modules/@mdi/font/materialdesignicons-webfont.eot\");\n" +
                    "  src: url(\"/node_modules/@mdi/font/materialdesignicons-webfont.eot\") format(\"embedded-opentype\"), url(\"/node_modules/@mdi/font/materialdesignicons-webfont.woff2\") format(\"woff2\"), url(\"/node_modules/@mdi/font/materialdesignicons-webfont.woff\") format(\"woff\"), url(\"/node_modules/@mdi/font/materialdesignicons-webfont.ttf\") format(\"truetype\");\n" +
                    "  font-weight: normal;\n" +
                    "  font-style: normal;\n" +
                    "}";
                document.head.appendChild(style);
            }
        };
    }

    IconSets.addIconSet(
        "mdi",
        createMdiIconSet()
    );
    IconSets.addIconSet(
        "or",
        createSvgIconSet(OrIconSet.size, OrIconSet.icons)
    );
}



setupORIcons();

const routes = [
    {
        path: '/',
        redirect: '/configs',
        title: 'Home',
    },
    {
        path: '/configs',
        component: 'page-config-list',
        title: 'Configs',
    },
    {
        path: '/configs/:id',
        component: 'page-config-details',
        title: 'Config Details',
    },
]

// Render the breadcrumb component
render(html`<breadcrumb-nav></breadcrumb-nav>`, outlet);

// Set up the router
router.setRoutes(routes);
