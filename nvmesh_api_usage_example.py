#!/usr/bin/python
# To make this excample tool work, you need to install the Requests Python package on the client/machine where you
# intend to use it. The download information and instructions on how install the requests package can be found here:
# http://docs.python-requests.org/en/master/user/install/#install

# Importing the required packages
import requests
import json
import argparse
import os
import re
import random

# As per default NVMesh uses self-signed certificates, this is to disable the related insecure connection warnings.
requests.packages.urllib3.disable_warnings()

# This is the default username and password intended for the use with the API set during the installation of the product
# automatically. If this was changed after the installation, you have to call this tool with the -u and -p option to
# set the correct credentials, username and/or password.
username = "app@excelero.com"
password = "admin"
management_server = None
management_server_port = "4000"
api_protocol = None
NVMESH_CONFIG_FILE = "/etc/opt/NVMesh/nvmesh.conf"

# Here are the regular expressions require to read the protocol and server information out of the nvmesh.conf file.
# These regex assume a working nvmesh.conf file using valid IP adresses
REGEX_MANAGEMENT_PROTOCOL = r'^MANAGEMENT_PROTOCOL="([A-Za-z]*)'
REGEX_MANAGEMENT_SERVER_INFO = r'^MANAGEMENT_SERVERS="([A-Za-z0-9-.]*)'

# Parsing the options and information required to establish a session with the API and to greate a session. If there is
# a valid nvmesh.conf on the client/machine where you intend to use this tool, you don't have to provide the management
# server IP an port information, we will read this right out of the nvmesh.conf.
parser = argparse.ArgumentParser()
parser.add_argument("-u", "--user", default=None, help="Allows you to use a different than the default username"
                    , required=False)
parser.add_argument("-p", "--password", default=None, help="Allows you to use a different than the default password"
                    , required=False)
parser.add_argument('-s', '--management-server', default=None, help="If there is no valid nvmesh.conf on this "
                                                                    "machine, you must provide a valid "
                                                                    "NVMesh Manager IP address.", required=False)
parser.add_argument('-a', '--api-protocol', default="https", help="If there is no valid nvmesh.conf on this "
                                                                  "machine, you must provide the protocol being "
                                                                  "used by the API, http or https."
                    , required=False)
args = parser.parse_args()
# If a username was provided via the command line, we will use this username and overwrite the default setting.
if getattr(args, "user") is not None:
    username = getattr(args, "user")

# If a password  was provided via the command line, we will use this password and overwrite the default setting.
# Please note that the via the command line provided credential will not be stored persistently and will live  in the
# memory only for as log the tool/script runs. The same applies to the API session we will create
# later on in the script.
if getattr(args, "password") is not None:
    username = getattr(args, "password")

if getattr(args, "management_server") is not None:
    management_server = getattr(args, "management_server_ip")

if getattr(args, "api_protocol") is not None:
    api_protocol = getattr(args, "api_protocol")

# In case that no API server information was passed on via command line or is partially missing.
# Trying to read the management server/API ip and and port information out of the nvmesh.conf file.
# First step is to verify that the file actually exists and if it exists.
if os.path.exists(NVMESH_CONFIG_FILE):
    nvmesh_conf = open(NVMESH_CONFIG_FILE, "r").read()
    if api_protocol is None:
        api_protocol = re.findall(REGEX_MANAGEMENT_PROTOCOL, nvmesh_conf, re.MULTILINE)[0]
    if management_server is None:
        management_server = re.findall(REGEX_MANAGEMENT_SERVER_INFO, nvmesh_conf, re.MULTILINE)[0]

# Creating an API session
api_session = requests.session()
api_root = "%s://%s:%s" % (api_protocol, management_server, management_server_port)
try:
    api_session.post(api_root + "/login", params={"username": username, "password": password}, verify=False)
except requests.ConnectionError as ex:
    print "Cannot connect to Server ", api_root, ex.message

print "Here is details of the API session cookie which was just obtained\n", api_session.cookies

# As an example, get the API version
print "\nAPI version\n", api_session.get(api_root + "/version").json()

