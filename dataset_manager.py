#!/usr/bin/env python
import datetime
from glob import glob
import os
import re
from requests import get
from shutil import rmtree
import tarfile
import zipfile

#tethys imports
from tethys_dataset_services.engines import (GeoServerSpatialDatasetEngine, 
                                             CkanDatasetEngine)
#------------------------------------------------------------------------------
#Helper Function
#------------------------------------------------------------------------------
def get_watershed_subbasin_from_folder(folder_name):
    """
    Get's the watershed & subbasin name from folder
    """
    input_folder_split = folder_name.split("-")
    watershed = input_folder_split[0].lower()
    subbasin = input_folder_split[1].lower()
    return watershed, subbasin
#------------------------------------------------------------------------------
#Main CKAN Dataset Manager Class
#------------------------------------------------------------------------------
class CKANDatasetManager(object):
    """
    This class is used to find, zip and upload files to a CKAN data server
    #note: this does not delete the original files
    """
    def __init__(self, engine_url, api_key, model_name, 
                 dataset_notes="CKAN Dataset", 
                 resource_description="CKAN Resource",
                 date_format_string="%Y%m%d",
                 owner_org=""):
        if engine_url.endswith('/'):
            engine_url = engine_url[:-1]
        if not engine_url.endswith('api/action') and not engine_url.endswith('api/3/action'):
            engine_url += '/api/3/action'
        
        print engine_url
        self.dataset_engine = CkanDatasetEngine(endpoint=engine_url, apikey=api_key)
        self.model_name = model_name
        self.dataset_notes = dataset_notes
        self.resource_description = resource_description
        self.date_format_string = date_format_string
        self.owner_org = owner_org
        
    def initialize_run(self, watershed, subbasin, date_string):
        """
        Initialize run for watershed upload/download
        """
        self.watershed = watershed.lower()
        self.subbasin = subbasin.lower()
        self.date_string = date_string
        self.date = datetime.datetime.strptime(self.date_string, self.date_format_string)
        self.dataset_name = '%s-%s-%s-%s' % (self.model_name,
                                             self.watershed,
                                             self.subbasin,
                                             self.date.strftime("%Y%m%d"))
        self.resource_name = '%s-%s-%s-%s' % (self.model_name,
                                             self.watershed, 
                                             self.subbasin,
                                             self.date_string)

    def make_tarfile(self, file_path):
        """
        This function packages the dataset into a tar.gz file and
        returns the path
        """
        base_path = os.path.dirname(file_path)
        output_tar_file =  os.path.join(base_path, "%s.tar.gz" % self.resource_name)
            
        
        if not os.path.exists(output_tar_file):
            with tarfile.open(output_tar_file, "w:gz") as tar:
                    tar.add(file_path, arcname=os.path.basename(file_path))

        return output_tar_file

    def make_directory_tarfile(self, directory_path, search_string="*"):
        """
        This function packages all of the datasets into a tar.gz file and
        returns the path
        """
        base_path = os.path.dirname(directory_path)
        output_tar_file =  os.path.join(base_path, "%s.tar.gz" % self.resource_name)

        if not os.path.exists(output_tar_file):
            directory_files = glob(os.path.join(directory_path,search_string))
            with tarfile.open(output_tar_file, "w:gz") as tar:
                    for directory_file in directory_files:
                        tar.add(directory_file, arcname=os.path.basename(directory_file))

        return output_tar_file
    
    def get_dataset_id(self):
        """
        This function gets the id of a dataset
        """
        # Use the json module to load CKAN's response into a dictionary.
        response_dict = self.dataset_engine.search_datasets({ 'name': self.dataset_name })
        
        if response_dict['success']:
            if int(response_dict['result']['count']) > 0:
                return response_dict['result']['results'][0]['id']
            return None
        else:
            return None

    def create_dataset(self):
        """
        This function creates a dataset if it does not exist
        """
        dataset_id = self.get_dataset_id()
        #check if dataset exists
        if not dataset_id:
            #if it does not exist, create the dataset
            if not self.owner_org:
                result = self.dataset_engine.create_dataset(name=self.dataset_name,
                                                            notes=self.dataset_notes, 
                                                            version='1.0', 
                                                            tethys_app='streamflow_prediciton_tool',
                                                            waterhsed=self.watershed,
                                                            subbasin=self.subbasin,
                                                            month=self.date.month,
                                                            year=self.date.year)
            else:
                result = self.dataset_engine.create_dataset(name=self.dataset_name,
                                                            notes=self.dataset_notes, 
                                                            version='1.0', 
                                                            tethys_app='streamflow_prediciton_tool',
                                                            waterhsed=self.watershed,
                                                            subbasin=self.subbasin,
                                                            month=self.date.month,
                                                            year=self.date.year,
                                                            owner_org=self.owner_org)
            try:
                dataset_id = result['result']['id']
            except KeyError:
                print self.dataset_name, result
                raise

        return dataset_id
       
    def upload_resource(self, file_path, overwrite=False, file_format='tar.gz'):
        """
        This function uploads a resource to a dataset if it does not exist
        """
        #create dataset for each watershed-subbasin combo if needed
        dataset_id = self.create_dataset()
        if dataset_id:
            #check if dataset already exists
            resource_results = self.dataset_engine.search_resources({'name':self.resource_name},
                                                                    datset_id=dataset_id)
            try:
                #determine if results are exact or similar
                same_ckan_resource_id = ""
                if resource_results['result']['count'] > 0:
                    for resource in resource_results['result']['results']:
                        if resource['name'] == self.resource_name:
                            same_ckan_resource_id = resource['id']
                            break
                        
                if overwrite and same_ckan_resource_id:
                    #delete resource
                    """
                    CKAN API CURRENTLY DOES NOT WORK FOR UPDATE - bug = needs file or url, 
                    but requres both and to have only one ...

                    #update existing resource
                    print resource_results['result']['results'][0]
                    update_results = self.dataset_engine.update_resource(resource_results['result']['results'][0]['id'], 
                                                        file=file_to_upload,
                                                        url="",
                                                        date_uploaded=datetime.datetime.utcnow().strftime("%Y%m%d%H%M"))
                    """
                    self.dataset_engine.delete_resource(same_ckan_resource_id)

                if not same_ckan_resource_id or overwrite:
                    #upload resources to the dataset
                    return self.dataset_engine.create_resource(dataset_id, 
                                                    name=self.resource_name, 
                                                    file=file_path,
                                                    format=file_format, 
                                                    tethys_app="streamflow_prediciton_tool",
                                                    watershed=self.watershed,
                                                    subbasin=self.subbasin,
                                                    forecast_date=self.date_string,
                                                    description=self.resource_description,
                                                    url="")
                                                    
                else:
                    print "Resource", self.resource_name ,"exists. Skipping ..."
            except Exception,e:
                print e
                pass
        else:
            print "Failed to find/create dataset"
         
    def zip_upload_file(self, file_path):
        """
        This function uploads a resource to a dataset if it does not exist
        """
        #zip file and get dataset information
        print "Zipping files for watershed: %s %s" % (self.watershed, self.subbasin)
        tar_file_path = self.make_tarfile(file_path)    
        print "Finished zipping files"
        print "Uploading datasets"
        resource_info = self.upload_resource(tar_file_path)
        os.remove(tar_file_path)
        print "Finished uploading datasets"
        return resource_info

    def zip_upload_directory(self, directory_path, search_string="*", overwrite=False):
        """
        This function uploads a resource to a dataset if it does not exist
        """
        #zip file and get dataset information
        print "Zipping files for watershed: %s %s" % (self.watershed, self.subbasin)
        tar_file_path = self.make_directory_tarfile(directory_path, search_string)    
        print "Finished zipping files"
        print "Uploading datasets"
        resource_info = self.upload_resource(tar_file_path, overwrite)
        os.remove(tar_file_path)
        print "Finished uploading datasets"
        return resource_info
           
    def get_resource_info(self):
        """
        This function gets the info of a resource
        """
        dataset_id = self.get_dataset_id()
        if dataset_id:
            #check if dataset already exists
            resource_results = self.dataset_engine.search_resources({'name': self.resource_name},
                                                                    datset_id=dataset_id)
            try:
                if resource_results['result']['count'] > 0:
                    for resource in resource_results['result']['results']:
                        if resource['name'] == self.resource_name:
                            #upload resources to the dataset
                            return resource
            except Exception,e:
                print e
                pass
        return None

    def get_dataset_info(self):
        """
        This function gets the info of a resource
        """
        # Use the json module to load CKAN's response into a dictionary.
        response_dict = self.dataset_engine.search_datasets({ 'name': self.dataset_name })
        
        if response_dict['success']:
            if int(response_dict['result']['count']) > 0:
                for dataset in response_dict['result']['results']:
                    if dataset['name'] == self.dataset_name:
                        #upload resources to the dataset
                        return dataset
            return None
        else:
            return None

    
    def download_resource_from_info(self, extract_directory, resource_info_array, local_file=None):
        """
        Downloads a resource from url
        """
        data_downloaded = False
        #only download if file does not exist already
        check_location = extract_directory
        if local_file:
            check_location = os.path.join(extract_directory, local_file)
        if not os.path.exists(check_location):
            print "Downloading and extracting files for watershed:", self.watershed, self.subbasin
            try:
                os.makedirs(extract_directory)
            except OSError:
                pass
            for resource_info in resource_info_array:
                #for resource
                file_format = resource_info['format']
                
                local_tar_file = "%s.%s" % (resource_info['name'], file_format)
                    
                local_tar_file_path = os.path.join(extract_directory,
                                                   local_tar_file)
                if os.path.exists(local_tar_file_path):
                    print "Local raw file found. Skipping ..."
                    data_downloaded = False
                try:    
                    r = get(resource_info['url'], stream=True)
                    with open(local_tar_file_path, 'wb') as f:
                        for chunk in r.iter_content(chunk_size=1024): 
                            if chunk: # filter out keep-alive new chunks
                                f.write(chunk)
                                f.flush()
        
                    if file_format.lower() == "tar.gz":
                        with tarfile.open(local_tar_file_path) as tar:
                            tar.extractall(extract_directory)
                    elif file_format.lower() == "zip":
                        with zipfile.ZipFile(local_tar_file_path) as zip_file:
                            zip_file.extractall(extract_directory)
                    else:
                        print "Unsupported file format. Skipping ..."
                except Exception, ex:
                    print ex
                    data_downloaded = False
                    pass
                
                try:
                    os.remove(local_tar_file_path)
                except OSError:
                    pass
                
            print "Finished downloading and extracting file(s)"
            return data_downloaded
        else:
            print "Resource exists locally. Skipping ..."
            return False

    def download_resource(self, extract_directory, local_file=None):
        """
        This function downloads a resource
        """
        resource_info = self.get_resource_info()
        if resource_info:
            return self.download_resource_from_info(extract_directory, 
                                                    [resource_info],
                                                     local_file)
        else:
            print "Resource not found in CKAN. Skipping ..."
            return False

    def download_prediction_resource(self, watershed, subbasin, date_string, extract_directory):
        """
        This function downloads a prediction resource
        """
        self.initialize_run(watershed, subbasin, date_string)
        self.download_resource(extract_directory)

