import { Router } from '@vaadin/router';
import "./pages/pages-config-list";
import "./pages/pages-config-details";
import "./pages/pages-not-found";
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
                    "  src: url(\"/static/fonts/materialdesignicons-webfont.eot\") format(\"embedded-opentype\"), url(\"/static/fonts/materialdesignicons-webfont.woff2\") format(\"woff2\"), url(\"/static/fonts/materialdesignicons-webfont.woff\") format(\"woff\"), url(\"/static/fonts/materialdesignicons-webfont.ttf\") format(\"truetype\");\n" +
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
        path: '/configs/new',
        component: 'page-config-details',
        title: 'New Config',
    },
    {
        path: '/configs/:id',
        component: 'page-config-details',
        title: 'Config Details',
    },
    {
        path: '/:pathMatch(.*)*',
        redirect: '/configs',
    },
]

// Render the breadcrumb component
render(html`<breadcrumb-nav></breadcrumb-nav>`, outlet);


router.setRoutes(routes);
