#This script retrieves the latest IP subnets of AWS, Google and Genesys Cloud in the chosen Region once a day
#It then compares the results with the previous day's run and gets any IP's added and IP's deleted

#!/usr/bin/env python
from numpy import outer
import requests
import json
import pandas as pd
import shutil
import PureCloudPlatformClientV2
from PureCloudPlatformClientV2.rest import ApiException

#Define Functions to get difference between two sets of IP's in Dataframes
#df1 will be the Dataframe holding Latest IP's, df2 will be Dataframe holding Previous IPs
#Solution is to merge the two Dataframes as an Outer Merge, and supply and Indicator column
#If a data row is present in both df1 and df2, the 'indicator' value will be 'both'
#If a data row is present in df1 but not in df2, the 'indicator' value will be 'right_only'. These are new IP's that have been added.
#If a data row is present in df2 but not in df1, the 'indicator' value will be 'left_only'. These are IP's that have been deleted.

def get_ips_added (df1,df2):
    df_merged = pd.merge(df1, df2, how="outer", indicator="Exist")
    diff1 = df_merged.query("Exist == 'right_only'")
    diff1 = diff1.drop(columns="Exist")
    return diff1

def get_ips_deleted (df1,df2):
    df_merged = pd.merge(df1, df2, how="outer", indicator="Exist")
    diff2 = df_merged.query("Exist == 'left_only'")
    diff2 = diff2.drop(columns="Exist")
    return diff2

#Read the config file for AWS Region
config_file = open('ip_diff_config.json')
config_data = json.load(config_file)
config_region = config_data["aws_region"]
config_gcregion = config_data["genesys_cloud_region"]
config_client_id = config_data["oauth2_client_id"]
config_client_secret = config_data["oauth2_client_secret"]
config_latest_ips_file = config_data["latest_ip_filename"]
config_previous_ips_file = config_data["previous_ip_filename"]
config_added_ips_file = config_data["ips_added_filename"]
config_deleted_ips_file = config_data["ips_deleted_filename"]
config_client_id = config_data["oauth2_client_id"]
config_client_secret = config_data["oauth2_client_secret"]

#Setup Genesys Cloud API Environment using OAuth credentials
region = PureCloudPlatformClientV2.PureCloudRegionHosts[config_gcregion]
PureCloudPlatformClientV2.configuration.host = region.get_api_host()

#Retrieve Client Credentials
api_client = PureCloudPlatformClientV2.api_client.ApiClient().get_client_credentials_token(config_client_id, config_client_secret)

#Initialise Utilites API Instance
utilities_api_instance = PureCloudPlatformClientV2.UtilitiesApi(api_client)

#Read JSON files of AWS and Google and get the IP Prefixes
ip_ranges_aws = requests.get('https://ip-ranges.amazonaws.com/ip-ranges.json').json()['prefixes']
ip_ranges_google = requests.get('https://www.gstatic.com/ipranges/goog.json').json()['prefixes']

#Retrieve the AWS Region and Service specific IP's, Google IPs
cloudfront_ips = [item['ip_prefix'] for item in ip_ranges_aws if item["service"] == "CLOUDFRONT" and item["region"] == config_region]
ec2_ips = [item['ip_prefix'] for item in ip_ranges_aws if item["service"] == "EC2" and item["region"] == config_region]
s3_ips = [item['ip_prefix'] for item in ip_ranges_aws if item["service"] == "S3" and item["region"] == config_region]
api_gw_ips = [item['ip_prefix'] for item in ip_ranges_aws if item["service"] == "API_GATEWAY" and item["region"] == config_region]
route53_ips = [item['ip_prefix'] for item in ip_ranges_aws if item["service"] == "ROUTE53"]
global_acc_ips = [item['ip_prefix'] for item in ip_ranges_aws if item["service"] == "GLOBALACCELERATOR" and item["region"] == config_region]
google_ips = [item['ipv4Prefix'] for item in ip_ranges_google if "ipv4Prefix" in item]

#Retrieve the Genesys Cloud CIDR ranges
gc_ip_ranges_obj = utilities_api_instance.get_ipranges().entities
#Create an empty List object for the Genesys Cloud IPs and extract the Genesys Cloud CIDR ranges
gc_ip_ranges = []
for i in range(len(gc_ip_ranges_obj)):
    gc_ip_ranges += [gc_ip_ranges_obj[i].cidr]

#Create Pandas dataframes with each set of IP's
df_cloudfront_ips = pd.DataFrame(cloudfront_ips)
df_ec2_ips = pd.DataFrame(ec2_ips)
df_s3_ips = pd.DataFrame(s3_ips)
df_api_gw_ips = pd.DataFrame(api_gw_ips)
df_route53_ips = pd.DataFrame(route53_ips)
df_global_acc_ips = pd.DataFrame(global_acc_ips)
df_google_ips = pd.DataFrame(google_ips)
df_gc_ip_ranges = pd.DataFrame(gc_ip_ranges)