#------------------------------------------------------------------------------
#ECMWF RAPID CKAN Dataset Manager Class
#------------------------------------------------------------------------------
class ECMWFRAPIDDatasetManager(CKANDatasetManager):
    """
    This class is used to find and download, zip and upload ECMWFRAPID 
    prediction files from/to a data server
    """
    def __init__(self, engine_url, api_key, owner_org=""):
        super(ECMWFRAPIDDatasetManager, self).__init__(engine_url, 
                                                        api_key,
                                                        'erfp',
                                                        "ECMWF-RAPID Flood Predicition Dataset",
                                                        'This dataset contians NetCDF3 files produced by '
                                                        'downscalsing ECMWF forecasts and routing them with RAPID',
                                                        "%Y%m%d.%H",
                                                        owner_org
                                                        )
                                                        
    def initialize_run_ecmwf(self, watershed, subbasin, date_string):
        """
        Initialize run for watershed upload/download custom for ecmwf
        """
        self.watershed = watershed.lower()
        self.subbasin = subbasin.lower()
        self.date_string = date_string[:11]
        self.date = datetime.datetime.strptime(self.date_string, self.date_format_string)
        self.dataset_name = '%s-%s-%s-%s' % (self.model_name, 
                                             self.watershed, 
                                             self.subbasin, 
                                             self.date.strftime("%Y%m%dt%H"))
                                                
    def update_resource_ensemble_number(self, ensemble_number):
        """
        Set ensemble number in resource name for ecmwf resource
        """
        self.resource_name = '%s-%s-%s-%s-%s' % (self.model_name,
                                                 self.watershed, 
                                                 self.subbasin,
                                                 self.date_string,
                                                 ensemble_number)

    def update_resource_return_period(self, return_period):
        """
        Set ensemble number in resource name for ecmwf resource
        """
        self.resource_name = '%s-%s-%s-%s-warning_points_%s' % (self.model_name,
                                                                self.watershed,
                                                                self.subbasin,
                                                                self.date_string,
                                                                return_period)

    def zip_upload_warning_points_in_directory(self, directory_path, search_string="return_*_points.txt"):
        """
        This function packages all of the datasets into individual tar.gz files and
        uploads them to the dataset
        """
        base_path = os.path.dirname(directory_path)
        return_period_search = re.compile(r'return_(\d+)_points\.txt')

        #zip file and get dataset information
        print "Zipping and uploading warning points files for watershed: %s %s" % (self.watershed, self.subbasin)
        directory_files = glob(os.path.join(directory_path,search_string))
        resource_info = None
        for directory_file in directory_files:
            return_period = return_period_search.search(os.path.basename(directory_file)).group(1)
            self.update_resource_return_period(return_period)
            #tar.gz file
            output_tar_file =  os.path.join(base_path, "%s.tar.gz" % self.resource_name)
            if not os.path.exists(output_tar_file):
                with tarfile.open(output_tar_file, "w:gz") as tar:
                    tar.add(directory_file, arcname=os.path.basename(directory_file))
            #upload file
            resource_info = self.upload_resource(output_tar_file)
            if resource_info is not None:
                if not resource_info['success']:
                    print 'Error:', resource_info['error']
            os.remove(output_tar_file)
        print "%s datasets uploaded" % len(directory_files)
        return resource_info

    def zip_upload_forecasts_in_directory(self, directory_path, search_string="*.nc"):
        """
        This function packages all of the datasets into individual tar.gz files and
        uploads them to the dataset
        """
        base_path = os.path.dirname(directory_path)
        ensemble_number_search = re.compile(r'Qout_\w+_(\d+)\.nc')

        #zip file and get dataset information
        print "Zipping and uploading files for watershed: %s %s" % (self.watershed, self.subbasin)
        directory_files = glob(os.path.join(directory_path,search_string))
        for directory_file in directory_files:
            ensemble_number = ensemble_number_search.search(os.path.basename(directory_file)).group(1)
            self.update_resource_ensemble_number(ensemble_number)
            #tar.gz file
            output_tar_file =  os.path.join(base_path, "%s.tar.gz" % self.resource_name)
            if not os.path.exists(output_tar_file):
                with tarfile.open(output_tar_file, "w:gz") as tar:
                    tar.add(directory_file, arcname=os.path.basename(directory_file))
            #upload file
            resource_info = self.upload_resource(output_tar_file)
            #resource_info is None if exists already
            if resource_info is not None:
                if not resource_info['success']:
                    print 'Error:', resource_info['error']
            os.remove(output_tar_file)
        print "%s datasets uploaded" % len(directory_files)
        return resource_info

    def zip_upload_resources(self, source_directory):
        """
        This function packages all of the datasets in to tar.gz files and
        returns their attributes
        """
        watershed_directories = [d for d in os.listdir(source_directory) \
                                if os.path.isdir(os.path.join(source_directory, d))]

        for watershed_directory in watershed_directories:
            watershed_dir = os.path.join(source_directory, watershed_directory)
            watershed, subbasin = get_watershed_subbasin_from_folder(watershed_directory)
            date_strings = [d for d in os.listdir(watershed_dir) \
                            if os.path.isdir(os.path.join(watershed_dir, d))]
            for date_string in date_strings:
                upload_dir = os.path.join(watershed_dir, date_string)
                self.initialize_run_ecmwf(watershed, subbasin, date_string)
                self.zip_upload_forecasts_in_directory(upload_dir,
                                                       'Qout_*.nc')
                self.zip_upload_warning_points_in_directory(upload_dir)
    
    def download_recent_resource(self, watershed, subbasin, main_extract_directory):
        """
        This function downloads the most recent resource within 6 days
        """
        iteration = 0
        download_file = False
        today_datetime = datetime.datetime.utcnow()
        #search for datasets within the last 6 days
        while not download_file and iteration < 12:
            today =  today_datetime - datetime.timedelta(seconds=iteration*12*60*60)
            hour = '1200' if today.hour > 11 else '0'
            date_string = '%s.%s' % (today.strftime("%Y%m%d"), hour)
            
            self.initialize_run_ecmwf(watershed, subbasin, date_string)
            #get list of all resources
            dataset_info = self.get_dataset_info()
            if dataset_info and main_extract_directory and os.path.exists(main_extract_directory):
                #check if forecast is ready to be downloaded
                forecast_count = 0
                warning_point_count = 0
                if dataset_info['num_resources'] >= 52:
                    for resource in dataset_info['resources']:
                        if "warning_points" in resource['name']:
                            warning_point_count += 1
                        else:
                           forecast_count += 1
                dataset_ready = dataset_info['num_resources'] >= 52
                if warning_point_count > 0 and warning_point_count < 3:
                    dataset_ready = False
                if forecast_count < 52:
                    dataset_ready = False

                #make sure there are at least 52 or at lest a day has passed before downloading
                if dataset_ready or (today_datetime-today >= datetime.timedelta(1)):
                    extract_directory = os.path.join(main_extract_directory, self.watershed, self.subbasin, date_string)
                    download_file = self.download_resource_from_info(extract_directory,
                                                     dataset_info['resources'])

            iteration += 1
                    
        if not download_file:
            print "Recent resources not found. Skipping ..."
                                      
