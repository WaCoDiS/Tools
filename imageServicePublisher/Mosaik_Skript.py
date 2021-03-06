# -*- coding: utf-8 -*-
# ---------------------------------------------------------------------------
# Mosaik_Skript.py
# Created on: 2019-07-09 10:47:30.00000
#
# Description:
# A connection to ArcGIS Server must be established in the Catalog window of ArcMap
# before running this script
#
# Following variables must be defined in config.txt
# 1. Workspace ("Folder for Created FileGDB and Mosaic Datasets") MUST BE DEFINED
# 2. username and password for ServerConnection MUST BE DEFINED
# 3. server_url
# 4. name of service Ags File for all Services: Default:wacodisService.ags
# 5. outdirServerConFolder -->  Path to save server connection file and registered folder for reference Data
# 
# Following variables are passed as command line arguments:
# IMAGE ("Absolute path to TIF DataResultProducts") MUST BE DEFINED
# METADATA Absolute path to metadata file
# Usage: Mosaik_Skript.py [-h] <IMAGE> <METADATA>
# ---------------------------------------------------------------------------
import argparse

parser = argparse.ArgumentParser(description='Create a mosaic dataset from an EO product image and publish it as an ArcGIS Image Service.')
parser.add_argument('image', metavar='<IMAGE>', type=str, help='the path to an EO product image that will be processed')
#parser.add_argument('collection', metavar='<COLLECTION>', type=str, help='a collection id relating to the service the EO product image will be published')
parser.add_argument('metadata', metavar='<METADATA>', type=str, help='the path to the metadata file of an EO product image that will be processed')

args = parser.parse_args()

# Set the necessary product code
import arcinfo

# Import modules
import arcpy
import sys
import os
import fnmatch
import json

#arcpy.env.overwriteOutput = True

pixel_type_dict = {
	"EO:WACODIS:DAT:FOREST_VITALITY_CHANGE": "32_BIT_FLOAT",
	"EO:WACODIS:DAT:INTRA_LAND_COVER_CLASSIFICATION": "8_BIT_UNSIGNED",
    "EO:WACODIS:DAT:SEALING_FACTOR": "32_BIT_FLOAT",
    "EO:WACODIS:DAT:VEGETATION_DENSITY_LAI": "32_BIT_FLOAT",
    "EO:WACODIS:DAT:NDVI": "32_BIT_FLOAT",
    "EO:WACODIS:DAT:S2A_RAW": "32_BIT_FLOAT"
	}

# Local variables:
try:
    # Local variables:
    config = open("config.txt").readlines()
    workspace = config[0].split("=")[1].strip("\n")
    username = config[1].split("=")[1].strip("\n")
    password = config[2].split("=")[1].strip("\n")
    server_url = config[3].split("=")[1].strip("\n")
    out_name = config[4].split("=")[1].strip("\n")
    outdirServerCon = config[5].split("=")[1].strip("\n")
    out_folder_path = outdirServerCon
    con = os.path.join(outdirServerCon, out_name)
    use_arcgis_desktop_staging_folder = True
    workspace_gdb = workspace
    data_store_path = workspace_gdb
except IOError:
    sys.exit('Failed in reading Configurations')

#Script arguments
product_result = args.image
metadata_path = args.metadata
serviceJSON = open(metadata_path).read()
json_metadata = json.loads(serviceJSON)
startTimefield = str(json_metadata['timeFrame']['startTime'])
endTimefield = str(json_metadata['timeFrame']['endTime'])
col_id = str(json_metadata['serviceDefinition']['productCollection']).split("/")[1]
collection_id = col_id.replace(":", "_")

if col_id in pixel_type_dict:
    product_pixel_type = pixel_type_dict[col_id]
else:
    print "No pixel type found for product {}".format(product_result)
    product_pixel_type = "32_BIT_FLOAT"
print "Set pixel type to {} for product {}".format(product_pixel_type, product_result)

