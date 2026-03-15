/** @odoo-module **/

import { _t } from '@web/core/l10n/translation';
import { patch } from '@web/core/utils/patch';
import { useDebounced } from '@web/core/utils/timing';
import { useBus, useService } from '@web/core/utils/hooks';
import { useState } from '@odoo/owl';

import { ControlPanel } from '@web/search/control_panel/control_panel';
import { ConfirmationDialog } from '@web/core/confirmation_dialog/confirmation_dialog';

import { useFormStatusIndicatorState } from '../views/form/form_status/indicator';
import { useUdooLocalStore, useUdooStore } from '../webclient/webclient';

const RFS_KEY_FRAMES = [
    { opacity: 0.9 },
    { transform: 'translateY(17px)', opacity: 0 },
    { opacity: 1 },
];

patch(ControlPanel.prototype, {

    setup() {
        super.setup();

        if (this.env.services['mail.store']) {
            this.store = useState(useService('mail.store'));
        }
        this.dialogService = useService('dialog'); // Duplicated in v18
        this.ui = useService('ui');
        this.ue = useUdooLocalStore();
        this.uo = useUdooStore();

        useBus(this.env.bus, 'CTL:SRSH', ({ detail }) => {
            const { formIndicatorState } = this;
            if (detail?.skipOnDirty && formIndicatorState && typeof formIndicatorState.displayButtons === 'function' && !!(formIndicatorState.displayButtons())) {
                return;
            }
            this._doRefresh(true);
        });

        this.formIndicatorState = useFormStatusIndicatorState();
        this.doRefresh = useDebounced(this.doRefresh, 200);
    },

    async doRefresh() {
        const { config, searchModel, services } = this.env;
        const { pagerProps, formIndicatorState } = this;

        if (formIndicatorState && typeof formIndicatorState.displayButtons === 'function') {
            const hasDataUnsaved = !!(formIndicatorState.displayButtons());
            if (hasDataUnsaved) {
                this.dialogService.add(ConfirmationDialog, {
                    body: _t('There is unsaved data. Do you want to discard the changes and proceed?'),
                    confirm: async () => {
                        await formIndicatorState.discard();
                        return this._doRefresh();
                    },
                    cancel: () => { },
                });
                return;
            }
        }
        return this._doRefresh();
    },

    initLayter() {
        this.store.focusChatter = document.querySelectorAll('.oe_chatter.o-aside').length > 0;
        this.hasChatter = document.querySelectorAll('.oe_chatter').length > 0;
        this.hasAttachmentPreview = document.querySelectorAll('div.o_attachment_preview').length > 0;
        this.onKanban = document.querySelectorAll('.o_action_manager>.o_kanban_view').length > 0;
        this.hasList = document.querySelectorAll('.o_list_table').length > 0;
    },

    switchAside() {
        this.env.bus.trigger('CHATTER:SWITCH');
        this.env.bus.trigger('TREE:OMCL');
        this.env.bus.trigger('SBAR:ADJVIS');
    },

    switchFloorMode() {
        this.ui.dropinMode = !this.ui.dropinMode;
        this.state.dropinMode = this.ui.dropinMode;

        // OWL: Call to renew ui state
        this.state.dropinMode;
    },

    async _doRefresh(silent = false) {
        const { searchModel } = this.env;
        // Refresh effect
        if (!silent) {
            document.querySelector('.o_content')?.animate(RFS_KEY_FRAMES, {
                duration: 300,
                easing: 'ease-out',
            });
        }

        // If has pager try it first
        if (this.pagerProps && typeof this.pagerProps.onUpdate === 'function') {
            const { limit, offset } = this.pagerProps;
            await this.pagerProps.onUpdate({ offset, limit });
        }
        // Other case (setting form, ...)
        else if (searchModel && typeof searchModel.search === 'function') {
            searchModel.search();
        }
        // Other case (ir.actions.report, ir.actions.client)
        else {
            this.actionService.loadState();
        }
    },

    backTrick() {
        const backBtn = document.querySelector('.breadcrumb-item.o_back_button');
        if (backBtn) {
            backBtn.click();
        } else {
            this.actionService.restore();
        }
    }
});