#------------------------------------------------------------------------------
#WRF-Hydro RAPID CKAN Dataset Manager Class
#------------------------------------------------------------------------------
class WRFHydroHRRRDatasetManager(CKANDatasetManager):
    """
    This class is used to find and download, zip and upload ECMWFRAPID 
    prediction files from/to a data server
    """
    def __init__(self, engine_url, api_key, owner_org=""):
        super(WRFHydroHRRRDatasetManager, self).__init__(engine_url, 
                                                        api_key,
                                                        'wrfp',
                                                        "WRF-Hydro HRRR Flood Predicition Dataset",
                                                        'This dataset contians NetCDF3 files produced by '
                                                        'downscalsing WRF-Hydro forecasts and routing them with RAPID',
                                                        "%Y%m%dT%H%MZ",
                                                        owner_org
                                                        )
          
    def zip_upload_resource(self, source_file, watershed, subbasin):
        """
        This function packages all of the datasets in to tar.gz files and
        returns their attributes
        """
        #WRF-Hydro HRRR time format string "%Y%m%dT%H%MZ"
        file_name = os.path.basename(source_file)
        date_string = file_name.split("_")[1]
        self.initialize_run(watershed, subbasin, date_string)
        self.zip_upload_file(source_file)


    def download_recent_resource(self, watershed, subbasin, main_extract_directory):
        """
        This function downloads the most recent resource within 1 day
        """
        iteration = 0
        download_file = False
        today_datetime = datetime.datetime.utcnow().replace(minute=0, second=0, microsecond=0)
        #search for datasets within the last day
        while not download_file and iteration < 24:
            today =  today_datetime - datetime.timedelta(seconds=iteration*60*60)
            date_string = today.strftime(self.date_format_string)
            self.initialize_run(watershed, subbasin, date_string)
            resource_info = self.get_resource_info()
            if resource_info and main_extract_directory and os.path.exists(main_extract_directory):
                extract_directory = os.path.join(main_extract_directory, self.watershed, self.subbasin)
                download_file = self.download_resource(extract_directory, "RapidResult_%s_CF.nc" % date_string)
            iteration += 1
                    
        if not download_file:
            print "Recent resources not found. Skipping ..."

