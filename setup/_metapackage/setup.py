import setuptools

with open('VERSION.txt', 'r') as f:
    version = f.read().strip()

setuptools.setup(
    name="odoo8-addons-oca-connector-magento",
    description="Meta package for oca-connector-magento Odoo addons",
    version=version,
    install_requires=[
        'odoo8-addon-customize_example',
        'odoo8-addon-magentoerpconnect',
        'odoo8-addon-magentoerpconnect_pricing',
        'odoo8-addon-server_env_magentoerpconnect',
    ],
    classifiers=[
        'Programming Language :: Python',
        'Framework :: Odoo',
        'Framework :: Odoo :: 8.0',
    ]
)
