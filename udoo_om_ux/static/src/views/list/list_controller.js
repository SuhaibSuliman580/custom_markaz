/** @odoo-module */

import { patch } from '@web/core/utils/patch';
import { useBus, useService } from '@web/core/utils/hooks';
import { onWillUnmount } from '@odoo/owl';
import { ListController } from '@web/views/list/list_controller';
import { FormViewDialog } from '@web/views/view_dialogs/form_view_dialog';

import { encodeRecordUrl } from '../../webclient/action_utils';


patch(ListController.prototype, {
    setup() {
        super.setup();

        this.ui = useService('ui');

        useBus(this.ui.bus, 'LIST:DROIN', async (arg) => {
            this.dialogService.add(FormViewDialog, {
                size: 'xl',
                resModel: arg.detail.resModel,
                resId: arg.detail.resId,
                onRecordSaved: async () => {
                    await this.model.load();
                },
            });
        });

        onWillUnmount(() => {
            if (!this.env.inDialog && this.ui.dropinMode) {
                this.ui.dropinMode = false;
            }
        });
    },

    get condPureOpenRecord() {
        return !this.ui.splitMode && !this.ui.ctrlKey;
    },

    async openRecord(record) {
        const { ui, actionService } = this;
        const vController = actionService.currentController;
        if (this.condPureOpenRecord) {
            super.openRecord(record); return;
        }
        const hasFormView = vController.views?.some((view) => view.type === 'form');
        if (!hasFormView || this.archInfo.openAction || this.env.inDialog) {
            super.openRecord(record); return;
        }
        await this._validOpenRecordOm(record, ui, vController);
    },

    async _validOpenRecordOm(record, ui, vController) {
        if (ui.ctrlKey) {
            const act = encodeRecordUrl(record, vController.action);
            await this.actionService.doAction(act);
            return 'redir';
        }
        if (this._validOpenRecord) {
            this._validOpenRecord(record, ui, vController)
        }
    },

    async expandFoldGroups() {
        const groupToLoad = [];
        this.model.root.groups.forEach(group => {
            const isFolded = !group.config.isFolded;
            group.model._updateConfig(
                group.config,
                { isFolded: isFolded },
                { reload: false }
            );
            if (!isFolded && group.hasData && group.records.length == 0) {
                groupToLoad.push(group);
            }
        });
        groupToLoad.forEach(group => {
            group.list.load();
        });
    },
});
