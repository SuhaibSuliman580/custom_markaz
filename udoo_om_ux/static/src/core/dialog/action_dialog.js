/** @odoo-module */

import { patch } from '@web/core/utils/patch';
import { Dialog } from '@web/core/dialog/dialog';

const SIZES = ['lg', 'xl', 'fs'];

patch(Dialog.prototype, {
    setup() {
        super.setup();
        this.orgSize = this.props.size;
        this.bkSize = this.props.size;
    },

    toggle_dialog_size(ev) {
        const dialog = ev.target.closest('.modal-dialog');
        dialog.style.alignItems = 'unset';
        const formView = dialog.querySelector('.o_form_view');
        if (formView) {
            formView.style.height = '100%';
        }

        const inbackfs = this.props.size != 'fs';
        if (inbackfs) {
            this.props.size = 'fs';
        } else {
            this.props.size = this.bkSize;
            dialog.style.alignItems = null;
        }

        this.onResize();
        this.render();
    },

    switch_dialog_size() {
        let idx = SIZES.indexOf(this.props.size);
        if (idx === (SIZES.length - 1)) {
            this.props.size = this.orgSize;
        } else {
            this.props.size = SIZES[idx + 1];
        }
        this.bkSize = this.props.size;
        this.render();
    },
});