from odoo import fields, models


class TourPackageItineraryAccommodationImage(models.Model):
    _name = 'tour.package.itinerary.accommodation.image'
    _description = 'Itinerary Day Accommodation Gallery Image'
    _order = 'sequence, id'

    name = fields.Char('Caption')
    sequence = fields.Integer(default=10)
    day_id = fields.Many2one(
        'tour.package.itinerary.day', required=True, ondelete='cascade', index=True)
    image_1920 = fields.Image('Image', required=True)
