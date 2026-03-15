/** @odoo-module **/

import { _t } from '@web/core/l10n/translation';

export const VIEW_IMAP = {
    'form': 'ri-news-line',
    'list': 'ri-list-view',
    'pivot': 'ri-timeline-view',
    'kanban': 'ri-kanban-view-2',
    'graph': 'ri-bar-chart-box-line',
    'calendar': 'ri-calendar-event-line',
    'activity': 'ri-calendar-schedule-line',
    'hierarchy': 'ri-organization-chart',
    'gantt': 'ri-slideshow-view',
    'grid': 'ri-gallery-view',
    'map': 'ri-map-2-line',
    'cohort': 'ri-increase-decrease-line',
}

export function encodeRecordUrl(rec, act) {
    const act_url = {
        type: 'ir.actions.act_url',
        url: `web#id=${rec.resId}&model=${rec.resModel || act.res_model}&view_type=form`,
    };
    if (act.id) {
        act_url.url = `${act_url.url}&action=${act.id}`;
    }
    if (act.context.active_id) {
        act_url.url = `${act_url.url}&active_id=${act.context.active_id}`;
    }
    return act_url;
}

export function encodeCurrentAction(env, hash = true) {
    const controller = env.services.action.currentController;
    if (!controller.action || controller.action.tag === 'invalid_action') {
        return false;
    }

    let displayName = controller.displayName;
    const actionName = controller.action.name;
    let hasSep = displayName.includes(' /');
    let knownPath = true;
    const nameInPath = actionName && actionName !== displayName && actionName.endsWith(displayName);

    if (nameInPath) {
        displayName = actionName;
    } else if (!hasSep && controller.action.name && displayName !== actionName) {
        displayName = `${actionName} / ${displayName}`;
    } else {
        knownPath = false;
    }

    const action = {
        type: controller.action.type,
        name: displayName,
        context: controller.action.context,
        domain: controller.action.domain,
        target: controller.action.target,
    };

    if (!knownPath) {
        const currentApp = env.services.menu.getCurrentApp();
        if (currentApp) {
            action.name = `${currentApp.name} / ${action.name}`;
        }
    }

    if (controller.view?.type) {
        action.view_type = controller.view.type;
    }
    if (controller.action.search_view_id) {
        action.search_view_id = controller.action.search_view_id;
    }
    if (controller.action.id) {
        action.act_id = controller.action.id;
    }

    if (action.type === 'ir.actions.act_window') {
        const valid_views = [];
        controller.action.views.forEach(view => {
            if (view[1] in VIEW_IMAP) {
                if (view[1] !== action.view_type) {
                    valid_views.push(view);
                } else {
                    valid_views.splice(0, 0, view);
                }
            } else {
                valid_views.splice(1, 0, view);
            }
        });

        Object.assign(action, {
            res_model: controller.action.res_model,
            views: valid_views,
            view_mode: controller.action.view_mode,
        });

        if (controller.props?.resId) {
            action.res_id = controller.props.resId;
            action.views = [[false, 'form']];
        }

    } else if (action.type === 'ir.actions.client') {
        const client_act = { tag: controller.action.tag };
        if (controller.action.context?.active_id) {
            client_act.ctx_aid = controller.action.context?.active_id;
        }
        Object.assign(action, client_act);

    } else if (action.type === 'ir.actions.report') {
        Object.assign(action, {
            report_type: controller.action.report_type,
            report_name: controller.action.report_name,
            data: controller.action.data || {},
        });

        if (action.report_file) {
            action.report_file = action.report_file;
        }
    }
    if (hash) {
        // Generate the unique action ID
        action.act_uid = objectHash.MD5(action);
        return action;
    } else {
        return action;
    }
}