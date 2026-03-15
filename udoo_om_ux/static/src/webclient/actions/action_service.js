/** @odoo-module **/

import { _t } from '@web/core/l10n/translation';
import { patch } from '@web/core/utils/patch';
import { registry } from '@web/core/registry';
import { makeContext } from '@web/core/context';


patch(registry.category('services').get('action'), {
    start(env) {
        const base = super.start(env);

        const { ui, rpc } = env.services;

        const doActionButtonDef = base.doActionButton;

        async function doActionButton(params) {

            if (params.type != 'object' || !params.resId || (!ui.dropinMode && !ui.ctrlKey && !ui.shiftKey)) {
                await doActionButtonDef(params);
                return;
            }
            /* Shadow logic from `doActionButton` */
            const context = makeContext([params.context, params.buttonContext]);
            // call a Python Object method, which may return an action to execute
            let args = [[params.resId]];
            if (params.args) {
                let additionalArgs;
                try {
                    // warning: quotes and double quotes problem due to json and xml clash
                    // maybe we should force escaping in xml or do a better parse of the args array
                    additionalArgs = JSON.parse(params.args.replace(/'/g, '"'));
                } catch {
                    browser.console.error('Could not JSON.parse arguments', params.args);
                }
                args = args.concat(additionalArgs);
            }
            const callProm = await rpc('/web/dataset/call_button', {
                args,
                kwargs: { context },
                method: params.name,
                model: params.resModel,
            });

            /* Execute call prom */
            if (callProm.type != 'ir.actions.act_window' || !callProm.res_id) {
                await doActionButtonDef(params);
                return;
            }
            if (ui.ctrlKey) {
                await base.doAction({
                    type: 'ir.actions.act_url',
                    url: `web#id=${callProm.res_id}&active_id=${params.resId}&model=${callProm.res_model}&view_type=form`,
                });
                return;
            } else if (ui.shiftKey) {
                ui.dropinMode = true;
            }
            if (ui.dropinMode) {
                ui.bus.trigger('LIST:DROIN', {
                    resModel: callProm.res_model,
                    resId: callProm.res_id,
                });
            }
        };

        base.doActionButton = doActionButton;

        return base;
    }
});