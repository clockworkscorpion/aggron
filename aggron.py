from mapper import plot_map
from googleapiclient.discovery import build
from google.oauth2 import service_account
import json
import time
from time import time
from datetime import datetime, date, timedelta
from operator import itemgetter
import pprint
import copy

from zomato import zomatoBuilder
from eateasy import eateasyBuilder

#***********************************************************************************************************
SCOPES = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/script.projects']
SERVICE_ACCOUNT_FILE = 'aggronkey.json'
creds = None
creds = service_account.Credentials.from_service_account_file(
    SERVICE_ACCOUNT_FILE, scopes=SCOPES)
service = build('sheets', 'v4', credentials = creds)
sheet = service.spreadsheets()

clientsFile = 'aggron-restaurants.json'
f = open(clientsFile,"r")
TEMPLATE_SHEET_ID = "XXXXXXXXXXXXXX"
pp = pprint.PrettyPrinter(indent=4)
# *********************************************************************************************************

def getCustomerData(ListofOrders, startDate):
    unique_customers = {}
    UNIQUE_CUSTOMERS = []
    for order in ListofOrders.values():
        key = order['platform']+order['customerName'] if len(order['customerPhone']) <= 7 else order['platform']+order['customerPhone']
        if key not in unique_customers.keys():
            # New Customer Added
            # print("New Customer")            
            unique_customers[key] = {
                "name": order['customerName'],
                "phone": order['customerPhone'],
                "address": order['customerAddress'],
                "times": 1,
                "value": float(order['billAmount']),
                "items": order['orderItems'],
                "platform": order['platform']
            }
        else:
            # Old Customer Updated
            address = unique_customers[key]["address"] if len(order['customerAddress']) <= 20 else order['customerAddress']
            #default to non-null address
            for item, itemData in order['orderItems'].items():
                if item not in unique_customers[key]['items'].keys():
                    # print("Old Customer - New Item")
                    unique_customers[key]['items'][item] = itemData
                else:
                    # print("Old Customer - Old Item")
                    unique_customers[key]['items'][item]["quantity"] += itemData["quantity"]
                    unique_customers[key]['items'][item]["billed"] += itemData["billed"]

            unique_customers[key].update({
                "address": address,
                "times": (unique_customers[key]["times"] + 1),
                "value": float(unique_customers[key]["value"]) + float(order['billAmount']),
            })
    print(unique_customers)
    for customer in unique_customers.values():
        itemString = ''
        for itemName, item in customer["items"].items():        
            itemString = itemString + str(itemName + " (" + str(item["quantity"]) + "), ")
        UNIQUE_CUSTOMERS.append([
            customer["phone"], 
            customer["name"], 
            customer["address"],
            startDate.strftime("%d/%b/%Y"),
            customer["times"], 
            customer["value"], 
            itemString,
            customer['platform']
        ])

    return unique_customers, UNIQUE_CUSTOMERS

def getItemData(ListofOrders, startDate):
    items_map = {}
    ITEMS_LIST = []
    for order in ListofOrders.values():
        for item, itemData in order["orderItems"].items():
            key = item + order['platform']
            if key not in items_map.keys():
                # New Item
                items_map[key] = itemData
                items_map[key]['itemName'] = item
                items_map[key]['platform'] = order["platform"]
            else:
                # Old Item
                items_map[key]["quantity"] += int(itemData["quantity"])
                items_map[key]["billed"] += float(itemData["billed"])
    print(items_map)
    for item in items_map.values():
        ITEMS_LIST.append([
            item['itemName'], 
            item["quantity"], 
            item["billed"],
            startDate.strftime("%d/%b/%Y"),
            item['platform'],
        ])
    return items_map, ITEMS_LIST

