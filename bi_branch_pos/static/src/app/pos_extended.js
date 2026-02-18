
/** @odoo-module */

import { Order, Orderline, Payment } from "@point_of_sale/app/store/models";
import { patch } from "@web/core/utils/patch";

patch(Order.prototype, {
		setup(_defaultObj, options) {
			super.setup(...arguments);
			this.branch_id = this.branch_id || "";
		},
		set_branch(branch_id) {
            this.branch_id = branch_id;
        },

        get_branch() {
            return this.branch_id;
        },

        init_from_JSON(json) {
            super.init_from_JSON(...arguments);
            this.branch_id = json.branch_id || "";
        },

        export_as_JSON() {
            const json = super.export_as_JSON(...arguments);
            json.branch_id = this.get_branch() || "";
            return json;
        },

        export_for_printing() {
            const json = super.export_for_printing(...arguments);
            json.branch_id = this.get_branch() || "";
            return json;
        },
		getDisplayData() {
			return {
			...super.getDisplayData(),
			// stayStr: this.get_to_staystr(),
			};
		}
});

