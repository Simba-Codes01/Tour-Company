from odoo import _, api, fields, models
from odoo.tools.translate import html_translate


class TourPackage(models.Model):
    _name = 'tour.package'
    _description = 'Tour Package'
    _inherit = ['website.published.mixin', 'mail.thread', 'mail.activity.mixin', 'rating.parent.mixin']
    _order = 'sequence, name'

    def _default_country_id(self):
        return self.env.ref('base.ke', raise_if_not_found=False)

    name = fields.Char(required=True, translate=True, tracking=True)
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    category_id = fields.Many2one('tour.package.category', string='Category', required=True, tracking=True)
    tag_ids = fields.Many2many('tour.package.tag', string='Tags')
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)
    currency_id = fields.Many2one(related='company_id.currency_id')
    user_id = fields.Many2one('res.users', string='Responsible', default=lambda self: self.env.user, tracking=True)

    description = fields.Html(string='Teaser', translate=html_translate, sanitize_attributes=False)
    itinerary = fields.Html(string='Itinerary', translate=html_translate, sanitize_attributes=False)
    included_services = fields.Html(string="What's Included", translate=html_translate, sanitize_attributes=False)
    excluded_services = fields.Html(string="What's Excluded", translate=html_translate, sanitize_attributes=False)

    duration_days = fields.Integer(string='Duration (days)', required=True, default=1)
    destination = fields.Char(string='Destination', tracking=True)
    destination_summary = fields.Html(string='Destination Overview', translate=html_translate, sanitize_attributes=False)
    country_id = fields.Many2one('res.country', string='Country', default=_default_country_id)
    latitude = fields.Float(string='Latitude', digits=(10, 6))
    longitude = fields.Float(string='Longitude', digits=(10, 6))
    best_season = fields.Char(string='Best Season')
    difficulty_level = fields.Selection([
        ('easy', 'Easy'),
        ('moderate', 'Moderate'),
        ('challenging', 'Challenging'),
    ], default='moderate', required=True)

    image_1920 = fields.Image('Cover Image')
    tour_package_image_ids = fields.One2many('tour.package.image', 'package_id', string='Gallery')
    waypoint_ids = fields.One2many(
        'tour.package.waypoint', 'package_id', string='Route Waypoints',
        help="Ordered stops for a multi-stop package's route map. Leave empty for a "
             "single-destination package with no route to show.")

    seats_max = fields.Integer(
        string='Default Max Travelers per Departure', default=12,
        help="Default capacity applied to new departure dates for this package. "
             "Can be overridden per departure date.")
    seats_limited = fields.Boolean(string='Limit Travelers', default=True)

    pricing_ids = fields.One2many('tour.package.pricing', 'package_id', string='Pricing Tiers')
    month_rate_ids = fields.One2many(
        'tour.package.month.rate', 'package_id', string='Seasonal Rates',
        help="Indicative per-person-sharing rate by month, shown as a reference table on the "
             "public page. Separate from the pricing tiers actually charged at booking.")
    date_ids = fields.One2many('tour.package.date', 'package_id', string='Departure Dates')
    booking_ids = fields.One2many('tour.booking', 'package_id', string='Bookings')
    booking_count = fields.Integer(compute='_compute_booking_count')

    def _compute_booking_count(self):
        counts = dict(self.env['tour.booking']._read_group(
            domain=[('package_id', 'in', self.ids), ('state', '!=', 'cancel')],
            groupby=['package_id'],
            aggregates=['__count'],
        ))
        for package in self:
            package.booking_count = counts.get(package, 0)

    @api.depends_context('lang')
    def _compute_website_url(self):
        super()._compute_website_url()
        for package in self:
            package.website_url = '/tours/%s' % self.env['ir.http']._slug(package)

    def action_view_bookings(self):
        self.ensure_one()
        action = self.env['ir.actions.actions']._for_xml_id('tour_travel_kenya.action_tour_booking')
        action['domain'] = [('package_id', '=', self.id)]
        action['context'] = {'default_package_id': self.id}
        return action

    def action_view_departure_dates(self):
        self.ensure_one()
        action = self.env['ir.actions.actions']._for_xml_id('tour_travel_kenya.action_tour_package_date')
        action['domain'] = [('package_id', '=', self.id)]
        action['context'] = {'default_package_id': self.id}
        return action

    def _format_price(self, amount):
        self.ensure_one()
        currency = self.currency_id
        amount_str = '%.0f' % amount
        if currency.position == 'before':
            return '%s%s' % (currency.symbol, amount_str)
        return '%s %s' % (amount_str, currency.symbol)

    def get_lowest_price_display(self):
        self.ensure_one()
        prices = self.pricing_ids.mapped('price')
        return self._format_price(min(prices) if prices else 0)
