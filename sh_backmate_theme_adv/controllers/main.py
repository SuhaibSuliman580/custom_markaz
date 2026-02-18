# -*- coding: utf-8 -*-
# Copyright (C) Softhealer Technologies.

from odoo import http
from odoo.http import request
import json
import base64

dict_pre_theme_color_style = {
    'pre_color_1': {
        'theme_color': 'color_1',
        'theme_style': 'style_1',
        'primary_color': '#111c43',
        'secondary_color': '#FFFFFF',
        'kanban_box_style': 'style_2',
        'header_background_color': '#ebedf6',
        'body_background_color': '#ebedf6',
        'header_font_color': '#111c43',
        'sidebar_is_show_nav_bar': True,
        'sidebar_collapse_style': 'expanded',
        'sidebar_background_style': 'color',
        'sidebar_background_color': '#111c43',
        'sidebar_font_color': '#e2e8f0',
        'separator_color': '#111c43',
        'separator_style': 'style_7',
        'button_style': 'style_4',
        'body_background_type': 'bg_color',
        'body_font_family': 'Poppins',
        'body_google_font_family': 'inter',
        'is_used_google_font': True,
        'predefined_list_view_boolean': False,
        'predefined_list_view_style': 'style_1',
        'list_view_border': 'without_border',
        'list_view_is_hover_row': True,
        'list_view_hover_bg_color': '#111c43',
        'list_view_even_row_color': '#FFFFFF',
        'list_view_odd_row_color': '#FFFFFF',
        'login_page_style': 'style_2',
        'login_page_style_comp_logo': False,
        'login_page_background_type': 'bg_color',
        'progress_style': 'style_1',
        'progress_height': '4px',
        'progress_color': '#2C3782',
        'is_sticky_pivot': False,
        'horizontal_tab_style': 'style_4',
        'form_element_style': 'style_1',
        'breadcrumb_style': 'style_1',
        'search_style': 'expanded',
        'icon_style': 'light_icon',
        'dual_tone_icon_color_1': '#FFFFFF',
        'dual_tone_icon_color_2': '#2C3782',
        'checkbox_style': 'style_2',
        'radio_btn_style': 'style_1',
        'scrollbar_style': 'style_1',
        'backend_all_icon_style': 'style_2',
        'is_sticky_form':True,
        'is_sticky_list':True,
        'is_sticky_list_inside_form':True,
        'header_background_type': 'header_color',
    },
}
class ThemeConfigController(http.Controller):

    @http.route('/api/upload/multi', type='http', auth="none", csrf=False)
    def Upload_image(self, **kwargs):

        theme_setting_rec = request.env['sh.back.theme.config.settings'].sudo().search([
            ('id', '=', 1)], limit=1)
        if kwargs.get('body_background_img'):
            body_background_img = base64.b64encode(
                kwargs.get('body_background_img').read())
            if theme_setting_rec:
                theme_setting_rec.write(
                    {'body_background_image': body_background_img})

        if kwargs.get('header_background_img'):
            body_background_img = base64.b64encode(
                kwargs.get('header_background_img').read())
            if theme_setting_rec:
                theme_setting_rec.write(
                    {'header_background_image': body_background_img})

        if kwargs.get('sidebar_background_img'):
            sidebar_background_img = base64.b64encode(
                kwargs.get('sidebar_background_img').read())
            if theme_setting_rec:
                theme_setting_rec.write(
                    {'sidebar_background_image': sidebar_background_img})

        if kwargs.get('loading_gif'):
            loading_gif = base64.b64encode(kwargs.get('loading_gif').read())
            if theme_setting_rec:
                theme_setting_rec.write({'loading_gif': loading_gif})

        if kwargs.get('login_page_banner_img'):
            login_page_banner_image = base64.b64encode(
                kwargs.get('login_page_banner_img').read())
            if theme_setting_rec:
                theme_setting_rec.write(
                    {'login_page_banner_image': login_page_banner_image})

        if kwargs.get('login_page_icon_img'):
            login_page_icon_img = base64.b64encode(
                kwargs.get('login_page_icon_img').read())
            if theme_setting_rec:
                theme_setting_rec.write(
                    {'login_page_icon_img': login_page_icon_img})
        if kwargs.get('login_page_icon_img_long'):
            login_page_icon_img_long = base64.b64encode(
                kwargs.get('login_page_icon_img_long').read())
            if theme_setting_rec:
                theme_setting_rec.write(
                    {'login_page_icon_img_long': login_page_icon_img_long})

        if kwargs.get('login_page_background_img'):
            login_page_background_image = base64.b64encode(
                kwargs.get('login_page_background_img').read())
            if login_page_background_image:
                theme_setting_rec.write(
                    {'login_page_background_image': login_page_background_image})

        return json.dumps({})

    @http.route('/get_theme_style', type='json', auth="public")
    def get_theme_style(self):
        theme_setting_rec = request.env['sh.back.theme.config.settings'].sudo().search([
            ('id', '=', 1)], limit=1)
        active_color = '1'
        active_style = '1'
        active_pre_color = 'pre_color_1'
        if theme_setting_rec.theme_style:
            active_style = str(theme_setting_rec.theme_style).split('_')[1]
        if theme_setting_rec.theme_color:
            active_color = str(theme_setting_rec.theme_color).split('_')[1]
        if theme_setting_rec.pre_theme_style:
            active_pre_color = theme_setting_rec.pre_theme_style

        data_html = ' <div class="sh_main_div">  <input type="hidden" class="current_active_style" value="style_' + \
                    active_style + '"/><input type="hidden" class="current_active_style_pallete"/>'
        data_color = ' <div class="sh_main_div">  <input type="hidden" class="current_active_color" value="color_' + \
                     active_color + '"/><input type="hidden" class="current_active_color_pallete"/>'
        data_pre_color = ' <div class="sh_main_div">  <input type="hidden" class="current_active_pre_color" value="' + \
                         active_pre_color + '"/><input type="hidden" class="current_active_pre_color_pallete"/>'

        if theme_setting_rec:
            i = 1
            for theme_style in range(1):
                data_html += '<li class="sh_div_plt"><div class="theme_style_box" id="style_' + \
                             str(i) + '"><input type="radio" name="themeStyle"> <span class="circle fa fa-check-circle"></span> <div class="sh_style_box_' + \
                             str(i) + '"></div></label></li>'
                i += 1

            j = 1
            for theme_color in range(7):
                data_color += '<li class="sh_div_plt"><div class="theme_color_box" id="color_' + \
                              str(j) + '"><input type="radio" name="themeColor"> <i class="fa fa-check-circle"></i> <div class="sh_color_box_' + \
                              str(j) + '"></div></label></li>'
                j += 1

            k = 1
            for pre_theme_color in range(1):
                data_pre_color += '<li class="sh_div_plt"><div class="pre_theme_color_box" id="pre_color_' + \
                                  str(k) + '"><input type="radio" name="preThemeColor"> <i class="fa fa-check-circle"></i> <div class="sh_pre_color_box_' + \
                                  str(k) + '"></div></label></li>'
                k += 1

        return {'data_html': data_html,
                'data_color': data_color,
                'data_pre_color': data_pre_color,
                'primary_color': theme_setting_rec.primary_color,
                'kanban_box_style': theme_setting_rec.kanban_box_style,
                'secondary_color': theme_setting_rec.secondary_color,
                'header_background_color': theme_setting_rec.header_background_color,
                'header_font_color': theme_setting_rec.header_font_color,
                'body_background_color': theme_setting_rec.body_background_color,
                'body_font_family': theme_setting_rec.body_font_family,
                'body_google_font_family': theme_setting_rec.body_google_font_family,
                'body_background_type': theme_setting_rec.body_background_type,
                'header_background_type':theme_setting_rec.header_background_type,
                'button_style': theme_setting_rec.button_style,
                'separator_style': theme_setting_rec.separator_style,
                'separator_color': theme_setting_rec.separator_color,
                'icon_style': theme_setting_rec.icon_style,
                'dual_tone_icon_color_1': theme_setting_rec.dual_tone_icon_color_1,
                'dual_tone_icon_color_2': theme_setting_rec.dual_tone_icon_color_2,
                'sidebar_font_color': theme_setting_rec.sidebar_font_color,
                'sidebar_background_style': theme_setting_rec.sidebar_background_style,
                'sidebar_background_color': theme_setting_rec.sidebar_background_color,
                'sidebar_collapse_style': theme_setting_rec.sidebar_collapse_style,
                'predefined_list_view_boolean': theme_setting_rec.predefined_list_view_boolean,
                'predefined_list_view_style': theme_setting_rec.predefined_list_view_style,
                'list_view_border': theme_setting_rec.list_view_border,
                'list_view_even_row_color': theme_setting_rec.list_view_even_row_color,
                'list_view_odd_row_color': theme_setting_rec.list_view_odd_row_color,
                'list_view_is_hover_row': theme_setting_rec.list_view_is_hover_row,
                'list_view_hover_bg_color': theme_setting_rec.list_view_hover_bg_color,
                'login_page_style': theme_setting_rec.login_page_style,
                'login_page_style_comp_logo': theme_setting_rec.login_page_style_comp_logo,
                'login_page_background_type': theme_setting_rec.login_page_background_type,
                'login_page_box_color': theme_setting_rec.login_page_box_color,
                'login_page_background_color': theme_setting_rec.login_page_background_color,
                'is_sticky_form': theme_setting_rec.is_sticky_form,
                'is_sticky_list': theme_setting_rec.is_sticky_list,
                'is_sticky_list_inside_form': theme_setting_rec.is_sticky_list_inside_form,
                'is_sticky_pivot': theme_setting_rec.is_sticky_pivot,
                'tab_style': theme_setting_rec.tab_style,
                'tab_mobile_style': theme_setting_rec.tab_style_mobile,
                'horizontal_tab_style': theme_setting_rec.horizontal_tab_style,
                'form_element_style': theme_setting_rec.form_element_style,
                'search_style': theme_setting_rec.search_style,
                'navbar_style': theme_setting_rec.navbar_style,
                'breadcrumb_style': theme_setting_rec.breadcrumb_style,
                'progress_style': theme_setting_rec.progress_style,
                'progress_height': theme_setting_rec.progress_height,
                'progress_color': theme_setting_rec.progress_color,
                'checkbox_style': theme_setting_rec.checkbox_style,
                'radio_btn_style': theme_setting_rec.radio_btn_style,
                'scrollbar_style': theme_setting_rec.scrollbar_style,
                'backend_all_icon_style': theme_setting_rec.backend_all_icon_style,
                'pre_theme_style':theme_setting_rec.pre_theme_style,
                'theme_style':theme_setting_rec.theme_style,
                'theme_color':theme_setting_rec.theme_color,
                }

    @http.route('/update/theme_style', type='json', auth="public")
    def update_theme_style_sidebar(self, color_id):
        theme_setting_rec = request.env['sh.back.theme.config.settings'].sudo().search([
            ('id', '=', 1)], limit=1)
        theme_style = 'color_' + \
                      theme_setting_rec.theme_color.split(
                          '_')[1] + '_' + color_id.split('_')[1]

        if selected_theme_style_dict:
            theme_setting_rec.update(selected_theme_style_dict)
            theme_setting_rec.write(
                {'theme_style': 'style_' + color_id.split('_')[1]})

        return {}

    @http.route('/update/navbar_style', type='json', auth="public")
    def update_theme_style(self, is_navbar_style):
        theme_setting_rec = request.env['sh.back.theme.config.settings'].sudo().search([
            ('id', '=', 1)], limit=1)
        if theme_setting_rec:
            if is_navbar_style:
                theme_setting_rec.write({'is_navbar_style':True})
            else:
                theme_setting_rec.write({'is_navbar_style': False})
        return {}


    @http.route('/update/theme_style_pre_color', type='json', auth="public")
    def theme_style_pre_color(self, pre_color_id):
        theme_setting_rec = request.env['sh.back.theme.config.settings'].sudo().search([
            ('id', '=', 1)], limit=1)
        pre_theme_color = pre_color_id

        selected_theme_style_dict = dict_pre_theme_color_style.get(
            pre_theme_color, False)

        predefined_style_1_back_image = request.env.ref(
            'sh_backmate_theme_adv.sh_back_theme_config_adv_attachment_predefined_theme_1')

        selected_theme_style_dict.update({
            'body_background_image': predefined_style_1_back_image.datas
        })

        if selected_theme_style_dict:
            theme_setting_rec.update(selected_theme_style_dict)
            theme_setting_rec.write({'pre_theme_style': pre_theme_color})
        return {}

