/** @odoo-module **/

import { patch } from '@web/core/utils/patch';
import { useBus } from '@web/core/utils/hooks';
import { StatusBarField } from '@web/views/fields/statusbar/statusbar_field';

patch(StatusBarField.prototype, {
    setup() {
        super.setup();

        useBus(this.env.bus, 'SBAR:ADJVIS', (args) => {
            this.adjustVisibleItems();
        });
    }
});