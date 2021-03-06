from bokeh.models.sources import ColumnDataSource
import requests, json
from geopy.geocoders import GoogleV3
import pprint

from bokeh.io import show
from bokeh.plotting import gmap
from bokeh.plotting import output_file, save
from bokeh.resources import CDN
from bokeh.embed import file_html
from selenium.common.exceptions import NoSuchElementException, TimeoutException

from bokeh.models import GMapOptions, HoverTool

from googleapiclient.discovery import build
from google.oauth2 import service_account
from googleapiclient.http import MediaFileUpload

#*******************************************************
GOOGLE_MAP_API_KEY = "GMAPS_API_KEY"
geolocator = GoogleV3(api_key=GOOGLE_MAP_API_KEY)
pp = pprint.PrettyPrinter(indent=4)
SCOPES = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
SERVICE_ACCOUNT_FILE = 'aggronkey.json'
creds = None
creds = service_account.Credentials.from_service_account_file(
    SERVICE_ACCOUNT_FILE, scopes=SCOPES)
drive_service = build('drive', 'v3', credentials = creds)
#*******************************************************

def getPoints(address):
    # ONLY GEOCODING
    if address != '':
        try:
            location = geolocator.geocode(address, timeout=10)
        except TimeoutException:
            lat = 25
            long = 25
        if location is None:
            # When Google fails to detect a location
            lat = 25
            long = 25
        else:
            lat = location.latitude
            long = location.longitude
    else:
        # For takeaway orders, where address is ""
        lat = 
        long = 
    return lat, long

def plot_map(restaurant, startDate, masterListofOrders = {}):
    gmap_options = GMapOptions(lat = restaurant["latitude"], lng = restaurant["longitude"], map_type = 'roadmap', zoom = 12)
    hover = HoverTool(
        tooltips = [
            ('Name', '@names'),
            ('Address', '@addresses'), 
            ('Bill', 'AED @billAmounts'), 
        ]
    )
    p = gmap(
        GOOGLE_MAP_API_KEY, gmap_options, 
        # title = restaurant["name"] + " Orders Map", 
        width = 600, 
        height = 600,
        tools=[hover, 'reset', 'wheel_zoom', 'pan'])
    if masterListofOrders != {}:
        colormap = {'Zomato': 'red', 'CareemNOW': 'green', 'Smiles': 'blue', 'Talabat': 'orange', 'Deliveroo': 'cyan', 'Noon Food' : 'yellow'}
        plotData = {
            "latitudes" : [order["latitude"] for order in masterListofOrders.values()],
            "longitudes" : [order["longitude"] for order in masterListofOrders.values()],
            "names" : [order["customerName"] for order in masterListofOrders.values()],
            "addresses" : [order["customerAddress"] for order in masterListofOrders.values()],
            "billAmounts" : ["{:6.2f}".format(order["billAmount"]) for order in masterListofOrders.values()],
            "radius": [200 * order['billAmount']/restaurant["cost_for_two"] for order in masterListofOrders.values()],
            "colors": [colormap[order['platform']] for order in masterListofOrders.values()],
            "platform": [order["platform"] for order in masterListofOrders.values()]
        }
        source = ColumnDataSource(plotData)
        p.circle('longitudes', 'latitudes', radius='radius', alpha=0.2, color='colors', legend='platform', source=source)
        p.legend.location = "top_left"
    # RESTAURANT MARKER
    p.square_cross([restaurant["longitude"]], [restaurant["latitude"]], size=10, alpha=1, color='black')
    filename = restaurant["name"] + "-"+ startDate.strftime("%b-%Y") + ".html"
    output_file(filename)
    save(p)
    folder_id = restaurant['folder']
    # Call the Drive API
    file_metadata = {
        'name': filename,
        'parents': [folder_id]
    }
    media = MediaFileUpload(filename,
                            mimetype='text/html',
                            resumable=True)
    file = drive_service.files().create(body=file_metadata,
                                        media_body=media,
                                        fields='id').execute()
    file_id = file.get('id')
    drive_service.permissions().create(
        body={
            "role":"reader", 
            "type":"user", 
            "emailAddress": restaurant["email"]
        }, 
        fileId=file_id,
        sendNotificationEmail=False
    ).execute()