#------------------------------------------------------------------------------
#RAPID Input CKAN Dataset Manager Class
#------------------------------------------------------------------------------
class RAPIDInputDatasetManager(CKANDatasetManager):
    """
    This class is used to find and download, zip and upload ECMWFRAPID 
    prediction files from/to a data server
    """
    def __init__(self, engine_url, api_key, model_name, app_instance_id, owner_org=""):
        super(RAPIDInputDatasetManager, self).__init__(engine_url, 
                                                        api_key,
                                                        model_name,
                                                        "RAPID Input Dataset for %s" % model_name,
                                                        'This dataset contians RAPID files for %s' % model_name,
                                                        owner_org=owner_org)
        self.app_instance_id = app_instance_id
        self.dataset_name = '%s-rapid-input-%s' % (self.model_name, self.app_instance_id)

    def initialize_run(self, watershed, subbasin):
        """
        Initialize run for watershed upload/download
        """
        self.watershed = watershed.lower()
        self.subbasin = subbasin.lower()
        self.date = datetime.datetime.utcnow()
        self.date_string = self.date.strftime(self.date_format_string)
        self.resource_name = '%s-%s-%s-rapid-input' % (self.model_name,
                                                       self.watershed, 
                                                       self.subbasin)
    def zip_upload_resource(self, source_directory):
        """
        This function adds RAPID files in to zip files and
        uploads files to data store
        """
        #get info for waterhseds
        basin_name_search = re.compile(r'rapid_namelist_(\w+).dat')
        namelist_files = glob(os.path.join(source_directory,'rapid_namelist_*.dat'))
        if namelist_files:
            subbasin = basin_name_search.search(namelist_files[0]).group(1)
            watershed = os.path.basename(source_directory)
         
            self.initialize_run(watershed, subbasin)
            self.zip_upload_directory(source_directory)

    def download_model_resource(self, resource_info, extract_directory):
        """
        This function downloads a prediction resource
        """
        self.initialize_run(resource_info['watershed'], resource_info['subbasin'])
        self.download_resource_from_info(extract_directory, [resource_info])

    def upload_model_resource(self, upload_file, watershed, subbasin):
        """
        This function uploads file to CKAN
        """
        self.initialize_run(watershed, subbasin)
        resource_info = self.upload_resource(upload_file, 
                                             True,
                                             '.zip')
        os.remove(upload_file)
        return resource_info
        
    def sync_dataset(self, extract_directory):
        """
        This function syncs the dataset with the directory
        """
        # Use the json module to load CKAN's response into a dictionary.
        dataset_info = self.get_dataset_info()
        if dataset_info:
            #get list of resources on CKAN
            current_ckan_resources = [d for d in dataset_info['resources'] \
                                      if 'watershed' in d and 'subbasin' in d]

            #get list of watersheds and subbasins on local instance
            current_local_resources = []
            rapid_input_folders = [d for d in os.listdir(extract_directory) \
                                   if os.path.isdir(os.path.join(extract_directory, d))]
    
            for rapid_input_folder in rapid_input_folders:
                input_folder_split = rapid_input_folder.split("-")
                try:
                    subbasin = input_folder_split[1]
                except IndexError:
                    subbasin = ""
                    pass
                current_local_resources.append({'watershed': input_folder_split[0],
                                                'subbasin': subbasin,
                                                'folder': rapid_input_folder
                                                })

            date_compare = datetime.datetime.utcnow()-datetime.timedelta(hours=12, minutes=30)
            #STEP 1: Remove resources no longer on CKAN or update local resource
            for local_resource in current_local_resources:
                ckan_resource = [d for d in current_ckan_resources if \
                                    (d['watershed'].lower() == local_resource['watershed'].lower()) and \
                                    d['subbasin'].lower() == local_resource['subbasin'].lower()]

                local_directory = os.path.join(extract_directory, local_resource['folder'])
                if not ckan_resource:
                    #remove resources no longer on CKAN
                    print "LOCAL DELETE", local_resource['watershed'], local_resource['subbasin']
                    rmtree(local_directory)
                elif datetime.datetime.strptime(ckan_resource[0]['created'].split(".")[0], "%Y-%m-%dT%H:%M:%S") > date_compare:
                    #2015-05-12T14:01:08.572338
                    #remove out of date local resources
                    print "LOCAL PAST DELETE", local_resource['watershed'], local_resource['subbasin']
                    rmtree(local_directory)
            
            #STEP 2: Add new resources to local instance if not already here
            for ckan_resource in current_ckan_resources:         
                print "ATTEMPT DOWNLOAD", ckan_resource['watershed'], ckan_resource['subbasin']
                self.download_model_resource(ckan_resource,
                                             os.path.join(extract_directory, "%s-%s" % (ckan_resource['watershed'],
                                                                                        ckan_resource['subbasin'])))

