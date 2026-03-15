/* @odoo-module */

import { patch } from '@web/core/utils/patch';
import { utils, SIZES } from '@web/core/ui/ui_service';
import { FormRenderer } from '@web/views/form/form_renderer';


patch(FormRenderer.prototype, {
    setup() {
        super.setup();

        const uiPureSize = utils.getPureSize();
        if (uiPureSize !== this.uiService.size) {
            this.puxSize = this.uiService.size;
        }
    },

    /**
     * @returns {boolean}
     */
    hasFileViewer() {
        // Patch XL can show sided document preview
        if (this.uiService.size >= SIZES.XL && this.puxSize == SIZES.XL) {
            if (!this.mailStore || !this.props.record.resId) {
                return false;
            }
            this.messagingState.thread = this.mailStore.Thread.insert({
                id: this.props.record.resId,
                model: this.props.record.resModel,
                type: 'chatter',
            });
            return this.messagingState.thread.attachmentsInWebClientView.length > 0;
        }
        return super.hasFileViewer();
    },
});
