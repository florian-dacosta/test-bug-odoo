# -*- coding: utf-8 -*-

import openerp.tests.common as test_common


class TestSaleOrderLotSelection(test_common.SingleTransactionCase):

    def setUp(self):
        super(TestSaleOrderLotSelection, self).setUp()
        self.supplier_location = self.env.ref(
            'stock.stock_location_suppliers')
        self.stock_location = self.env.ref('stock.stock_location_stock')
        self.product_model = self.env['product.product']
        self.lot_model = self.env['stock.production.lot']


    def test_restrict_lot_id(self):
        product_vals = {
            'name': 'Test multi_lot_by_product',
            'tracking': 'lot',
            'type': 'product',
        }
        # Create 1 product and 2 lot for this product
        self.productA = self.env['product.product'].create(product_vals)
        self.lot1 = self.lot_model.create({'name': 'LOT1', 'product_id': self.productA.id})
        self.lot2 = self.lot_model.create({'name': 'LOT2', 'product_id': self.productA.id})
        # Create 1 procurement_group and one picking with 2 lines with the 2 different lot created before
        group_id = self.env['procurement.group'].create({'name': 'test group'}).id
        move1_vals = {
            'product_id': self.productA.id,
            'name': self.productA.name,
            'product_uom_qty': 1,
            'location_id': self.stock_location.id,
            'location_dest_id': self.supplier_location.id,
            'date': '2016-11-15',
            'product_uom':1,
            'company_id': 1,
            'restrict_lot_id': self.lot1.id,
            'procure_method': 'make_to_stock',
            'group_id': group_id,
            'picking_type_id': 3,
        }
        move1 = self.env['stock.move'].create(move1_vals)
        move1.action_confirm()
        move2_vals = {
            'product_id': self.productA.id,
            'name': self.productA.name,
            'product_uom_qty': 1,
            'location_id': self.stock_location.id,
            'location_dest_id': self.supplier_location.id,
            'date': '2016-11-15',
            'product_uom':1,
            'company_id': 1,
            'restrict_lot_id': self.lot2.id,
            'procure_method': 'make_to_stock',
            'group_id': group_id,
            'picking_type_id': 3,
        }
        move2 = self.env['stock.move'].create(move1_vals)
        move2.action_confirm()

        picking = move1.picking_id
        self.assertEqual(picking.id, move2.picking_id.id)

        # force assign the picking
        picking.force_assign()

        self.assertEqual(len(picking.pack_operation_ids), 1)
        # We have one operation with qty = 2, we want to transfer only one product
        # With the lot 2
        pack_lot_vals = {
            'operation_id': picking.pack_operation_ids.id,
            'qty': 1,
            'qty_todo': 1,
            'lot_id': self.lot2.id,
        }
        self.env['stock.pack.operation.lot'].create(pack_lot_vals)
        picking.pack_operation_ids.write({'qty_done': 1})
        # Confirm the picking
        transfer_wizard = self.env['stock.backorder.confirmation'].create({'pick_id': picking.id})
        transfer_wizard.process()
        for move in picking.move_lines:
            # As there is no stock available in the system, it will create a negative quant, but we don't need it.
            quant = move.quant_ids.filtered(lambda q:q.qty>0)

            # The positive quant created has the right lot (lot2) but Odoo transfered the wrong move (move1)
            self.assertEqual(quant.lot_id.id, move.restrict_lot_id.id)
