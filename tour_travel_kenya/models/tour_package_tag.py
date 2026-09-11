from odoo import fields, models


class TourPackageTag(models.Model):
    _name = 'tour.package.tag'
    _description = 'Tour Package Tag'
    _order = 'name'

    name = fields.Char(required=True, translate=True)
    color = fields.Integer('Color Index')

    _name_uniq = models.Constraint(
        'unique (name)',
        'A tag with the same name already exists.',
    )
