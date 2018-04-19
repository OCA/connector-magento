import setuptools

with open('VERSION.txt', 'r') as f:
    version = f.read().strip()

setuptools.setup(
    name="odoo10-addons-oca-connector-magento",
    description="Meta package for oca-connector-magento Odoo addons",
    version=version,
    install_requires=[
        'odoo10-addon-connector_magento',
        'odoo10-addon-connector_magento_customize_example',
        'odoo10-addon-connector_magento_firstname',
        'odoo10-addon-server_env_connector_magento',
    ],
    classifiers=[
        'Programming Language :: Python',
        'Framework :: Odoo',
    ]
)