def main():
    clientData = json.loads(f.read())
    # Input Start Date of Range
    startDateInput = input('Enter start date(yyyy-mm-dd): ')
    # Input End Date of Range
    endDateInput = input('Enter end date(yyyy-mm-dd): ')

    if startDateInput == '':
        last_day_of_prev_month = date.today().replace(day=1) - timedelta(days=1)
        start_day_of_prev_month = date.today().replace(day=1) - timedelta(days=last_day_of_prev_month.day)
        startDate = datetime.combine(start_day_of_prev_month, datetime.min.time()).replace(hour=1, minute=30)
    else:
        startDateInput = str(startDateInput) + " 01:30"
        startDate = datetime.strptime(startDateInput, "%Y-%m-%d %H:%M")
    if endDateInput == '':
        last_day_of_prev_month = date.today().replace(day=1)# - timedelta(days=1)
        endDate = datetime.combine(last_day_of_prev_month, datetime.min.time()).replace(hour=1, minute=30)
    else:
        endDateInput = str(endDateInput) + " 01:30"
        endDate = datetime.strptime(endDateInput, "%Y-%m-%d %H:%M")

    zomatoExcelList, zomatoOrders = [], {}
    talabatExcelList, talabatOrders = [], {}
    deliverooExcelList, deliverooOrders = [], {}
    eateasyExcelList, eateasyOrders = [], {}
    careemnowExcelList, careemnowOrders = [], {}
    noonfoodExcelList, noonfoodOrders = [], {}

    for restaurant in clientData['restaurants']:
        if "zomato" in restaurant:
            zomatoData = zomatoBuilder(restaurant, startDate, endDate)
            zomatoExcelList = zomatoData[0]
            zomatoOrders = zomatoData[1]
        if "eateasy" in restaurant:
            eateasyData = eateasyBuilder(restaurant, startDate, endDate)
            eateasyExcelList = eateasyData[0]
            eateasyOrders = eateasyData[1]
    
        MASTER_ORDERS = zomatoExcelList + talabatExcelList + deliverooExcelList + eateasyExcelList + careemnowExcelList + noonfoodExcelList
        masterListofOrders = zomatoOrders | eateasyOrders | talabatOrders | deliverooOrders | eateasyOrders | careemnowOrders | noonfoodOrders
        MASTER_ORDERS = sorted(MASTER_ORDERS, key=itemgetter(2,1), reverse=True)
        
        CustomerListofOrders = copy.deepcopy(masterListofOrders)
       
        customerData = getCustomerData(CustomerListofOrders, startDate)
        unique_customers = customerData[0]
        UNIQUE_CUSTOMERS = customerData[1]
        UNIQUE_CUSTOMERS = sorted(UNIQUE_CUSTOMERS, key=itemgetter(4,3), reverse=True)

        ItemListofOrders = copy.deepcopy(masterListofOrders)
        itemData = getItemData(ItemListofOrders, startDate)
        items_map = itemData[0]
        ITEMS_LIST = itemData[1]
        ITEMS_LIST = sorted(ITEMS_LIST, key=itemgetter(2,1), reverse=True)

        # plot_map(restaurant, startDate, masterListofOrders)

        NEW_SHEET_NAME = startDate.strftime("%b-%Y")
        newSheet_request_body = {
            'requests': {
                'duplicateSheet': {
                    'sourceSheetId': TEMPLATE_SHEET_ID,
                    'insertSheetIndex': 2,
                    'newSheetName': NEW_SHEET_NAME
                    }
                }
            }

        SPREADSHEET_ID = restaurant["spreadsheet_id"]
        newSheet_response = sheet.batchUpdate(spreadsheetId=SPREADSHEET_ID,
            body = newSheet_request_body
        ).execute()

        # UPLOADING ORDER DATA
        rangeValue = NEW_SHEET_NAME + "!A3"
        request = sheet.values().update(spreadsheetId=SPREADSHEET_ID,
                        range=rangeValue, valueInputOption="USER_ENTERED", 
                        body={"values": MASTER_ORDERS}).execute()

        # UPLOADING ITEM DATA
        rangeValue = NEW_SHEET_NAME + "!O3"
        request = sheet.values().update(spreadsheetId=SPREADSHEET_ID,
                        range=rangeValue, valueInputOption="USER_ENTERED", 
                        body={"values": ITEMS_LIST}).execute()

        # UPLOADING CUSTOMER DATA
        rangeValue = NEW_SHEET_NAME + "!U3"
        request = sheet.values().update(spreadsheetId=SPREADSHEET_ID,
                        range=rangeValue, valueInputOption="USER_ENTERED", 
                        body={"values": UNIQUE_CUSTOMERS}).execute()
    f.close()

if __name__ == '__main__':
    start = time()
    main()
    end = time()
    print('Time Expended: ', end-start)
