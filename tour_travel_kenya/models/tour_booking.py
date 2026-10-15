import logging

from odoo import _, api, fields, models
from odoo.tools import float_is_zero

_logger = logging.getLogger(__name__)


class TourBooking(models.Model):
    _name = 'tour.booking'
    _description = 'Tour Booking'
    _inherit = ['portal.mixin', 'mail.activity.mixin', 'rating.mixin']
    _order = 'id desc'
    _mail_defaults_to_email = True

    name = fields.Char(compute='_compute_name', store=True)
    package_id = fields.Many2one('tour.package', string='Package', required=True, tracking=True, index=True)
    package_date_id = fields.Many2one(
        'tour.package.date', string='Departure Date', ondelete='restrict', tracking=True,
        domain="[('package_id', '=', package_id)]",
        help="Optional link to a fixed group departure. Inquiry bookings instead carry their "
             "own requested arrival_date and are scheduled by staff during follow-up.")
    pricing_id = fields.Many2one(
        'tour.package.pricing', string='Accommodation Tier', required=True, ondelete='restrict', tracking=True,
        domain="[('package_id', '=', package_id)]")
    company_id = fields.Many2one(related='package_id.company_id', store=True)

    partner_id = fields.Many2one('res.partner', string='Customer', tracking=True, index='btree_not_null')
    first_name = fields.Char(string='First Name')
    last_name = fields.Char(string='Last Name')
    name_attendee = fields.Char(
        string='Lead Traveler', compute='_compute_name_attendee', readonly=False, store=True)
    email = fields.Char(compute='_compute_email', readonly=False, store=True)
    phone = fields.Char(compute='_compute_phone', readonly=False, store=True)
    arrival_date = fields.Date(string='Arrival Date', tracking=True)
    adults_count = fields.Integer(string='No. of Adults', default=2, required=True)
    children_count = fields.Integer(string='No. of Children', default=0, required=True, help="Ages 4-12.")
    infants_count = fields.Integer(string='No. of Infants', default=0, required=True, help="Under 4 years.")
    rooms_count = fields.Integer(string='No. of Rooms', default=1, required=True)
    traveler_count = fields.Integer(
        string='Travelers', default=1, required=True,
        compute='_compute_traveler_count', readonly=False, store=True, precompute=True)
    travel_party = fields.Selection([
        ('couple', 'Couple'),
        ('family', 'Family'),
        ('friends', 'Friends'),
        ('solo', 'Solo'),
    ], string='Traveling As', help="Who the lead traveler is coming with, captured from the website inquiry form.")
    special_requests = fields.Text(string='Additional Notes / Message')

    active = fields.Boolean(default=True)
    state = fields.Selection([
        ('draft', 'Unconfirmed'),
        ('open', 'Confirmed'),
        ('done', 'Completed'),
        ('cancel', 'Cancelled'),
    ], default=None, required=True, tracking=True, copy=False,
        compute='_compute_booking_status', store=True, readonly=False, precompute=True)

    sale_order_id = fields.Many2one('sale.order', string='Sales Order', ondelete='cascade', copy=False)
    sale_order_line_id = fields.Many2one(
        'sale.order.line', string='Sales Order Line', ondelete='cascade', copy=False, index='btree_not_null')
    sale_status = fields.Selection([
        ('free', 'Free'),
        ('to_pay', 'To Pay'),
        ('sold', 'Sold'),
    ], copy=False, compute='_compute_booking_status', store=True, readonly=False, precompute=True)

    @api.depends('partner_id', 'package_id', 'name_attendee')
    def _compute_name(self):
        for booking in self:
            booking.name = _('%(package)s - %(customer)s', package=booking.package_id.name, customer=booking.partner_id.name or booking.name_attendee or '')

    @api.depends('first_name', 'last_name', 'partner_id')
    def _compute_name_attendee(self):
        for booking in self:
            if booking.first_name or booking.last_name:
                booking.name_attendee = ' '.join(filter(None, [booking.first_name, booking.last_name]))
            elif not booking.name_attendee and booking.partner_id:
                booking.name_attendee = booking.partner_id.name

    @api.depends('adults_count', 'children_count')
    def _compute_traveler_count(self):
        for booking in self:
            booking.traveler_count = (booking.adults_count or 0) + (booking.children_count or 0) or 1

    @api.depends('partner_id')
    def _compute_email(self):
        for booking in self:
            if not booking.email and booking.partner_id:
                booking.email = booking.partner_id.email

    @api.depends('partner_id')
    def _compute_phone(self):
        for booking in self:
            if not booking.phone and booking.partner_id:
                booking.phone = booking.partner_id.phone

    @api.depends('sale_order_id.state', 'sale_order_id.amount_total', 'sale_order_id.currency_id')
    def _compute_booking_status(self):
        for sale_order, bookings in self.filtered('sale_order_id').grouped('sale_order_id').items():
            cancelled_so_bookings = bookings.filtered(lambda b: b.sale_order_id.state == 'cancel')
            cancelled_so_bookings.state = 'cancel'
            cancelled = cancelled_so_bookings | bookings.filtered(lambda b: b.state == 'cancel')
            if float_is_zero(sale_order.amount_total, precision_rounding=sale_order.currency_id.rounding):
                bookings.sale_status = 'free'
                bookings.filtered(lambda b: not b.state or b.state == 'draft').state = 'open'
            else:
                sold = bookings.filtered(lambda b: b.sale_order_id.state == 'sale') - cancelled
                sold.sale_status = 'sold'
                (bookings - sold).sale_status = 'to_pay'
                sold.filtered(lambda b: not b.state or b.state in ('draft', 'cancel')).state = 'open'
                (bookings - sold - cancelled).state = 'draft'

        for booking in self:
            if not booking.sale_status:
                booking.sale_status = 'free'
            if not booking.state:
                booking.state = 'draft'

    @api.depends('sale_order_id.state', 'sale_order_id.amount_total', 'sale_order_id.currency_id')
    def _compute_access_url(self):
        for booking in self:
            booking.access_url = '/my/bookings/%s' % booking.id

    @api.constrains('active', 'state', 'package_date_id', 'traveler_count')
    def _check_seats_availability(self):
        # seats_reserved/seats_used on tour.package.date are computed from the current
        # DB state, which already includes this write; verifying with extra_travelers=0
        # simply confirms that state doesn't oversell the departure date's capacity.
        to_check = self.filtered(lambda booking: booking.state in ('open', 'done') and booking.active)
        for package_date in to_check.package_date_id:
            package_date._verify_seats_availability(extra_travelers=0)

    def _rating_get_parent_field_name(self):
        return 'package_id'

    @api.onchange('package_id')
    def _onchange_package_id(self):
        if self.package_date_id and self.package_date_id.package_id != self.package_id:
            self.package_date_id = False
        if self.pricing_id and self.pricing_id.package_id != self.package_id:
            self.pricing_id = False

    def action_confirm(self):
        self.write({'state': 'open'})

    def action_done(self):
        self.write({'state': 'done'})

    def action_cancel(self):
        self.write({'state': 'cancel'})

    def action_draft(self):
        self.write({'state': 'draft'})

    def action_view_sale_order(self):
        self.ensure_one()
        action = self.env['ir.actions.actions']._for_xml_id('sale.action_orders')
        action['views'] = [(False, 'form')]
        action['res_id'] = self.sale_order_id.id
        return action

    def _send_confirmation_email(self):
        template = self.env.ref('tour_travel_kenya.email_template_booking_confirmation', raise_if_not_found=False)
        if not template:
            return
        for booking in self:
            if not booking.email:
                continue
            try:
                template.sudo().send_mail(booking.id, force_send=True)
            except Exception:
                _logger.warning('Failed to send booking confirmation email for booking %s', booking.id, exc_info=True)
