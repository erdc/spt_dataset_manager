from setuptools import setup, find_packages

setup(
    name='spt_dataset_manager',
    version='0.0.1',
    description='Streamflow Prediction Tool Dataset Manager (for CKAN and GeoServer)',
    long_description='Streamflow Prediction Tool (SPT) Dataset Manager (for CKAN and GeoServer)'
                     ' is the manager to upload and download datasets to CKAN and geoserver'
                     ' associated with the SPT',
    keywords='Streamflow Prediction Tool, RAPID',
    author='Alan Dee Snow',
    author_email='alan.d.snow@usace.army.mil',
    url='https://github.com/erdc/spt_dataset_manager',
    download_url='https://github.com/erdc/spt_dataset_manager/archive/0.0.1.tar.gz',
    license='BSD 3-Clause',
    packages=find_packages(),
    install_requires=['future', 'requests', 'requests_toolbelt', 'tethys_dataset_services'],
    classifiers=[
                'Intended Audience :: Developers',
                'Intended Audience :: Science/Research',
                'Operating System :: OS Independent',
                'Programming Language :: Python',
                'Programming Language :: Python :: 2',
                'Programming Language :: Python :: 2.7',
                'Programming Language :: Python :: 3',
                'Programming Language :: Python :: 3.5',
                ],
)
