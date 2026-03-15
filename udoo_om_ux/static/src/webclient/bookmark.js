/** @odoo-module **/

import { _t } from '@web/core/l10n/translation';
import { encodeCurrentAction } from './action_utils';
import { useService } from '@web/core/utils/hooks';
import { hasTouch, isIosApp, isMacOS } from '@web/core/browser/feature_detection';
import { Component } from '@odoo/owl';
import { Dropdown } from '@web/core/dropdown/dropdown';


export const actionBookmarkThis = async (env, pin = false) => {
    const currentAction = encodeCurrentAction(env);
    if (!currentAction) return;

    if (pin) {
        currentAction.pinned = true;
    }
    env.services.ui.bookmarks.push(currentAction);
    await env.services.user.setUserSettings('up_bookmarks', JSON.stringify(env.services.ui.bookmarks));

    env.services.notification.add(
        _t('Bookmark saved. Type ALT+K to access it!'),
        {
            type: 'success',
            title: _t('Notification'),
            className: 'udoo_bookmark_notify',
        }
    );
}

export const bookmarkProvider = async (env, options) => {
    const bookmarks = env.services.ui.bookmarks;

    const lastBookmarkIdx = bookmarks.length - 1;
    const bookmarkCommands = bookmarks.toReversed().map((record, idx) => {
        const act_name = record?.name;
        const itemIdx = lastBookmarkIdx - idx;
        let can_oint = record.type == 'ir.actions.client' || (record.type == 'ir.actions.act_window' && record.view_type == 'form');
        return {
            name: act_name || _t('Undefined'),
            view_type: record.view_type,
            category: record.pinned ? 'pin' : 'norm',
            is_action: true,
            can_oint: can_oint,
            action: () => {
                env.services.action.doAction(record);
            },
            ointAction: async () => {
                const act_url = { type: 'ir.actions.act_url' };

                if (record.type == 'ir.actions.act_window') {
                    act_url.url = `web#model=${record.res_model}&view_type=${record.view_type}`;
                    if (record.res_id) {
                        act_url.url = `${act_url.url}&id=${record.res_id}`;
                    }
                    if (record.act_id) {
                        act_url.url = `${act_url.url}&action=${record.act_id}`;
                    }
                } else if (record.type == 'ir.actions.client') {
                    act_url.url = `web#action=${record.act_id}`;
                    if (record.ctx_aid) {
                        act_url.url = `${act_url.url}&active_id=${record.ctx_aid}`;
                    }
                }
                env.services.action.doAction(act_url);
            },
            unpinAction: async () => {
                bookmarks[itemIdx].pinned = false;
                await syncBookmark(env, bookmarks);
            },
            pinAction: async () => {
                bookmarks[itemIdx].pinned = true;
                await syncBookmark(env, bookmarks);
            },
            deleteAction: async () => {
                bookmarks.splice(itemIdx, 1);
                await syncBookmark(env, bookmarks);
            },
        }
    });

    return bookmarkCommands;
};

async function syncBookmark(env, bookmarks) {
    await env.services.user.setUserSettings('up_bookmarks', JSON.stringify(bookmarks));
    env.bus.trigger('CMD:REFRESH', '');
}

export class BookmarkFooter extends Component {
    static props = {
        //prop added by the command palette
        switchNamespace: { type: Function, optional: true },
    };

    setup() {
        this.ui = useService('ui');
        this.action = useService('action');
        this.altKey = isMacOS() ? 'OPTION' : 'ALT';
    }

    async bookmarkThis() {
        await actionBookmarkThis(this.env);
        this.env.bus.trigger('CMD:REFRESH', '');
    }

    async bookmarkPinThis() {
        await actionBookmarkThis(this.env, true);
        this.env.bus.trigger('CMD:REFRESH', '');
    }

    async removeAllUnpinBookmark() {
        const bookmarks = this.ui.bookmarks
        this.ui.bookmarks = bookmarks.filter(o => o.pinned);
        await syncBookmark(this.env, this.ui.bookmarks);
    }

    async removeAllBookmark() {
        this.ui.bookmarks = [];
        await syncBookmark(this.env, this.ui.bookmarks);
    }
}

BookmarkFooter.template = 'uweb.BookmarkManager.Footer';
BookmarkFooter.components = { Dropdown };

export const bookmarkPalette = {
    configByNamespace: {
        default: {
            categories: ['pin', 'norm'],
            categoryNames: {
                'pin': _t('Pinned'),
            },
        },
    },
    providers: [{ provide: bookmarkProvider }],
    FooterComponent: BookmarkFooter,
}

export function openBookmarkPalette(env) {
    env.services.command.openPalette(bookmarkPalette);
}
