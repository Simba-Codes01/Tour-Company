from odoo import fields, models


class TourPackageImage(models.Model):
    _name = 'tour.package.image'
    _description = 'Tour Package Gallery Image'
    _order = 'sequence, id'

    name = fields.Char('Caption')
    sequence = fields.Integer(default=10)
    package_id = fields.Many2one('tour.package', required=True, ondelete='cascade', index=True)
    image_1920 = fields.Image('Image', required=True)
