import json
import re
from datetime import date

from markupsafe import Markup

from odoo import http, _
from odoo.exceptions import ValidationError
from odoo.http import request


class WebsiteTourController(http.Controller):

    def _get_search_domain(self, category=None, search=None):
        domain = [('website_published', '=', True)]
        if category:
            domain.append(('category_id', '=', int(category)))
        if search:
            domain.append(('name', 'ilike', search))
        return domain

    @http.route(['/tours', '/tours/page/<int:page>'], type='http', auth='public', website=True, sitemap=True, readonly=True)
    def tours(self, page=1, category=None, search=None, **kwargs):
        Package = request.env['tour.package'].sudo()
        domain = self._get_search_domain(category, search)
        step = 12
        total = Package.search_count(domain)
        pager = request.website.pager(url='/tours', total=total, page=page, step=step, scope=5,
                                       url_args={'category': category, 'search': search})
        packages = Package.search(domain, limit=step, offset=pager['offset'], order='sequence, name')
        all_published = Package.search([('website_published', '=', True)])
        prices = all_published.pricing_ids.mapped('price')
        lowest_price = min(prices) if prices else 0
        currency = all_published[0].currency_id if prices else False
        values = {
            'packages': packages,
            'pager': pager,
            'categories': request.env['tour.package.category'].sudo().search([]),
            'current_category': int(category) if category else None,
            'search': search or '',
            'total_packages': len(all_published),
            'total_reviews': sum(all_published.mapped('rating_count')),
            'lowest_price': int(lowest_price),
            'lowest_price_display': all_published[0]._format_price(lowest_price) if prices else False,
            'price_prefix': currency.symbol if currency and currency.position == 'before' else '',
            'price_suffix': '' if not currency or currency.position == 'before' else (' ' + currency.symbol),
            'wishlisted_ids': (
                request.env.user.partner_id.wishlist_tour_ids.ids
                if not request.env.user._is_public() else []
            ),
        }
        return request.render('tour_travel_kenya.tours_index', values)

    @http.route(['/cancellation-policy'], type='http', auth='public', website=True, sitemap=True, readonly=True)
    def cancellation_policy(self, **kwargs):
        return request.render('tour_travel_kenya.cancellation_policy_page', {})

    @http.route(['/privacy-policy'], type='http', auth='public', website=True, sitemap=True, readonly=True)
    def privacy_policy(self, **kwargs):
        return request.render('tour_travel_kenya.privacy_policy_page', {})

    @http.route(['/faq'], type='http', auth='public', website=True, sitemap=True, readonly=True)
    def faq(self, **kwargs):
        return request.render('tour_travel_kenya.faq_page', {})

    @http.route(['/destinations'], type='http', auth='public', website=True, sitemap=True, readonly=True)
    def destinations(self, **kwargs):
        packages = request.env['tour.package'].sudo().search([
            ('website_published', '=', True),
        ], order='sequence, name')

        # Our packages are multi-stop circuits (route waypoints), not single-point
        # destinations, so the map is built from every package's waypoints - falling
        # back to the package's own latitude/longitude for any single-stop package -
        # deduplicated by location so a place visited by several packages (e.g.
        # Nairobi) gets one pin listing every package that stops there.
        locations = {}
        for package in packages:
            stops = package.waypoint_ids or (
                [package] if package.latitude and package.longitude else []
            )
            for stop in stops:
                if not stop.latitude or not stop.longitude:
                    continue
                key = (round(stop.latitude, 2), round(stop.longitude, 2))
                clean_name = re.sub(r'^Day\s+[\d]+(-[\d]+)?:\s*', '', stop.name or package.destination or package.name)
                location = locations.setdefault(key, {
                    'name': clean_name,
                    'lat': stop.latitude,
                    'lng': stop.longitude,
                    'packages': [],
                })
                if not any(pkg['url'] == package.website_url for pkg in location['packages']):
                    location['packages'].append({'name': package.name, 'url': package.website_url})

        return request.render('tour_travel_kenya.tour_destinations', {
            'packages': packages.filtered('destination_summary'),
            'map_points_json': json.dumps(list(locations.values())),
        })

    def _get_route_points_json(self, package_sudo):
        points = [{
            'name': wp.name,
            'lat': wp.latitude,
            'lng': wp.longitude,
        } for wp in package_sudo.waypoint_ids]
        return json.dumps(points)

    def _get_package_page_values(self, package_sudo):
        base_url = request.website.get_base_url()
        og_image_url = base_url + '/web/image/tour.package/%s/image_1920' % package_sudo.id if package_sudo.image_1920 else False
        prices = package_sudo.pricing_ids.mapped('price')
        structured_data = {
            '@context': 'https://schema.org',
            '@type': 'TouristTrip',
            'name': package_sudo.name,
            'description': package_sudo.destination or package_sudo.name,
            'touristType': dict(package_sudo._fields['difficulty_level'].selection).get(package_sudo.difficulty_level),
        }
        if og_image_url:
            structured_data['image'] = og_image_url
        if prices:
            structured_data['offers'] = {
                '@type': 'Offer',
                'price': '%.2f' % min(prices),
                'priceCurrency': package_sudo.currency_id.name or 'USD',
                'url': base_url + package_sudo.website_url,
            }
        if package_sudo.rating_count:
            structured_data['aggregateRating'] = {
                '@type': 'AggregateRating',
                'ratingValue': '%.1f' % package_sudo.rating_avg,
                'reviewCount': package_sudo.rating_count,
            }
        return {
            'og_image_url': og_image_url,
            'canonical_url': base_url + package_sudo.website_url,
            'structured_data_json': Markup(json.dumps(structured_data)),
            'upcoming_dates': package_sudo.date_ids.filtered(
                lambda d: d.state == 'open' and d.date_start and d.date_start >= date.today()
            )[:6],
            'related_packages': request.env['tour.package'].sudo().search([
                ('website_published', '=', True),
                ('category_id', '=', package_sudo.category_id.id),
                ('id', '!=', package_sudo.id),
            ], limit=3),
            'is_wishlisted': (
                not request.env.user._is_public()
                and package_sudo in request.env.user.partner_id.wishlist_tour_ids
            ),
        }

    @http.route(['/tours/<model("tour.package"):package>'], type='http', auth='public', website=True, sitemap=True, readonly=True)
    def tour_package_page(self, package, **kwargs):
        package_sudo = package.sudo()
        if not package_sudo.website_published and not request.env.user.has_group('tour_travel_kenya.group_tour_user'):
            request.not_found()
        reviews = request.env['rating.rating'].sudo().search([
            ('parent_res_model', '=', 'tour.package'),
            ('parent_res_id', '=', package_sudo.id),
            ('consumed', '=', True),
            ('rating', '>', 0),
        ], order='write_date desc', limit=10)
        values = {
            'package': package_sudo,
            'pricings': package_sudo.pricing_ids,
            'reviews': reviews,
            'route_points_json': self._get_route_points_json(package_sudo),
        }
        values.update(self._get_package_page_values(package_sudo))
        return request.render('tour_travel_kenya.tour_package_detail', values)

    @http.route(['/tours/<model("tour.package"):package>/book'], type='http', auth='public', methods=['POST'], website=True)
    def tour_booking_confirm(self, package, **post):
        package_sudo = package.sudo()
        try:
            first_name = (post.get('first_name') or '').strip()
            last_name = (post.get('last_name') or '').strip()
            email = (post.get('email') or '').strip()
            phone = (post.get('phone') or '').strip()
            arrival_date = post.get('arrival_date')
            adults_count = max(int(post.get('adults_count') or 1), 1)
            children_count = max(int(post.get('children_count') or 0), 0)
            rooms_count = max(int(post.get('rooms_count') or 1), 1)
            pricing = request.env['tour.package.pricing'].sudo().browse(int(post.get('pricing_id', 0)))

            if not all([first_name, last_name, email, phone, arrival_date]) or '@' not in email:
                raise ValidationError(_('Please fill in all required fields with a valid email address.'))
            if pricing.package_id != package_sudo:
                raise ValidationError(_('Invalid accommodation option for this package.'))

            partner = request.env['res.partner'].sudo().search([('email', '=', email)], limit=1)
            if not partner:
                partner = request.env['res.partner'].sudo().create({
                    'name': f'{first_name} {last_name}',
                    'email': email,
                    'phone': phone,
                })

            booking = request.env['tour.booking'].sudo().create({
                'package_id': package_sudo.id,
                'pricing_id': pricing.id,
                'partner_id': partner.id,
                'first_name': first_name,
                'last_name': last_name,
                'email': email,
                'phone': phone,
                'arrival_date': arrival_date,
                'adults_count': adults_count,
                'children_count': children_count,
                'rooms_count': rooms_count,
                'special_requests': post.get('special_requests'),
            })
            booking._send_confirmation_email()
        except (ValidationError, ValueError) as exc:
            values = {
                'package': package_sudo,
                'pricings': package_sudo.pricing_ids,
                'booking_error': str(exc),
                'route_points_json': self._get_route_points_json(package_sudo),
            }
            values.update(self._get_package_page_values(package_sudo))
            return request.render('tour_travel_kenya.tour_package_detail', values)

        return request.redirect('/tours/%s/booked' % request.env['ir.http']._slug(package_sudo))

    @http.route(['/tours/<model("tour.package"):package>/booked'], type='http', auth='public', website=True, sitemap=False)
    def tour_booking_success(self, package, **kwargs):
        return request.render('tour_travel_kenya.tour_booking_complete', {'package': package.sudo()})

    @http.route(['/tours/<model("tour.package"):package>/itinerary.pdf'], type='http', auth='public', website=True, sitemap=False)
    def tour_package_itinerary_pdf(self, package, **kwargs):
        package_sudo = package.sudo()
        if not package_sudo.website_published and not request.env.user.has_group('tour_travel_kenya.group_tour_user'):
            request.not_found()
        pdf, dummy_report_type = request.env['ir.actions.report'].sudo()._render_qweb_pdf(
            'tour_travel_kenya.report_tour_itinerary_document', [package_sudo.id])
        headers = [
            ('Content-Type', 'application/pdf'),
            ('Content-Length', len(pdf)),
            ('Content-Disposition', 'inline; filename="%s-itinerary.pdf"' % request.env['ir.http']._slug(package_sudo)),
        ]
        return request.make_response(pdf, headers=headers)

    @http.route(['/tours/<model("tour.package"):package>/wishlist/toggle'], type='jsonrpc', auth='user', website=True)
    def tour_wishlist_toggle(self, package, **kwargs):
        partner = request.env.user.partner_id
        package_sudo = package.sudo()
        if package_sudo in partner.wishlist_tour_ids:
            partner.sudo().write({'wishlist_tour_ids': [(3, package_sudo.id)]})
            wishlisted = False
        else:
            partner.sudo().write({'wishlist_tour_ids': [(4, package_sudo.id)]})
            wishlisted = True
        return {'wishlisted': wishlisted}