try:
    product_path = product_result.split('\\')
    product_name = product_path[len(product_path)-1]
    if arcpy.Exists(workspace_gdb + "\\"+collection_id+".gdb"):
        print "GDB " + collection_id + " exists"
        #Test_Script.pypython Test_Script.py -h Do nothing
    else:
        arcpy.CreateFileGDB_management(workspace_gdb, collection_id+".gdb")
        # Create Master Mosaic
        # Process: Mosaik-Dataset erstellen
        arcpy.CreateMosaicDataset_management(workspace_gdb+"\\" + collection_id + '.gdb', "Master" + '_' + collection_id,
                                                 "PROJCS['ETRS_1989_UTM_Zone_32N',GEOGCS['GCS_ETRS_1989',DATUM['D_ETRS_1989',SPHEROID['GRS_1980',6378137.0,298.257222101]],"
                                                 "PRIMEM['Greenwich',0.0],UNIT['Degree',0.0174532925199433]],PROJECTION['Transverse_Mercator'],PARAMETER['False_Easting',500000.0],"
                                                 "PARAMETER['False_Northing',0.0],PARAMETER['Central_Meridian',9.0],PARAMETER['Scale_Factor',0.9996],PARAMETER['Latitude_Of_Origin',0.0],"
                                                 "UNIT['Meter',1.0]];-5120900 -9998100 10000;-100000 10000;-100000 10000;0,001;0,001;0,001;IsHighPrecision",pixel_type=product_pixel_type)
        print "Created Master Mosaic for " + collection_id
        arcpy.AddField_management(workspace_gdb+"\\"+collection_id + '.gdb\\' + 'Master' + "_" + collection_id, "startTime", "text")
        arcpy.AddField_management(workspace_gdb+"\\"+collection_id + '.gdb\\' + 'Master' + "_" + collection_id, "endTime", "text")
        print "Added field"
        arcpy.SetMosaicDatasetProperties_management(
                workspace_gdb+"\\" + collection_id + '.gdb\\' "Master" + '_' + collection_id,
                use_time="ENABLED", start_time_field="startTime", end_time_field="endTime",
                time_format="YYYY-MM-DD hh:mm:ss.s",time_interval=1.0, time_interval_units="Days")
        print "Mosaic Properties were set"
except arcpy.ExecuteError:
    e = sys.exc_info()[1]
    print(e.args[0])
    print arcpy.GetMessages() + "\n\n"
    sys.exit("Failed in creating GDB and MasterMosaic")