# As an example, list all the drive types/models available in the cluster
print "\nAvailable drive types/models\n", json.dumps(api_session.get(api_root + "/disks/models/").json(), indent=4)

# As an example, create a random dummy test user
print "\nCreating a dummy user with a very random name"
random_user = "user_" + random.randrange(0, 1000000000001, 2).__str__() + "@excelero.com"
user_payload = [{
    "email": random_user,
    "role": "Observer",
    "notificationLevel": "NONE",
    "password": "bla",
    "confirmationPassword": "blub",
    "relogin": "true"
}]
print api_session.post(api_root + "/users/save", json=user_payload, )

# As an example, list all users
print "\nAll users in the system\n", json.dumps(api_session.get(api_root + "/users/all").json(), indent=4)

# An an example, lets  create a volume with a random volume name/id. Please note that the capacity is in bytes
random_volume_name = "volume_" + random.randrange(0, 1000000000001, 2).__str__()
volume_payload = {"create":
                      [{"RAIDLevel": "Striped RAID-0",
                        "capacity": 14293651161088,
                        "diskClasses": [],
                        "limitByDisks": [],
                        "limitByNodes":
                            ["uslab-31.uslab.excelero.com",
                             "uslab-32.uslab.excelero.com"],
                        "name": "%s" % random_volume_name,
                        "serverClasses": [],
                        "stripeSize": 32,
                        "stripeWidth": 12}],
                  "edit": [],
                  "remove": []}
print "\n Creating a volume\n", json.dumps(api_session.post(api_root + "/volumes/save", json=volume_payload).json()
                                           , indent=4)

# As an example how to iterate through the API JSON output programmatically, herean example servers to create drive
# classes based on the target server host name name and the installed drives

# Loading json data containing all the target server information
json_servers = json.loads(json.dumps(api_session.get(api_root + "/servers/all/0/0?filter={}&sort={}").json()))

# Creating an empty list of target classes
disk_classes_list = []

# iterating through the list of the available target servers
for server in json_servers:
    disk_classes_dict = {}
    server_name = str(server["_id"])

    # Loading json data containing all the available drive types/models
    json_disk_models = json.loads(json.dumps(api_session.get(api_root + "/disks/models").json()))

    # Creating an empty list to store the disk information by drive type
    disks_by_model_list = []

    # Iterating thorugh the list of available drive types/models
    for model_item in json_disk_models:

        # Creating an empty dictionary to store the required disk information
        disks_by_model_dict = {}

        # Creating an empty to list to store the disk details dictionaries generated later on
        disks_list = []
        disk_model = str(model_item["_id"])

        # Loading the json data containing the disk details which is required
        json_disk_details = json.loads(
            json.dumps(api_session.get(api_root + "/disks/disksByModel/" + disk_model).json()))

        # Iterating throught the list of the disks
        for disk_item in json_disk_details:

            # If the servername/target matches, the detailed dictionary  data is populated
            if server_name in str(disk_item["node_id"]):
                disks_dict = {"diskID": str(disk_item["disks"]["diskID"]), "node_id": str(disk_item["node_id"])}

                # populating the list with the detail dictionaries
                disks_list.append(disks_dict)

            # defining the model/type key/property and adding all the individual drive/disk information
            disks_by_model_dict["model"] = disk_model
            disks_by_model_dict["disks"] = disks_list

        # populating the list with the list ordered by ssd/drive type
        disks_by_model_list.append(disks_by_model_dict)

    # defining the drive/disk class id and adding all the disk information to it
    disk_classes_dict["_id"] = server_name.split(".")[0]
    disk_classes_dict["disks"] = disks_by_model_list

    # populating the list containing all the drive/disk classes and preparing it to post it
    disk_classes_list.append(disk_classes_dict)

# printing/dumping the list of drive/disk classes on the screen
print json.dumps(disk_classes_list, indent=4)

# post the required information to the server/api and print out the return code. Return code "null" means all good
print json.dumps(api_session.post(api_root + "/diskClasses/save", json=json.loads(json.dumps(disk_classes_list)), )
                 .json())
