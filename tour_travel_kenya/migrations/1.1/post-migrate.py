"""Copy existing booking ratings (rating.rating) into tour.package.review.

From 1.1 on, published tour.package.review records drive the package rating
stats, so ratings collected from the portal before then are carried over as
published, verified reviews.
"""
from odoo import SUPERUSER_ID, api


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    Review = env['tour.package.review']
    ratings = env['rating.rating'].search([
        ('res_model', '=', 'tour.booking'),
        ('consumed', '=', True),
        ('rating', '>=', 1),
    ])
    already = set(Review.search([('booking_id', '!=', False)]).booking_id.ids)
    vals_list = []
    for rating in ratings:
        booking = env['tour.booking'].browse(rating.res_id).exists()
        if not booking or booking.id in already:
            continue
        already.add(booking.id)
        partner = rating.partner_id or booking.partner_id
        vals_list.append({
            'package_id': booking.package_id.id,
            'booking_id': booking.id,
            'partner_id': partner.id or False,
            'author_name': partner.name or booking.name_attendee or 'Verified Traveler',
            'author_email': partner.email or booking.email or False,
            'rating': max(1, min(5, round(rating.rating))),
            'comment': (rating.feedback or '').strip() or 'Rated %d out of 5.' % round(rating.rating),
            'state': 'published',
            'published_date': rating.rated_on or rating.write_date,
        })
    reviews = Review.create(vals_list)
    for review, vals in zip(reviews, vals_list):
        # Keep the original rating date so the review list stays in true order.
        cr.execute("UPDATE tour_package_review SET create_date = %s WHERE id = %s",
                   (vals['published_date'], review.id))