try:
    # Create MosaicDataset for every processed Rasterproduct
    # Add the belonging Rasterfile(TIF) to the created MosaicDataset
    mosaic_dataset_name = "T_" + product_name[:len(product_name)-4]+'_Mosaic'
    mosaic_product_name = mosaic_dataset_name.replace("-", "_")
    # Process: Mosaik-Dataset erstellen
    gdb_ws_name = collection_id + '.gdb'
    if arcpy.Exists(workspace_gdb+"\\"+gdb_ws_name+"\\" + mosaic_product_name):
        print mosaic_product_name + " Exists, continue with Checking Service Definition"
    else:
        arcpy.CreateMosaicDataset_management(workspace_gdb+"\\"+gdb_ws_name, mosaic_product_name, "PROJCS['ETRS_1989_UTM_Zone_32N', "
                                                                                                              "GEOGCS['GCS_ETRS_1989',DATUM['D_ETRS_1989',SPHEROID['GRS_1980',6378137.0,298.257222101]],"
                                                                                                              "PRIMEM['Greenwich',0.0],UNIT['Degree',0.0174532925199433]],PROJECTION['Transverse_Mercator'],"
                                                                                                              "PARAMETER['False_Easting',500000.0],PARAMETER['False_Northing',0.0],"
                                                                                                              "PARAMETER['Central_Meridian',9.0],"
                                                                                                              "PARAMETER['Scale_Factor',0.9996],PARAMETER['Latitude_Of_Origin',0.0],"
                                                                                                              "UNIT['Meter',1.0]];-5120900 -9998100 10000;-100000 10000;-100000 10000;0,001;0,001;0,001;"
                                                                                                              "IsHighPrecision",pixel_type=product_pixel_type)
        print "Created Mosaic for " + gdb_ws_name + " with " + mosaic_product_name
        # Raster zum Mosaik hinzufuegen
        arcpy.AddRastersToMosaicDataset_management(workspace_gdb+"\\"+gdb_ws_name + '\\' + mosaic_product_name, "Raster Dataset", product_result,
                                                           "UPDATE_CELL_SIZES", "UPDATE_BOUNDARY", "UPDATE_OVERVIEWS", "0", "1500", "#", "", "#", "SUBFOLDERS",
                                                           "EXCLUDE_DUPLICATES", "BUILD_PYRAMIDS", "CALCULATE_STATISTICS", "NO_THUMBNAILS", "", "NO_FORCE_SPATIAL_REFERENCE", "ESTIMATE_STATISTICS", "")
        print "Added Raster to Mosaic"
        # Process: Raster zu Mosaik-Dataset hinzufuegen (add all belonging rasters to the Master Mosaic)
        arcpy.AddRastersToMosaicDataset_management(workspace_gdb+"\\"+gdb_ws_name + '\\' + "Master" + '_' + collection_id, "Raster Dataset",
                                                           workspace_gdb + "\\" + gdb_ws_name + "\\" + mosaic_product_name,
                                                           "UPDATE_CELL_SIZES", "UPDATE_BOUNDARY", "NO_OVERVIEWS", "0", "1500", "#", "", "#", "NO_SUBFOLDERS", "EXCLUDE_DUPLICATES",
                                                           "NO_PYRAMIDS", "CALCULATE_STATISTICS", "BUILD_THUMBNAILS", "", "NO_FORCE_SPATIAL_REFERENCE", "ESTIMATE_STATISTICS", "")
        # Add Rendering Function to Raster Dataset probably depending wether a rtf file has been build or not
        # arcpy.EditRasterFunction_management(workspace_gdb+"\\"+gdb_ws_name + '\\' + "Master" + '_' + collection_id, "EDIT_MOSAIC_DATASET",
        #                                    "INSERT", "C:/WaCoDiS/raster_functions/Oberflaechentemperatur.rft.xml", "Rendering Function")
        print "Added Raster to MasterMosaic"

        cursor = arcpy.da.UpdateCursor(workspace_gdb+"\\"+gdb_ws_name + '\\' + 'Master' + "_" + collection_id, ['NAME','startTime'])
        for row in cursor:
            if(row[0] == mosaic_product_name):
                row[1] = startTimefield
            cursor.updateRow(row)
        del row
        del cursor
        cursorET = arcpy.da.UpdateCursor(workspace_gdb+"\\"+gdb_ws_name + '\\' + 'Master' + "_" + collection_id, ['NAME','endTime'])
        for row in cursorET:
            if(row[0] == mosaic_product_name):
                row[1] = endTimefield
            cursorET.updateRow(row)
        del row
        del cursorET
        print "Calculated Fields for " + collection_id
                    # To DO mark processed datasets and save to another directory
                    # os.rename(os.path.join(product_results_path,prod_name), os.path.join(processed_prod_path, prod_name))
except arcpy.ExecuteError:
    e = sys.exc_info()[1]
    print(e.args[0])
    print arcpy.GetMessages() + "\n\n"
    sys.exit("Failed in authoring mosaic datasets and calculating fields")


try:
    #Analyze Mosaic Dataset
    print "Analyzing Mosaic Dataset"
    arcpy.AnalyzeMosaicDataset_management(workspace_gdb+"\\"+collection_id+".gdb\\"+mosaic_product_name)
    arcpy.AnalyzeMosaicDataset_management(workspace_gdb+"\\"+collection_id+".gdb\\"+'Master' + "_" + collection_id)
except arcpy.ExecuteError:
    e = sys.exc_info()[1]
    print (e.args[0])
    print arcpy.GetMessages() + "\n\n"
    sys.exit("Errors in analyzing Mosaic Dataset")