#Write the IP's into a multi-tab Excel file, don't print the Index rows and columns
with pd.ExcelWriter(config_latest_ips_file) as Cloud_IPs:
    df_cloudfront_ips.to_excel(Cloud_IPs, sheet_name="CloudFront", index=False)
    df_ec2_ips.to_excel(Cloud_IPs,sheet_name="EC2", index=False)
    df_s3_ips.to_excel(Cloud_IPs, sheet_name="S3", index=False)
    df_api_gw_ips.to_excel(Cloud_IPs, sheet_name="API Gateway", index=False)
    df_route53_ips.to_excel(Cloud_IPs, sheet_name="Route 53", index=False)
    df_global_acc_ips.to_excel(Cloud_IPs, sheet_name="GlobalAccelerator", index=False)
    df_google_ips.to_excel(Cloud_IPs, sheet_name="Google", index=False)
    df_gc_ip_ranges.to_excel(Cloud_IPs, sheet_name="Genesys Cloud", index=False)

#Import the Latest IPs file and Previous IPs files into two separate Dataframes
df_Prev_CloudFront_IPs = pd.read_excel(config_previous_ips_file, sheet_name="CloudFront")
df_Prev_ec2_IPs = pd.read_excel(config_previous_ips_file, sheet_name="EC2")
df_Prev_S3_IPs = pd.read_excel(config_previous_ips_file, sheet_name="S3")
df_Prev_API_GW_IPs = pd.read_excel(config_previous_ips_file, sheet_name="API Gateway")
df_Prev_Route53_IPs = pd.read_excel(config_previous_ips_file, sheet_name="Route 53")
df_Prev_Global_Acc_IPs = pd.read_excel(config_previous_ips_file, sheet_name="GlobalAccelerator")
df_Prev_Google_IPs = pd.read_excel(config_previous_ips_file, sheet_name="Google")
df_Prev_GC_IPs = pd.read_excel(config_previous_ips_file, sheet_name="Genesys Cloud")

#Compare and find the IP's added per Service for AWS and Google
cloudfront_ips_added = get_ips_added(df_cloudfront_ips,df_Prev_CloudFront_IPs)
ec2_ips_added = get_ips_added(df_ec2_ips,df_Prev_ec2_IPs)
s3_ips_added = get_ips_added(df_s3_ips,df_Prev_S3_IPs)
api_gw_ips_added = get_ips_added(df_api_gw_ips,df_Prev_API_GW_IPs)
route53_ips_added = get_ips_added(df_route53_ips,df_Prev_Route53_IPs)
global_acc_ips_added = get_ips_added(df_global_acc_ips,df_Prev_Global_Acc_IPs)
google_ips_added = get_ips_added(df_google_ips,df_Prev_Google_IPs)
gc_ips_added = get_ips_added(df_gc_ip_ranges,df_Prev_GC_IPs)

#Write the New IP's added into a multi-tab Excel file, don't print the Index rows and columns
with pd.ExcelWriter(config_added_ips_file) as Cloud_Diff:
    cloudfront_ips_added.to_excel(Cloud_Diff, sheet_name="CloudFront",index=False)
    ec2_ips_added.to_excel(Cloud_Diff, sheet_name="EC2",index=False)
    s3_ips_added.to_excel(Cloud_Diff, sheet_name="S3")
    api_gw_ips_added.to_excel(Cloud_Diff, sheet_name="API Gateway")
    route53_ips_added.to_excel(Cloud_Diff, sheet_name="Route 53")
    global_acc_ips_added.to_excel(Cloud_Diff, sheet_name="GlobalAccelerator")
    google_ips_added.to_excel(Cloud_Diff, sheet_name="Google")
    gc_ips_added.to_excel(Cloud_Diff, sheet_name="Genesys Cloud")

#Compare and find the IP's deleted per Service for AWS and Google
cloudfront_ips_deleted = get_ips_deleted(df_cloudfront_ips,df_Prev_CloudFront_IPs)
ec2_ips_deleted = get_ips_deleted(df_ec2_ips,df_Prev_ec2_IPs)
s3_ips_deleted = get_ips_deleted(df_s3_ips,df_Prev_S3_IPs)
api_gw_ips_deleted = get_ips_deleted(df_api_gw_ips,df_Prev_API_GW_IPs)
route53_ips_deleted = get_ips_deleted(df_route53_ips,df_Prev_Route53_IPs)
global_acc_ips_deleted = get_ips_deleted(df_global_acc_ips,df_Prev_Global_Acc_IPs)
google_ips_deleted = get_ips_deleted(df_google_ips,df_Prev_Google_IPs)
gc_ips_deleted = get_ips_deleted(df_gc_ip_ranges,df_Prev_GC_IPs)

#Write the Deleted IP's into a multi-tab Excel file, don't print the Index rows and columns
with pd.ExcelWriter(config_deleted_ips_file) as Cloud_Del:
    cloudfront_ips_deleted.to_excel(Cloud_Del, sheet_name="CloudFront", index=False)
    ec2_ips_deleted.to_excel(Cloud_Del, sheet_name="EC2", index=False)
    s3_ips_deleted.to_excel(Cloud_Del, sheet_name="S3", index=False)
    api_gw_ips_deleted.to_excel(Cloud_Del, sheet_name="Route 53", index=False)
    global_acc_ips_deleted.to_excel(Cloud_Del, sheet_name="GlobalAccelerator", index=False)
    google_ips_deleted.to_excel(Cloud_Del, sheet_name="Google", index=False)
    gc_ips_deleted.to_excel(Cloud_Del, sheet_name="Genesys Cloud")

#Copy Latest IP's to Previous IP's. This allows for the script to be run next day.
shutil.copy2(config_latest_ips_file, config_previous_ips_file)