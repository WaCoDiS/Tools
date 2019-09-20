# -*- coding: utf-8 -*-
# ---------------------------------------------------------------------------
# Mosaik_Skript.py
# Created on: 2019-07-09 10:47:30.00000
#
# Usage: Mosaik_Skript <File_GDB_Name> 
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
# Following variables are defined throughout the console:
# product_results ("Connection to Folder containing TIF DataResultProducts") MUST BE DEFINED
# collection-id  Id of processed Dataproduct
# ---------------------------------------------------------------------------
import argparse

parser = argparse.ArgumentParser(description='Crate a mosaic dataset from an EO product image and publish it as an ArcGIS Image Service.')
parser.add_argument('image', metavar='<IMAGE>', type=str, help='the path to an EO product image that will be processed')
parser.add_argument('collection', metavar='<COLLECTION>', type=str, help='a collection id relating to the service the EO product image will be published')

args = parser.parse_args()

# Set the necessary product code
import arceditor

# Import modules
import arcpy
import sys
import os
import fnmatch

# arcpy.env.overwriteOutput = True

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
col_id = args.collection
collection_id = col_id.replace(":", "_")


try:
    product_path = product_result.split('\\')
    product_name = product_path[len(product_path)-1]
    if arcpy.Exists(workspace_gdb+"\\"+collection_id+".gdb"):
        print "GDB " + collection_id + " exists"
        # Do nothing
    else:
        arcpy.CreateFileGDB_management(workspace_gdb, collection_id+".gdb")
        # Create Master Mosaic
        # Process: Mosaik-Dataset erstellen
        arcpy.CreateMosaicDataset_management(workspace_gdb+"\\" + collection_id + '.gdb', "Master" + '_' + collection_id,
                                                 "PROJCS['ETRS_1989_UTM_Zone_32N',GEOGCS['GCS_ETRS_1989',DATUM['D_ETRS_1989',SPHEROID['GRS_1980',6378137.0,298.257222101]],"
                                                 "PRIMEM['Greenwich',0.0],UNIT['Degree',0.0174532925199433]],PROJECTION['Transverse_Mercator'],PARAMETER['False_Easting',500000.0],"
                                                 "PARAMETER['False_Northing',0.0],PARAMETER['Central_Meridian',9.0],PARAMETER['Scale_Factor',0.9996],PARAMETER['Latitude_Of_Origin',0.0],"
                                                 "UNIT['Meter',1.0]];-5120900 -9998100 10000;-100000 10000;-100000 10000;0,001;0,001;0,001;IsHighPrecision",pixel_type="8_BIT_UNSIGNED")
        print "Created Master Mosaic for " + collection_id
        arcpy.AddField_management(workspace_gdb+"\\"+collection_id + '.gdb\\' + 'Master' + "_" + collection_id, "year_quat", "text")
        print "Added field"
        arcpy.SetMosaicDatasetProperties_management(
                workspace_gdb+"\\" + collection_id + '.gdb\\' "Master" + '_' + collection_id,
                use_time="ENABLED", start_time_field="year_quat", end_time_field="year_quat",
                time_format="YYYYMMDD", time_interval_units="Months")
        print "Mosaic Properties were set"
except arcpy.ExecuteError:
    e = sys.exc_info()[1]
    print(e.args[0])
    print arcpy.GetMessages() + "\n\n"
    sys.exit("Failed in creating GDB and MasterMosaic")

codeblock = """
def getYearQuat(date,dat):
    switcher = {
            "Fruehling": '-03',
            "Sommer": '-06',
            "Herbst": '-09',
            "Winter": '-12',
            }
    return date + switcher.get(dat, "")
    """

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
                                                                                                              "IsHighPrecision",pixel_type="8_BIT_UNSIGNED")
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
        # arcpy.EditRasterFunction_management(workspace_gdb+"\\"+gdb_ws_name + '\\' + "Master" + '_' + gdb_name, "EDIT_MOSAIC_DATASET",
        #                                    "INSERT", "C:/workspace/hillshade.rft.xml", "Rendering Function")
        print "Added Raster to MasterMosaic"
        arcpy.CalculateField_management(workspace_gdb+"\\"+gdb_ws_name + '\\' + 'Master' + "_" + collection_id, "year_quat",
                                        "getYearQuat(!NAME!.split('_')[1],!NAME!.split('_')[1])",
                                        "PYTHON", codeblock)
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

# If Image Service does not Exist create server Connection and Service drafts to publih the service
# Otherwise add new raster to existing Image Service

# When Image Service does not exist yet create a service definition draft and publish the Service
if not os.path.exists(workspace_gdb+"\\"+collection_id+ "Service.sd"):
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
        print "Try Creating SD draft"
        if data_store_path not in [i[2] for i in arcpy.ListDataStoreItems(con, 'FOLDER')]:
            # Register folder with ArcGIS Server site --> both the server path(out_folder_path 1.) and client path (out_folder_path 2.) are the same
            dsStatus = arcpy.AddDataStoreItem(con, "FOLDER", "Workspace for " + collection_id + 'Service', data_store_path, data_store_path)
            print "Data store : " + str(dsStatus)
        Sddraft = os.path.join(workspace_gdb, collection_id+"Service"+".sddraft")  # Name = Name der Bilddateien/ Ordner bzw. des sddraft
        arcpy.CreateImageSDDraft(os.path.join(workspace_gdb, collection_id+'.gdb\\Master_'+collection_id), Sddraft, collection_id+"Service", 'ARCGIS_SERVER', None, False, 'WaCoDiS', collection_id, collection_id+",image service, WaCoDiS")
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