# spt_dataset_manager
Streamflow Prediction Tool Dataset Manager (for CKAN and GeoServer)

#Installation Instructions

##Step 1: Install tethys_dataset_services
```
$ pip install requests_toolbelt tethys_dataset_services future
```
##Step 2: Download the source code
```
$ cd /path/to/your/scripts/
$ git clone https://github.com/erdc-cm/spt_dataset_manager.git
```
##Step 3: Install the script
```
$ cd spt_dataset_manager
$ python setup.py install
```

#Troubleshooting
## ImportError: No module named packages.urllib3.poolmanager
```
$ pip install pip --upgrade
```
Restart your terminal
```
$ pip install requests --upgrade
```
## If you are using CKAN 2.3 -2.5:
If you see this error when uploading a dataset: The url and file parameters are mutually exclusive: use one, not both.

You may need to go to: /usr/lib/tethys/lib/python2.7/site-packages/tethys_dataset_services/engines/ckan_engine.py
and mmodify this section of code to look like this:
```python
def create_resource(self, dataset_id, url=None, file=None, console=False, **kwargs):
  ...
  #if url and file:
      #raise IOError('The url and file parameters are mutually exclusive: use one, not both.')
  if not url and not file:
      raise IOError('The url or file parameter is required, but do not use both.')
      
  ...


```
