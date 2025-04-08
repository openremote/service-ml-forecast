import "./pages/pages-config-list";
import "./pages/pages-config-details";
import "./router";
import { html, render } from "lit";

const template = html`
    <app-router></app-router>
`;

render(template, document.body);