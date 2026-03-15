/** @odoo-module **/

import { _t } from '@web/core/l10n/translation';
import { patch } from '@web/core/utils/patch';
import { Chatter } from '@mail/core/web/chatter';
import { useBus } from '@web/core/utils/hooks';

patch(Chatter.prototype, {
    setup() {
        super.setup();

        useBus(this.env.bus, 'CHATTER:SWITCH', (args) => {
            const formRenderer = document.querySelector('.o_form_renderer');
            const chatter = document.querySelector('.oe_chatter');

            if (!this.props.isChatterAside || this.store.focusChatter === false) {
                formRenderer.classList.remove('flex-column');
                formRenderer.classList.add('flex-nowrap', 'h-100');
                document.querySelector('.o_form_view.o_action').classList.add('o_xxl_form_view', 'h-100');
                chatter.classList.remove('mt-4', 'mt-md-0');
                chatter.classList.add('o-aside');
                document.querySelector('.o-mail-Thread').classList.add('pb-4');
                this.store.focusChatter = true;
            } else {
                formRenderer.classList.remove('flex-nowrap', 'h-100');
                formRenderer.classList.add('flex-column');
                document.querySelector('.o_form_view.o_action').classList.remove('o_xxl_form_view', 'h-100');
                chatter.classList.remove('o-aside');
                chatter.classList.add('mt-4', 'mt-md-0');
                document.querySelector('.o-mail-Thread').classList.remove('pb-4');
                document.querySelector('.o_form_view .o_form_sheet_bg').style.maxWidth = 'unset';
                this.store.focusChatter = false;
            }
            this.props.isChatterAside = !this.props.isChatterAside;
            this.render();
        });
    }
});