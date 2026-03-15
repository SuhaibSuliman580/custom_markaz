/** @odoo-module */

import { _t } from '@web/core/l10n/translation';
import { patch } from '@web/core/utils/patch';
import { useService } from '@web/core/utils/hooks';
import { onWillUnmount } from '@odoo/owl';
import { KanbanController } from '@web/views/kanban/kanban_controller';
import { FormViewDialog } from '@web/views/view_dialogs/form_view_dialog';

import { encodeRecordUrl } from '../../webclient/action_utils';


patch(KanbanController.prototype, {
    setup() {
        super.setup();
        this.ui = useService('ui');

        onWillUnmount(() => {
            if (this.ui.dropinMode) {
                this.ui.dropinMode = false;
            }
        });
    },

    async openRecord(record) {
        if (!this.ui.dropinMode && !this.ui.ctrlKey && !this.ui.shiftKey) {
            await super.openRecord(record); return;
        }

        const controller = this.actionService.currentController;
        const hasFormView = controller.views?.some((view) => view.type === 'form');

        if (!hasFormView || this.env.inDialog) {
            await super.openRecord(record); return;
        }
        if (this.ui.ctrlKey) {
            const act = encodeRecordUrl(record, controller.action);
            await this.actionService.doAction(act);
            return;
        } else if (this.ui.shiftKey) {
            this.ui.dropinMode = true;
        }
        if (this.ui.dropinMode) {
            record.model.dialog.add(FormViewDialog, {
                size: 'xl',
                resModel: record.resModel,
                resId: record.resId,
                onRecordSaved: async () => {
                    await this.model.load();
                },
            });
        }
    },
});
