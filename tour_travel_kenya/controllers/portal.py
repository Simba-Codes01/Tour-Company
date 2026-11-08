from odoo import http, _
from odoo.addons.payment.controllers import portal as payment_portal
from odoo.addons.portal.controllers.portal import pager as portal_pager
from odoo.http import request


class TourCustomerPortal(payment_portal.PaymentPortal):
    _items_per_page = 20

    def _prepare_home_portal_values(self, counters):
        values = super()._prepare_home_portal_values(counters)
        partner = request.env.user.partner_id
        if 'booking_count' in counters:
            values['booking_count'] = request.env['tour.booking'].search_count(
                self._prepare_bookings_domain(partner))
        if 'wishlist_count' in counters:
            values['wishlist_count'] = len(partner.wishlist_tour_ids)
        return values

    def _prepare_bookings_domain(self, partner):
        return [('partner_id', '=', partner.id), ('state', '!=', 'cancel')]

    @http.route(['/my/bookings', '/my/bookings/page/<int:page>'], type='http', auth='user', website=True)
    def portal_my_bookings(self, page=1, **kwargs):
        Booking = request.env['tour.booking']
        partner = request.env.user.partner_id
        domain = self._prepare_bookings_domain(partner)
        pager_values = portal_pager(
            url='/my/bookings', total=Booking.search_count(domain),
            page=page, step=self._items_per_page)
        bookings = Booking.search(domain, order='create_date desc', limit=self._items_per_page, offset=pager_values['offset'])
        values = {
            'bookings': bookings,
            'page_name': 'booking',
            'pager': pager_values,
            'default_url': '/my/bookings',
        }
        return request.render('tour_travel_kenya.portal_my_bookings', values)

    @http.route(['/my/bookings/<int:booking_id>'], type='http', auth='public', website=True)
    def portal_booking_page(self, booking_id, access_token=None, **kwargs):
        booking_sudo = self._document_check_access('tour.booking', booking_id, access_token=access_token)
        values = {
            'booking': booking_sudo,
            'page_name': 'booking',
        }
        return request.render('tour_travel_kenya.portal_booking_page', values)

    @http.route(['/my/wishlist'], type='http', auth='user', website=True)
    def portal_my_wishlist(self, **kwargs):
        partner = request.env.user.partner_id
        values = {
            'packages': partner.wishlist_tour_ids.filtered('website_published'),
            'page_name': 'wishlist',
        }
        return request.render('tour_travel_kenya.portal_my_wishlist', values)

    @http.route(['/my/bookings/<int:booking_id>/rate'], type='jsonrpc', auth='public', website=True)
    def portal_booking_rate(self, booking_id, access_token=None, rating_value=None, feedback=None, **kwargs):
        booking_sudo = self._document_check_access('tour.booking', booking_id, access_token=access_token)
        if booking_sudo.state != 'done':
            return {'error': _('Only completed bookings can be reviewed.')}
        try:
            rating_value = int(rating_value or 0)
        except (TypeError, ValueError):
            rating_value = 0
        if not 1 <= rating_value <= 5:
            return {'error': _('Please select a star rating.')}
        feedback = (feedback or '').strip()[:3000]
        if request.env['tour.package.review'].sudo().search_count([('booking_id', '=', booking_sudo.id)], limit=1):
            return {'error': _('You have already reviewed this trip. Thank you!')}

        # Logs the rating in the booking chatter for staff.
        rating_token = booking_sudo._rating_get_access_token()
        booking_sudo.rating_apply(rating_value, token=rating_token, feedback=feedback, subtype_xmlid='mail.mt_comment')

        # The public review. It comes from a completed booking, so it is
        # verified and goes live without moderation.
        partner = booking_sudo.partner_id
        request.env['tour.package.review'].sudo().create({
            'package_id': booking_sudo.package_id.id,
            'booking_id': booking_sudo.id,
            'partner_id': partner.id or False,
            'author_name': booking_sudo.name_attendee or partner.name or _('Verified Traveler'),
            'author_email': booking_sudo.email or partner.email or False,
            'rating': rating_value,
            'comment': feedback or _('Rated %s out of 5.', rating_value),
            'state': 'published',
        })
        return {'success': True}