#------------------------------------------------------------------------------
#Main GeoServer Dataset Manager Class
#------------------------------------------------------------------------------
class GeoServerDatasetManager(object):
    """
    This class is used to upload files to a GeoServer and remove files 
    from a geoserver for the Streamflow Prediction Tool
    """
    def __init__(self, engine_url, username, password, app_instance_id):
        """
        Initialize and validate the GeoServer credentials
        """
        if engine_url.endswith('/'):
            engine_url = engine_url[:-1]

        if not engine_url.endswith('/geoserver/rest'):

            if not engine_url.endswith('/geoserver'):
                engine_url += '/geoserver/rest'

            else: # engine_url.endswith('/geoserver')
                engine_url += '/rest'
        
        if not engine_url.endswith('/geoserver/rest'):
            raise Exception("Invalid geoserver API endpoint.")
            
        self.engine_url = engine_url
        self.dataset_engine = GeoServerSpatialDatasetEngine(endpoint=engine_url, 
                                                            username=username,
                                                            password=password)
        self.resource_workspace = 'spt-%s' % app_instance_id
        self.dataset_engine.create_workspace(workspace_id=self.resource_workspace, 
                                             uri=app_instance_id)
                                             
    def check_shapefile_input_files(self, shp_files):
        """
        #make sure required files for shapefiles are included
        """
        required_extensions = ['.shp', '.shx', '.prj','.dbf']
        accepted_extensions = []
        for shp_file in shp_files:
            
            if isinstance(shp_file, basestring) and os.path.exists(shp_file):
                #if file paths
                file_name, file_extension = os.path.splitext(shp_file)
            elif "name" in dir(shp_file):
                #if local upload via web
                file_name, file_extension = os.path.splitext(shp_file.name)
            else:
                raise Exception("Invalid part of shapefile %s" % shp_file)

            for required_extentsion in required_extensions: 
                if file_extension == required_extentsion:
                    accepted_extensions.append(required_extentsion)
                    required_extensions.remove(required_extentsion)
                    
        if required_extensions:
            raise Exception("Shapefile missing files with extensions: %s" \
                            % ", ".join(required_extensions))

    def rename_shapefile_input_files(self, file_list, new_file_name):
        """
        #rename files to be consistent
        """
        for index, shp_file in enumerate(file_list):
            if isinstance(shp_file, basestring) and os.path.exists(shp_file):
                #if file paths
                file_name, file_extension = os.path.splitext(shp_file)
                new_path = os.path.join(os.path.dirname(shp_file),
                                       "%s%s" % (new_file_name, file_extension))
                os.rename(shp_file, new_path)
                file_list[index] = new_path
                
            elif "name" in dir(shp_file):
                #if file upload via web
                file_name, file_extension = os.path.splitext(shp_file.name)
                shp_file.name = "%s%s" % (new_file_name, file_extension)
            else:
                raise Exception("Invalid part of shapefile %s" % shp_file)
    
    def get_layer_name(self, resource_name):
        """
        Get full layer name based on resource name
        """
        return '{0}:{1}'.format(self.resource_workspace, resource_name)
                                             
    def upload_shapefile(self, resource_name, file_list):
        
        """
        Upload shapefile to geoserver
        """
        #check inputs
        self.check_shapefile_input_files(file_list)
        #rename files approprately
        self.rename_shapefile_input_files(file_list, resource_name)
        
        layer_name = self.get_layer_name(resource_name)
        if "name" in dir(file_list[0]):
            #if upload via web
            self.dataset_engine.create_shapefile_resource(layer_name, 
                                                          shapefile_upload=file_list,
                                                          overwrite=True)
        else:
            #if file paths
            file_name = os.path.splitext(file_list[0])[0]
            self.dataset_engine.create_shapefile_resource(layer_name, 
                                                          shapefile_base=file_name,
                                                          overwrite=True)
            
        return layer_name
        
    def purge_remove_geoserver_layer(self, layer_id):
        """
        completely remove geoserver layer
        """
        self.dataset_engine.delete_layer(layer_id, purge=True, recurse=True)
        self.dataset_engine.delete_resource(layer_id, purge=True, recurse=True)
        self.dataset_engine.delete_store(layer_id, purge=True, recurse=True)


