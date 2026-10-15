import json
import re
from datetime import date

from markupsafe import Markup

from odoo import http, _
from odoo.exceptions import ValidationError
from odoo.http import request


SAFARI_MONTHS = [
    {'num': 1, 'abbr': 'Jan', 'name': 'January', 'season': 'green', 'season_label': 'Green Season',
     'trips': 4, 'weather': 'Warm & mostly dry', 'crowds': 'Medium crowds', 'highlight': 'Calving season',
     'desc': "One of the best months for predator action as wildebeest and zebra calve on the southern "
             "plains of the Mara and Amboseli. Warm, mostly dry weather with fewer crowds than peak season.",
     'parks': "Masai Mara, Amboseli, Lake Nakuru"},
    {'num': 2, 'abbr': 'Feb', 'name': 'February', 'season': 'green', 'season_label': 'Green Season',
     'trips': 4, 'weather': 'Hot & dry', 'crowds': 'Medium crowds', 'highlight': 'Great cat sightings',
     'desc': "Hot, dry conditions concentrate wildlife around water sources, making for excellent predator "
             "sightings across the Mara and Amboseli before the long rains begin.",
     'parks': "Masai Mara, Amboseli"},
    {'num': 3, 'abbr': 'Mar', 'name': 'March', 'season': 'rainy', 'season_label': 'Low / Rainy Season',
     'trips': 3, 'weather': 'Rain showers begin', 'crowds': 'Low crowds', 'highlight': 'Lowest rates',
     'desc': "The long rains begin, bringing lush green scenery and the lowest crowds and rates of the "
             "year. Roads can be muddy in remote areas, so travel is best with a 4x4.",
     'parks': "Lake Nakuru, Samburu"},
    {'num': 4, 'abbr': 'Apr', 'name': 'April', 'season': 'rainy', 'season_label': 'Low / Rainy Season',
     'trips': 3, 'weather': 'Heavy rains', 'crowds': 'Very low crowds', 'highlight': 'Best value',
     'desc': "The heart of the long rains. Dramatic skies, newborn wildlife, and by far the quietest parks "
             "and lowest accommodation rates of the year - some remote camps close for the month.",
     'parks': "Lake Nakuru, Ol Pejeta"},
    {'num': 5, 'abbr': 'May', 'name': 'May', 'season': 'rainy', 'season_label': 'Low / Rainy Season',
     'trips': 3, 'weather': 'Rains easing', 'crowds': 'Low crowds', 'highlight': 'Quiet parks',
     'desc': "Rains begin easing toward the end of the month, leaving Kenya at its greenest. Ideal for "
             "budget-conscious travelers who don't mind the occasional shower.",
     'parks': "Aberdare, Lake Nakuru"},
    {'num': 6, 'abbr': 'Jun', 'name': 'June', 'season': 'peak', 'season_label': 'Dry / Peak Season',
     'trips': 4, 'weather': 'Cool & dry', 'crowds': 'Medium crowds', 'highlight': 'Migration begins',
     'desc': "The dry season sets in and the wildebeest migration starts moving north toward the Mara. "
             "Cool mornings and clear game viewing across all parks.",
     'parks': "Masai Mara, Samburu"},
    {'num': 7, 'abbr': 'Jul', 'name': 'July', 'season': 'peak', 'season_label': 'Dry / Peak Season',
     'trips': 4, 'weather': 'Cool & dry', 'crowds': 'High crowds', 'highlight': 'Migration in the Mara',
     'desc': "The Great Migration typically arrives in the Masai Mara, with dramatic river crossings "
             "possible from July onward. Book well ahead - this is peak season.",
     'parks': "Masai Mara, Samburu"},
    {'num': 8, 'abbr': 'Aug', 'name': 'August', 'season': 'peak', 'season_label': 'Dry / Peak Season',
     'trips': 4, 'weather': 'Cool & dry', 'crowds': 'High crowds', 'highlight': 'River crossings',
     'desc': "Peak Migration season continues in the Mara with the best chance of dramatic Mara River "
             "crossings, alongside superb game viewing across every park on our circuits.",
     'parks': "Masai Mara, Amboseli, Samburu"},
    {'num': 9, 'abbr': 'Sep', 'name': 'September', 'season': 'peak', 'season_label': 'Dry / Peak Season',
     'trips': 4, 'weather': 'Cool & dry', 'crowds': 'High crowds', 'highlight': 'Migration in the Mara',
     'desc': "The migration herds remain in the Mara for much of September, with excellent predator "
             "action as resident lion and cheetah follow the herds.",
     'parks': "Masai Mara, Lake Nakuru"},
    {'num': 10, 'abbr': 'Oct', 'name': 'October', 'season': 'peak', 'season_label': 'Dry / Peak Season',
     'trips': 4, 'weather': 'Warm & dry', 'crowds': 'Medium-high crowds', 'highlight': 'Migration departs',
     'desc': "The migration begins moving back south through the month, while dry conditions keep game "
             "viewing excellent across Amboseli and Lake Nakuru.",
     'parks': "Masai Mara, Amboseli"},
    {'num': 11, 'abbr': 'Nov', 'name': 'November', 'season': 'green', 'season_label': 'Green Season',
     'trips': 3, 'weather': 'Short rains', 'crowds': 'Low crowds', 'highlight': 'Fewer crowds',
     'desc': "The short rains freshen up the landscape after the dry season, bringing back the birdlife "
             "and greenery. Crowds and rates both drop from the October peak.",
     'parks': "Lake Nakuru, Aberdare"},
    {'num': 12, 'abbr': 'Dec', 'name': 'December', 'season': 'green', 'season_label': 'Green Season',
     'trips': 3, 'weather': 'Warm, brief showers', 'crowds': 'Medium crowds', 'highlight': 'Festive season',
     'desc': "Short rains ease off and warm, mostly sunny days return in time for the festive season - a "
             "popular window for family safaris over the holidays.",
     'parks': "Masai Mara, Amboseli, Samburu"},
]


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
            'current_month': date.today().month,
            'safari_months': SAFARI_MONTHS,
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
            'wishlisted_ids': (
                request.env.user.partner_id.wishlist_tour_ids.ids
                if not request.env.user._is_public() else []
            ),
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
            full_name = (post.get('full_name') or '').strip()
            name_parts = full_name.split(None, 1)
            first_name = name_parts[0] if name_parts else ''
            last_name = name_parts[1] if len(name_parts) > 1 else ''
            email = (post.get('email') or '').strip()
            phone = ' '.join(filter(None, [
                (post.get('phone_code') or '').strip(),
                (post.get('phone_number') or '').strip(),
            ]))
            arrival_date = post.get('arrival_date') or False
            adults_count = max(int(post.get('adults_count') or 1), 1)
            children_count = max(int(post.get('children_count') or 0), 0)
            infants_count = max(int(post.get('infants_count') or 0), 0)
            rooms_count = max(int(post.get('rooms_count') or 1), 1)
            travel_party = post.get('travel_party') or False
            pricing = request.env['tour.package.pricing'].sudo().browse(int(post.get('pricing_id', 0)))

            if not all([full_name, email, (post.get('phone_number') or '').strip()]) or '@' not in email:
                raise ValidationError(_('Please fill in your name, email and phone number.'))
            if pricing.package_id != package_sudo:
                raise ValidationError(_('Invalid accommodation option for this package.'))

            partner = request.env['res.partner'].sudo().search([('email', '=', email)], limit=1)
            if not partner:
                partner = request.env['res.partner'].sudo().create({
                    'name': full_name,
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
                'infants_count': infants_count,
                'rooms_count': rooms_count,
                'travel_party': travel_party,
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