# Create an ArcGIS Server connection if not already established
try:
    if not arcpy.Exists(out_folder_path+"\\"+out_name):
        print "Creating Server Connection File"
        arcpy.mapping.CreateGISServerConnectionFile("PUBLISH_GIS_SERVICES",
                                            out_folder_path,
                                            out_name,
                                            server_url,
                                            "ARCGIS_SERVER",
                                            use_arcgis_desktop_staging_folder,
                                            None,
                                            username,
                                            password,
                                            "SAVE_USERNAME")
    else:
        print "Server connection already established."
except arcpy.ExecuteError:
    e = sys.exc_info()[1]
    print(e.args[0])
    print arcpy.GetMessages() + "\n\n"
    sys.exit("Failed establishing server connection")

# If Image Service does not exist create Service drafts to publih the service
# Otherwise add new raster to existing Image Service

# When Image Service does not exist yet create a service definition draft and publish the Service
if not os.path.exists(workspace_gdb+"\\"+collection_id+ "Service.sd"):
    try:
        print "Try Creating SD draft"
        if data_store_path not in [i[2] for i in arcpy.ListDataStoreItems(con, 'FOLDER')]:
            # Register folder with ArcGIS Server site --> both the server path(out_folder_path 1.) and client path (out_folder_path 2.) are the same
            dsStatus = arcpy.AddDataStoreItem(con, "FOLDER", "Workspace for " + collection_id + 'Service', data_store_path, data_store_path)
            print "Data store : " + str(dsStatus)
        Sddraft = os.path.join(workspace_gdb, collection_id+"Service"+".sddraft")  # Name = Name der Bilddateien/ Ordner bzw. des sddraft
        # vorletzter Parameter der createImageSdd Draft Funktion muss nachher mit den Metadaten besetzt werden, als description des Services
        arcpy.CreateImageSDDraft(os.path.join(workspace_gdb, collection_id+'.gdb\\Master_'+collection_id), Sddraft, collection_id+"Service", 'ARCGIS_SERVER', None, False, 'WaCoDiS',
                                 str(json_metadata['productType']),
                                 str(json_metadata['productType'])+",image service, WaCoDiS")
    except arcpy.ExecuteError:
        e = sys.exc_info()[1]
        print(e.args[0])
        print arcpy.GetMessages() + "\n\n"
        sys.exit("Failed in creating SD draft")

    # Analyze the service definition draft
    Sddraft = os.path.join(workspace_gdb, collection_id+"Service"+".sddraft")
    Sd = os.path.join(workspace_gdb, collection_id+"Service"+".sd")
    analysis = arcpy.mapping.AnalyzeForSD(Sddraft)
    print "The following information was returned during analysis of the image service:"
    for key in ('messages', 'warnings', 'errors'):
        print '----' + key.upper() + '---'
        vars = analysis[key]
        for ((message, code), layerlist) in vars.iteritems():
            print '    ', message, ' (CODE %i)' % code
            print '       applies to:',
            for layer in layerlist:
                print layer.name,
            print
                # Stage and upload the service if the sddraft analysis did not contain errors
    if analysis['errors'] == {}:
        try:
            print "Staging service to create service definition"
            arcpy.StageService_server(Sddraft, Sd)

            print "Uploading the service definition and publishing image service"
            arcpy.UploadServiceDefinition_server(Sd, con)

            print "Service successfully published"
        except arcpy.ExecuteError:
            e = sys.exc_info()[1]
            print(e.args[0])
            print arcpy.GetMessages() + "\n\n"
            sys.exit("Failed to stage and upload service")
    else:
        print "Service could not be published because errors were found during analysis."
        print arcpy.GetMessages()
# if Image Service already exists Refresh Service
else:
    try:
        print collection_id + " Image Service exists, Update Service"
        tbx = arcpy.ImportToolbox(out_folder_path+"\\"+ out_name +";System/PublishingTools")
        tbx.RefreshService(collection_id+"Service","ImageServer",workspace_gdb,"#")
    except arcpy.ExecuteError:
        e = sys.exc_info()[1]
        print(e.args[0])
        print arcpy.GetMessages() + "\n\n"
        sys.exit("Failed in Refreshing Service")