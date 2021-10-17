import setuptools

with open('VERSION.txt', 'r') as f:
    version = f.read().strip()

setuptools.setup(
    name="odoo12-addons-oca-connector-magento",
    description="Meta package for oca-connector-magento Odoo addons",
    version=version,
    install_requires=[
        'odoo12-addon-connector_magento',
    ],
    classifiers=[
        'Programming Language :: Python',
        'Framework :: Odoo',
        'Framework :: Odoo :: 12.0',
    ]
)
