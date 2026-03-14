from odoo import http
from odoo.http import request


class MemberDirectory(http.Controller):

    def _base_domain(self):
        return [
            ('union_status', '=', 'active'),
            ('name', '!=', False),
        ]

    @http.route(['/members'], type='http', auth='public', website=True, sitemap=True)
    def members(self, q=None, page=1, state_id=None, city=None, specialty_id=None, **kw):
        page = int(page) if page else 1
        step = 24

        Partner = request.env['res.partner'].sudo()
        domain = list(self._base_domain())

        if q:
            domain += [('name', 'ilike', q)]

        if state_id:
            try:
                domain += [('state_id', '=', int(state_id))]
            except Exception:
                state_id = None

        if city:
            city = (city or '').strip()
            if city:
                domain += [('city', '=', city)]
            else:
                city = None

        if specialty_id:
            try:
                specialty_id_int = int(specialty_id)
                domain += [('medical_specialty_id', '=', specialty_id_int)]
            except Exception:
                specialty_id = None

        all_active_doctors = Partner.search(self._base_domain())
        states = all_active_doctors.mapped('state_id').sorted(lambda s: (s.name or '').lower())
        cities = sorted({c for c in all_active_doctors.mapped('city') if c})
        specialties = all_active_doctors.mapped('medical_specialty_id').filtered(lambda s: s).sorted(lambda s: (s.name or '').lower())

        total = Partner.search_count(domain)
        members = Partner.search(domain, order='name asc', limit=step, offset=(page - 1) * step)

        url_args = {}
        if q:
            url_args['q'] = q
        if state_id:
            url_args['state_id'] = state_id
        if city:
            url_args['city'] = city
        if specialty_id:
            url_args['specialty_id'] = specialty_id

        pager = request.website.pager(
            url='/members',
            total=total,
            page=page,
            step=step,
            url_args=url_args,
        )

        return request.render('membership_website_directory.member_directory_list', {
            'members': members,
            'pager': pager,
            'q': q or '',
            'states': states,
            'cities': cities,
            'selected_state_id': int(state_id) if state_id else 0,
            'selected_city': city or '',
            'specialties': specialties,
            'selected_specialty_id': int(specialty_id) if specialty_id else 0,
        })

    @http.route(['/members/<int:partner_id>'], type='http', auth='public', website=True, sitemap=False)
    def member_detail(self, partner_id, **kw):
        Partner = request.env['res.partner'].sudo()
        member = Partner.search(self._base_domain() + [('id', '=', partner_id)], limit=1)
        if not member:
            return request.not_found()

        return request.render('membership_website_directory.member_directory_detail', {
            'member': member
        })
