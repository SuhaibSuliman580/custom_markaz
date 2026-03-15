/** @odoo-module **/

import { Component } from "@odoo/owl";

export class CommandPalette extends Component {
    static props = {};

    openMainPalette() {
        this.env.services.command.openMainPalette({
            searchValue: '',
            bypassEditableProtection: true,
            global: true,
        })
    }
}

CommandPalette.template = 'uweb.CommandPalette';
