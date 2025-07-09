from odoo import models, fields, api
from odoo.exceptions import ValidationError
from odoo.tools import safe_eval
from ast import literal_eval
from elasticsearch import Elasticsearch
from datetime import datetime, date
import json
import logging

from pprint import pformat

_logger = logging.getLogger(__name__)

class ProductElasticsearchSync(models.Model):
    _inherit = 'product.product'

    def _get_product_fields(self):

        converted_data = self._clean_product_data()
        return converted_data
    
        product = self.read([])
        if product:
            if isinstance(product, list) and len(product) > 0:
                converted_data = self._clean_product_data(product[0])
                return converted_data
        else:
            return False
        
    def _clean_product_data(self):

        clean_data = {}

        product = self.read([])
        if product:
            if isinstance(product, list) and len(product[0]) > 0:

                    excluded_prefixes = [
                        'message_',
                        'access_',
                        'create_',
                        'write_',
                        'ebay_',
                        'bom_',
                        'nbr_',
                        'reordering_',
                        'property_',
                        'activity_',
                        'pos_',
                        'account_',
                        'purchase_',
                        'xero_',
                        'project_',
                        'my_activity_date_deadline',
                        'origin_country_id',
                        'incoming_qty',
                        'outgoing_qty',
                        'route_ids',
                        'product_tooltip',
                        'responsible_id',
                        'qc_triggers',
                        'fiscal_country_code',
                        'warehouse_id',
                        'location_id',
                        'has_available_route_ids',
                        'route_from_categ_ids',
                        'show_on_hand_qty_status_button',
                        'show_forecasted_',
                        'used_in_bom_count',
                        'mrp_product_qty',
                        'cost_method',
                        'valuation',
                        'is_auto_generated',
                        'prefix',
                        'digits',
                        'number_next',
                        'available_in_pos',
                        'to_weight',
                        'expense_policy',
                        'invoice_policy',
                        'service_tracking',
                        'deferred_revenue_category_id',
                        'sales_count_30_days',
                        'sale_line_warn_msg',
                    ]
                    
                    if isinstance(product[0], (dict, list)):
                        for field, value in product[0].items():
                            try:
                                if any(field.startswith(prefix) for prefix in excluded_prefixes):
                                    continue
                                if field == 'image_ids':
                                    if isinstance(value, list):
                                        images = []
                                        for image in value:
                                            fs = self.env['fs.product.image'].browse(image)
                                            if fs:
                                                img = fs.read()
                                                images.append({
                                                    'id': img[0]['id'],
                                                    'name': img[0]['name'],
                                                    'sequence': img[0]['sequence'],
                                                    'image': img[0]['image'],
                                                    'image_medium': img[0]['image_medium'],
                                                    'image_url': f"/web/image/fs.product.image/{img[0]['id']}/image",
                                                })
                                                        

                                        value = images

                                if isinstance(value, tuple) and len(value) >= 1:
                                    value = value[0]

                                if isinstance(value, (datetime, date)):
                                    clean_data[field] = value.isoformat()
                                elif value is None:
                                    continue
                                else:
                                    # Ensure value is JSON serializable
                                    json.dumps(value)
                                    clean_data[field] = value
                            except TypeError:
                                _logger.warning(f"Could not serialize field {field}: {value}")
                    else:
                        _logger.error(f"Expected dict, got {type(product)}")
                    
                    return clean_data

    def _sync_product_to_elasticsearch(self):
        """
        Synchronize product data to Elasticsearch
        """
        self.ensure_one()
        
        es_mapping = self.env['product.elasticsearch.mapping'].sudo().search([
            ('model', '=', 'product.product')
        ], limit=1)

        if es_mapping and es_mapping.indexing_domain:
            try:
                domain = literal_eval(es_mapping.indexing_domain)
                if not self.env['product.product'].browse(self.id).filtered_domain(domain):
                    return  # Skip indexing if product doesn't match domain
            except Exception as e:
                logging.error(f"Error evaluating indexing domain: {str(e)}")
                return
        else:
            _logger.info(f"No Index Domain found??")

        # Get Elasticsearch client
        es_client = self.env['elasticsearch.config'].sudo().search([], limit=1)._get_elasticsearch_client()

        try:
            product_data = self._get_product_fields()
            
            if product_data:
                # Index product in Elasticsearch
                index_name = self.env['elasticsearch.config'].search([], limit=1).index_name

                es_client.index(
                    index=index_name,
                    id=self.id,
                    body=product_data
                )
        except Exception as e:
            _logger.error(f"Elasticsearch Sync Error: {str(e)}")
            raise ValidationError(f"Failed to sync product {self.id} to Elasticsearch: {str(e)}")

    def _is_discount_product(self):
        for product in self:
            if product.type == 'service':  
                return True 
        return False

    def write(self, vals):
        res = super().write(vals)
                
        try:
            if not self._is_discount_product():
                for record in self:
                    record._sync_product_to_elasticsearch()

        except Exception as e:
            raise ValidationError(f"Failed to sync product {self.id} to Elasticsearch: {str(e)}")
        
        return res

    def create(self, vals):
        record = super().create(vals)
        
        try:
            if not self._is_discount_product():
                for record in self:
                    record._sync_product_to_elasticsearch()
        except Exception as e:
             raise ValidationError(f"Failed to sync product {self.id} to Elasticsearch: {str(e)}")
        
        return record
