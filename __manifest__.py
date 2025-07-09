{
    'name': 'Elasticsearch Product Connector',
    'version': '1.0',
    'category': 'Connector',
    'summary': 'Advanced Elasticsearch Connector for Product Indexing',
    'description': """
    Elasticsearch Connector for Odoo Products
    - Configurable Elasticsearch server connection
    - Automatic index and mapping creation
    - Streaming bulk indexing
    - Product creation and update synchronization
    """,
    'depends': ['product', 'graphql_base'],
    'data': [
        'security/ir.model.access.csv',
        'views/elasticsearch_config_view.xml',
        'views/product_elasticsearch_mapping_view.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'elasticsearch_connector/static/src/js/json_widget.js',
            'elasticsearch_connector/static/src/xml/json_widget.xml',
        ],
    },
    'external_dependencies': {
        'python': ['elasticsearch'],
    },
}
