import json
import re
from datetime import date

from markupsafe import Markup

from odoo import http, _
from odoo.exceptions import ValidationError
from odoo.fields import Domain
from odoo.tools import html2plaintext
from odoo.tools.json import scriptsafe as json_scriptsafe
from odoo.http import request
from odoo.addons.website.models.ir_http import sitemap_qs2dom


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


def sitemap_tour_packages(env, rule, qs):
    # Same records as the route's model converter domain, plus a lastmod - the
    # default converter sitemap only emits <loc>, so Google had no change dates
    Package = env['tour.package'].sudo()
    domain = sitemap_qs2dom(qs, '/tours', Package._rec_name) & Domain('website_published', '=', True)
    for package in Package.search(domain):
        loc = package.website_url
        if not qs or qs.lower() in loc:
            dates = [package.write_date] + package.itinerary_day_ids.mapped('write_date')
            yield {'loc': loc, 'lastmod': max(d for d in dates if d).date()}


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

    @http.route(['/llms.txt'], type='http', auth='public', website=True, sitemap=False, readonly=True)
    def llms_txt(self, **kwargs):
        """Plain-markdown site summary for AI answer engines (llmstxt.org), built
        from the published packages so it never drifts from the live catalogue."""
        website = request.website
        base_url = website.get_base_url()
        company = website.company_id.sudo()
        packages = request.env['tour.package'].sudo().search(
            [('website_published', '=', True)], order='duration_days, name')
        lines = [
            '# %s' % website.name,
            '',
            '> %s is a Nairobi-based Kenya safari operator (not affiliated with the Serian camps in '
            'the Masai Mara). Every itinerary is planned and run '
            'in-house with a private guide and 4x4 Land Cruiser for each group, and booked directly '
            'with the operator - no agent markups. Prices are per person, from the lowest '
            'accommodation tier.' % website.name,
            '',
        ]
        if company.phone:
            lines.append('- Phone / WhatsApp: %s' % company.phone)
        if company.email:
            lines.append('- Email: %s' % company.email)
        lines += ['- Based in: Nairobi, Kenya', '', '## Tour packages', '']
        for package in packages:
            summary = self._get_package_meta_description(package, limit=200)
            price = package.get_lowest_price_display() if package.pricing_ids else ''
            lines.append('- [%s](%s%s): %s day(s)%s. %s' % (
                package.name, base_url, package.website_url, package.duration_days,
                ', from %s per person' % price if price else '', summary))
        lines += [
            '',
            '## Planning',
            '',
            '- [All tour packages](%s/tours)' % base_url,
            '- [Kenya destinations map](%s/destinations)' % base_url,
            '- [Travel info & FAQs](%s/faq): visas, vaccinations, packing, money, tipping, when to go' % base_url,
            '- [Contact & custom quotes](%s/contactus)' % base_url,
            '',
            '## Policies',
            '',
            '- [Terms & conditions](%s/terms)' % base_url,
            '- [Cancellation policy](%s/cancellation-policy)' % base_url,
            '- [Privacy policy](%s/privacy-policy)' % base_url,
            '',
        ]
        return request.make_response('\n'.join(lines), headers=[('Content-Type', 'text/plain; charset=utf-8')])

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

    def _get_package_meta_description(self, package_sudo, limit=160):
        text = ' '.join(html2plaintext(package_sudo.description or '').split())
        if not text:
            text = '%s - %s-day tour of %s with Seriani Tours & Travel.' % (
                package_sudo.name, package_sudo.duration_days, package_sudo.destination or 'Kenya')
        if len(text) > limit:
            text = text[:limit - 1].rsplit(' ', 1)[0].rstrip(' ,;:-') + '\u2026'
        return text

    def _get_package_structured_data(self, package_sudo, base_url):
        page_url = base_url + package_sudo.website_url
        organization = {'@id': base_url + '/#organization'}
        images = [base_url + '/web/image/tour.package/%s/image_1920' % package_sudo.id] if package_sudo.image_1920 else []
        images += [base_url + '/web/image/tour.package.image/%s/image_1920' % img.id
                   for img in package_sudo.tour_package_image_ids[:4]]
        trip = {
            '@type': 'TouristTrip',
            '@id': page_url + '#trip',
            'name': package_sudo.name,
            'url': page_url,
            'description': ' '.join(html2plaintext(package_sudo.description or '').split())
                           or self._get_package_meta_description(package_sudo),
            'provider': organization,
        }
        if images:
            trip['image'] = images
        if package_sudo.itinerary_day_ids:
            trip['itinerary'] = {
                '@type': 'ItemList',
                'numberOfItems': len(package_sudo.itinerary_day_ids),
                'itemListElement': [{
                    '@type': 'ListItem',
                    'position': position,
                    'item': {
                        '@type': 'TouristAttraction',
                        'name': '%s: %s' % (day.day_label, day.title),
                        'description': ' '.join(html2plaintext(day.description or '').split())[:300] or day.destination or day.title,
                    },
                } for position, day in enumerate(package_sudo.itinerary_day_ids, start=1)],
            }
        prices = package_sudo.pricing_ids.mapped('price')
        if prices:
            trip['offers'] = {
                '@type': 'Offer',
                'price': '%.2f' % min(prices),
                'priceCurrency': package_sudo.currency_id.name or 'USD',
                'url': page_url,
                'availability': 'https://schema.org/InStock',
                'offeredBy': organization,
            }
        if package_sudo.rating_count:
            trip['aggregateRating'] = {
                '@type': 'AggregateRating',
                'ratingValue': '%.1f' % package_sudo.rating_avg,
                'reviewCount': package_sudo.rating_count,
            }
        breadcrumb = {
            '@type': 'BreadcrumbList',
            'itemListElement': [
                {'@type': 'ListItem', 'position': 1, 'name': 'Tour Packages', 'item': base_url + '/tours'},
                {'@type': 'ListItem', 'position': 2, 'name': package_sudo.name, 'item': page_url},
            ],
        }
        return {'@context': 'https://schema.org', '@graph': [trip, breadcrumb]}

    def _get_package_page_values(self, package_sudo):
        base_url = request.website.get_base_url()
        structured_data = self._get_package_structured_data(package_sudo, base_url)
        return {
            # Drives website.layout's OpenGraph/Twitter tags, see tour.package._default_website_meta
            'main_object': package_sudo,
            # <title> and <meta name="description"> for website.layout - without these
            # every package page was titled "Tour Package" with no description
            'additional_title': package_sudo.name,
            'website_meta_description': self._get_package_meta_description(package_sudo),
            'canonical_url': base_url + package_sudo.website_url,
            'structured_data_json': Markup(json_scriptsafe.dumps(structured_data)),
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

    # The converter domain only filters the sitemap (URL matching ignores it) -
    # archived/unpublished packages are kept out of it; the page itself 404s below.
    @http.route(['/tours/<model("tour.package", "[(\'website_published\', \'=\', True)]"):package>'], type='http', auth='public', website=True, sitemap=sitemap_tour_packages, readonly=True)
    def tour_package_page(self, package, **kwargs):
        package_sudo = package.sudo()
        if not (package_sudo.active and package_sudo.website_published) and not request.env.user.has_group('tour_travel_kenya.group_tour_user'):
            raise request.not_found()
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
        if not (package_sudo.active and package_sudo.website_published) and not request.env.user.has_group('tour_travel_kenya.group_tour_user'):
            raise request.not_found()
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
