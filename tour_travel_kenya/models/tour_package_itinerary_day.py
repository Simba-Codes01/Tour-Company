from odoo import fields, models
from odoo.tools.translate import html_translate


class TourPackageItineraryDay(models.Model):
    _name = 'tour.package.itinerary.day'
    _description = 'Tour Package Itinerary Day'
    _order = 'sequence, id'

    package_id = fields.Many2one('tour.package', required=True, ondelete='cascade', index=True)
    sequence = fields.Integer(default=10)
    day_label = fields.Char(
        required=True, help="Short day marker shown on the tab/badge, e.g. 'Day 1' or 'Day 3-4'.")
    title = fields.Char(required=True, translate=True)
    description = fields.Html(translate=html_translate, sanitize_attributes=False)
    note = fields.Char(
        translate=True,
        help="Optional short callout shown under the description, e.g. an alternative "
             "arrangement for guests who'd rather skip an activity.")
    image_1920 = fields.Image('Day Photo', help="Optional hero photo shown at the top of this day's card.")
    destination = fields.Char(translate=True)
    accommodation = fields.Char(help="Overnight lodge/camp for this day. Leave empty on a departure day.")
    accommodation_rating = fields.Integer(
        string='Accommodation Rating', help="Star rating out of 5, shown next to the accommodation name.")
    accommodation_tagline = fields.Char(
        string='Accommodation Tagline', help="Short descriptor, e.g. 'Bush Camp - Best Value'.")
    accommodation_image_ids = fields.One2many(
        'tour.package.itinerary.accommodation.image', 'day_id', string='Accommodation Gallery')
    meals = fields.Char(
        default='B, L, D', help="Meals included this day, e.g. 'B, L, D' for breakfast, lunch and dinner.")
    wildlife = fields.Char(
        string='Key Sightings',
        help="Comma-separated key wildlife species to look out for this day, e.g. "
             "'African Elephant, Lion, Plains Zebra'. Shown as tags on the itinerary-at-a-glance table.")
    travel_mode = fields.Selection([
        ('drive', 'Drive'),
        ('fly', 'Fly'),
        ('boat', 'Boat'),
        ('walk', 'Walk'),
    ], default='drive', required=True, help="How guests travel to reach this day's destination.")
    activities = fields.Char(
        help="Comma-separated activities for this day, e.g. 'Game Drive, Sundowner, Bush Breakfast'.")
    extra_ids = fields.One2many(
        'tour.package.itinerary.extra', 'day_id', string='Optional Extras',
        help="Optional paid add-ons guests can book locally for this day, with per-person "
             "(and optionally per-child) pricing, e.g. 'Hot Air Balloon Safari - $450pp'.")
    icon = fields.Selection([
        ('plane-departure', 'Departure/Arrival (plane)'),
        ('road', 'Road Transfer'),
        ('binoculars', 'Game Drive'),
        ('sun-o', 'Sunrise/Sunset Drive'),
        ('paw', 'Wildlife Tracking'),
        ('tree', 'Sanctuary/Reserve'),
        ('globe', 'Landmark/Equator'),
        ('users', 'Cultural Visit'),
        ('bed', 'Check-in/Rest'),
        ('flag-checkered', 'Final Day'),
    ], default='binoculars', required=True)

    def get_wildlife_list(self):
        self.ensure_one()
        return [name.strip() for name in (self.wildlife or '').split(',') if name.strip()]

    def get_activities_list(self):
        self.ensure_one()
        return [name.strip() for name in (self.activities or '').split(',') if name.strip()]
