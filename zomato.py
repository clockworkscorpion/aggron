from datetime import datetime, time

from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import pprint

from mapper import getPoints

# ***********************************************************************************************************
# DO NOT EDIT THESE
chrome_options = webdriver.ChromeOptions()
chrome_options.add_argument("start-maximized")
chrome_options.add_argument('--user-data-dir=C:/Users/AndroidDev/AppData/Local/Google/Chrome/User Data')
PATH = r"C:\Users\AndroidDev\Desktop\aggron\chromedriver\chromedriver.exe"
pp = pprint.PrettyPrinter(indent=2)
# DO NOT EDIT TILL HERE
# *********************************************************************************************************

def zomatoBuilder(restaurant, startDate, endDate):
    map_of_orders = {}
    LIST_OF_ORDERS = []
    print("\nRunning Zomato parser")

    # Priming variables
    ZOMATO_ID = restaurant['zomato']
    NAME = restaurant['name']
    SPREADSHEET_ID = restaurant['spreadsheet_id']
    ADDRESS = restaurant['address']
    LOCALITY = restaurant['locality']
    CITY = restaurant['city']
    PHONE = restaurant['phone']
    LATITUDE = restaurant['latitude']
    LONGITUDE = restaurant['longitude']
    CUISINES = restaurant['cuisines']
    COST_FOR_2 = restaurant['cost_for_two']
    HAS_ONLINE_DELIVERY = restaurant['has_online_delivery']
    URL = 'https://www.zomato.com/clients/delivery_orders.php?entity_type=restaurant&entity_id=' + ZOMATO_ID
    # Starting WebDriver and loading profile
    chrome_options.add_argument('--profile-directory=Profile %d' % restaurant['chrome_profile'])
    driver = webdriver.Chrome(PATH, options = chrome_options)
    driver.get(URL)
    driver.implicitly_wait(3)

    while True:
        try:
            # Limit orders to only those between selected dates
            orders = driver.find_elements_by_class_name("order_row")
            lastOrder = orders[-1]
            lastOrderTimeString = lastOrder.find_element_by_class_name("order_time").text       # order time
            lastOrderTime = datetime.strptime(lastOrderTimeString, "%H:%M, %B %d %Y")               # parse order Date-Time
            if startDate <= lastOrderTime <= datetime.now():
                load_more = WebDriverWait(driver,10).until(EC.element_to_be_clickable((By.ID, 'table-footer-load-more')))
                load_more.click()
            else:
                break
        except TimeoutException:
            print ("End of List")
            break
        except NoSuchElementException:
            print ("End of List")
            break
    orders = driver.find_elements_by_class_name("order_row")                        # orders class
    for order in orders:
        ORDER_EXCEL_ROW = []
        orderTimeString = order.find_element_by_class_name("order_time").text       # order time extraction
        orderTime = datetime.strptime(orderTimeString, "%H:%M, %B %d %Y")     # parse order Date-Time
        ORDER_DATE = str(orderTime.date())                                       # order Date
        ORDER_TIME = str(orderTime.time())                                         # order Time
        ORDER_MEAL = ""
        if time(4,00,00) <= orderTime.time() <= time(10,59,59):
            ORDER_MEAL = "Breakfast"
        elif time(11,00,00) <= orderTime.time() <= time(16,29,59):
            ORDER_MEAL = "Lunch"
        elif time(16,30,00) <= orderTime.time() <= time(18,59,59):
            ORDER_MEAL = "Snacks"
        elif time(19,00,00) <= orderTime.time() <= time(23,59,59) or time(00,00,00) <= orderTime.time() <= time(3,59,59):
            ORDER_MEAL = "Dinner"
        if startDate <= orderTime <= endDate:
            orderRowText = order.text.replace(orderTimeString,"")               # remove the date from the array
            orderArray = orderRowText.split(" ")                                # split the row array for each order into respective columns
            ORDER_ID = orderArray[0]
            PAYMENT_TYPE = orderArray[3]
            ORDER_DELIVERY_MODE = orderArray[4]
            if "Zomato" in orderArray:
                BILL_AMOUNT = float(orderArray[6].replace("AED", ""))
                # ORDER_REJECTION = " ".join(orderArray[7:len(orderArray)])
            else:
                BILL_AMOUNT = float(orderArray[5].replace("AED", ""))
                # ORDER_REJECTION = " ".join(orderArray[6:len(orderArray)])
            if ORDER_ID not in map_of_orders.keys():
                # Click on Order ZOMATO_ID to get customer Information
                billdetails = WebDriverWait(driver,20).until(EC.invisibility_of_element_located((By.ID, 'modal-container')))
                orderIDclickable = order.find_element_by_class_name("viewOrder").click()
                
                # Customer Details
                billdetails = WebDriverWait(driver,20).until(EC.visibility_of_element_located((By.ID, 'modal-container')))
                arrays = driver.find_elements_by_class_name("ui.very.basic.table")
                customerArray = arrays[0].text.split("\n")
                CUSTOMER_NAME = customerArray[0]
                CUSTOMER_INSTRUCTIONS = ""
                CUSTOMER_PHONE = ""
                if customerArray[1].isdecimal():
                    CUSTOMER_PHONE = "+971" + customerArray[1]
                    if len(customerArray) == 2:
                        CUSTOMER_ADDRESS = ADDRESS
                    else:
                        CUSTOMER_ADDRESS = customerArray[2]
                    # if len(customerArray) > 3:
                    #     LANDMARK = customerArray[4]
                    #     CUSTOMER_ADDRESS = CUSTOMER_ADDRESS + " " + LANDMARK
                    # if len(customerArray) > 5:
                    #     CUSTOMER_INSTRUCTIONS = customerArray[6]
                else:
                    # NO customer phone number available
                    CUSTOMER_ADDRESS = customerArray[1]
                    # if len(customerArray) > 2:
                    #     LANDMARK = customerArray[3]
                    #     CUSTOMER_ADDRESS = CUSTOMER_ADDRESS + " " + LANDMARK
                    # if len(customerArray) > 4:
                    #     CUSTOMER_INSTRUCTIONS = customerArray[5]
                
                # Items Details
                try:
                    orderItemsArray = arrays[1].text.split("\n")
                    si = iter(orderItemsArray)                                  # Join menu items with price and quantities
                    orderItemsUnformatted = [c + " " + next(si, '') for c in si]      # List with item name, quantity and prices joined
                    # orderItems = {
                    #         ' '.join(item.split(' x ')[0].split()[:-1]).replace("Quantity : ", "").replace("Customize : ", ""): {
                    #             'quantity': int(item.split(' x ')[0].split()[-1]),
                    #             'billed': float(item.split()[-1])
                    #     } if item not in orderItems.items() else ' '.join(item.split(' x ')[0].split()[:-1]).replace("Quantity : ", "").replace("Customize : ", ""): {
                    #             'quantity': int(item.split(' x ')[0].split()[-1]),
                    #             'billed': float(item.split()[-1])
                    #     } for item in orderItemsUnformatted}
                    orderItems = {}
                    for itemString in orderItemsUnformatted:
                        orderItemName = ' '.join(itemString.split(' x ')[0].split()[:-1]).replace("Quantity : ", "").replace("Customize : ", "")
                        orderItemQuantity = int(itemString.split(' x ')[0].split()[-1])
                        orderItemBilled = float(itemString.split()[-1])
                        if orderItemName not in orderItems.keys():
                            orderItems[orderItemName] = {
                                'quantity': orderItemQuantity,
                                'billed': orderItemBilled                            
                            }
                        else:
                            orderItems[orderItemName] = {
                                'quantity': orderItems[orderItemName]["quantity"] + orderItemQuantity,
                                'billed': orderItems[orderItemName]["billed"] + orderItemBilled
                            }
                except:
                    print("Error - Items not found")
                deliveryCharge = arrays[2].text
                if "Delivery Charge" in deliveryCharge:
                    deliveryCharge = deliveryCharge.split("\n")[0]
                    deliveryCharge = float(deliveryCharge.split("AED ")[1])
                else:
                    deliveryCharge = 0
                BILL_AMOUNT = BILL_AMOUNT - deliveryCharge
                ORDER_PLATFORM = "Zomato"
                CUSTOMER_ADDRESS = CUSTOMER_ADDRESS.replace('"', "").replace("'","").replace("\n","")
                # coords = getPoints(CUSTOMER_ADDRESS)
                # ORDER_LATITUDE = coords[0]
                # ORDER_LONGITUDE = coords[1]
                # GIS2_LATITUDE = coords[2]
                # GIS2_LONGITUDE = coords[3]
                new_order = {
                    ORDER_ID: {
                        "platform": ORDER_PLATFORM,
                        "time": ORDER_TIME,
                        "date": ORDER_DATE,
                        "deliverMode": ORDER_DELIVERY_MODE,
                        "mealTime": ORDER_MEAL,
                        "customerName": CUSTOMER_NAME,
                        "customerPhone": CUSTOMER_PHONE,
                        "customerAddress": CUSTOMER_ADDRESS,
                        # "latitude": ORDER_LATITUDE,
                        # "longitude": ORDER_LONGITUDE,
                        # "2gis latitude": GIS2_LATITUDE,
                        # "2gis longitude": GIS2_LONGITUDE,
                        "billAmount": BILL_AMOUNT,
                        "paymentType": PAYMENT_TYPE,
                        "orderItems": orderItems
                    }
                }
                # pp.pprint(new_order)
                ORDER_ITEMS = ''
                for itemName, item in orderItems.items():        
                    ORDER_ITEMS = ORDER_ITEMS + str(itemName + " (" + str(item["quantity"]) + "), ")
                # Row in Spreadsheet
                ORDER_EXCEL_ROW = [
                    ORDER_ID, ORDER_TIME, ORDER_DATE, ORDER_PLATFORM, ORDER_MEAL, 
                    CUSTOMER_NAME, CUSTOMER_PHONE, CUSTOMER_ADDRESS, 
                    # ORDER_LATITUDE, ORDER_LONGITUDE, 
                    BILL_AMOUNT, PAYMENT_TYPE, ORDER_ITEMS
                ]
                LIST_OF_ORDERS.append(ORDER_EXCEL_ROW)
                map_of_orders |= new_order
                # Close the Modal Container Overlay
                closeIcon = WebDriverWait(driver,10).until(EC.presence_of_element_located((By.XPATH, '//*[@id="modal-container"]/i')))
                driver.execute_script("arguments[0].click();", closeIcon)
    driver.quit()
    # print(LIST_OF_ORDERS)
    # LIST_OF_ORDERS.sort()
    # print(LIST_OF_ORDERS)
    # map_of_orders.sort()
    # list(LIST_OF_ORDERS for LIST_OF_ORDERS,_ in itertools.groupby(LIST_OF_ORDERS))
    # list(map_of_orders for map_of_orders,_ in itertools.groupby(map_of_orders))
    # LIST_OF_ORDERS = list(OrderedDict.fromkeys(LIST_OF_ORDERS))
    # LIST_OF_ORDERS.sort(key = LIST_OF_ORDERS.index)
    # b_set = set(tuple(x) for x in LIST_OF_ORDERS)
    # LIST_OF_ORDERS = [list(x) for x in b_set]
    return LIST_OF_ORDERS, map_of_orders
