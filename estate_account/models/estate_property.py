from datetime import datetime, timedelta
from odoo import _, api, fields, models, Command
from odoo.tools.float_utils import float_is_zero, float_compare
from odoo.exceptions import UserError


class EstateProperty(models.Model):
    _inherit = "estate.property"

    def action_set_sold(self):
        for record in self:
            record._create_invoice()
        return super().action_set_sold()
    
    def _create_invoice(self):
        self.ensure_one()
        invoice_vals = {
            'partner_id': self.buyer.id,
            'move_type': 'out_invoice',
            'invoice_line_ids': [
                Command.create({
                    'name': f'Commission for {self.name}',
                    'quantity': 1,
                    'price_unit': self.selling_price * 0.06,
                }),
                Command.create({
                    'name': 'Administrative Fees',
                    'quantity': 1,
                    'price_unit': 100.00,
                }),
            ]
        }
        self.env['account.move'].create(invoice_vals)