if __name__ == "__main__":
    """    
    Tests for the datasets
    """
    #engine_url = 'http://test.ckan.org/api/3/action'
    #api_key = 'fhdfhadHFADH'
    #ECMWF
    """
    er_manager = ECMWFRAPIDDatasetManager(engine_url, api_key, owner_org="erdc")
    er_manager.zip_upload_resources(source_directory='/home/alan/work/rapid-io/output/')
    er_manager.download_prediction_resource(watershed='magdalena', 
                                            subbasin='el_banco', 
                                            date_string='20150505.0', 
                                            extract_directory='/home/alan/work/rapid/output/magdalena/20150505.0')
    er_manager.download_recent_resource(watershed="rio_yds", 
                                        subbasin="palo_alto", 
                                        main_extract_directory='/home/alan/tethysdev/tethysapp-erfp_tool/ecmwf_rapid_predictions' )
    """
    #WRF-Hydro
    """
    wr_manager = WRFHydroHRRRDatasetManager(engine_url, api_key)
    wr_manager.zip_upload_resource(source_file='/home/alan/Downloads/RapidResult_20150405T2300Z_CF.nc',
                                    watershed='usa',
                                    subbasin='usa')
    wr_manager.download_prediction_resource(watershed='usa',
                                            subbasin='usa', 
                                            date_string='20150405T2300Z', 
                                            extract_directory='/home/alan/tethysdev/tethysapp-erfp_tool/wrf_hydro_rapid_predictions/usa/usa')
    wr_manager.download_recent_resource(watershed='nfie_wrfhydro_conus',
                                        subbasin='nfie_wrfhydro_conus', 
                                        main_extract_directory='/home/alan/tethysdev/tethysapp-erfp_tool/wrf_hydro_rapid_predictions')
    """
    #RAPID Input
    """
    app_instance_id = 'eb76561dc4ba513c994a00f7721becf1'
    ri_manager = RAPIDInputDatasetManager(engine_url, api_key, 'ecmwf', app_instance_id)
    ri_manager.zip_upload_resource(source_directory='/home/alan/work/tmp_input/rio_yds')
    ri_manager.download_model_resource(watershed='nfie_texas_gulf_region', 
                                       subbasin='huc_2_12', 
                                       extract_directory='/home/alan/work/tmp_input/nfie_texas_gulf_region')
    ri_manager.sync_dataset('/home/alan/work/tmp_input/')
    """
