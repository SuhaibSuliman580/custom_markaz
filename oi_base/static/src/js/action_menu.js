/** @odoo-module */

import { ListController } from '@web/views/list/list_controller';
import { FormController } from '@web/views/form/form_controller';
import { patch } from "@web/core/utils/patch";
import {RecordInfoDialog} from '@oi_base/js/record_info';
import { _lt } from "@web/core/l10n/translation";

patch(FormController.prototype, {

	getStaticActionMenuItems() {
		const res = super.getStaticActionMenuItems();
		res.record_info = {
			isAvailable: () => true,
			sequence: 100,
			icon: "fa fa-info",
			description: _lt("Record Info"),
			callback: async () => {
				const dialogProps = await this.model.orm.call(this.model.root.resModel, "get_record_info", [this.model.root.resId]);
				await this.dialogService.add(RecordInfoDialog, dialogProps);					
			}
		}
		return res;
	},

});

patch(ListController.prototype, {

	getStaticActionMenuItems() {
		const res = super.getStaticActionMenuItems();
		res.record_info = {
			isAvailable: () => true,
			sequence: 100,
			icon: "fa fa-info",
			description: _lt("Record Info"),
			callback: async () => {
				var ids = await this.getSelectedResIds();
				if (ids.length > 1)
					ids = ids.slice(0,1);
				const dialogProps = await this.model.orm.call(this.model.root.resModel, "get_record_info", ids);
				await this.dialogService.add(RecordInfoDialog, dialogProps);					
			}
		}
		return res;
	},

});
