from datetime import datetime, time

from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import re
import pprint

from mapper import getPoints

# ***********************************************************************************************************
chrome_options = webdriver.ChromeOptions()
chrome_options.add_argument("start-maximized")
chrome_options.add_argument('--user-data-dir=path_to_chrome_user_data')
PATH = r"path_to_chromedriver.exe"
pp = pprint.PrettyPrinter(indent=2)
# *********************************************************************************************************

def eateasyBuilder(restaurant, startDate, endDate):
    map_of_orders = {}
    LIST_OF_ORDERS = []
    print("\nRunning EatEasy Parser")

    # Priming variables
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
    URL = "https://manage.eateasily.com/merchant/order/restaurant_view/2/0"
    # Starting WebDriver and loading profile
    chrome_options.add_argument('--profile-directory=Profile %d' % restaurant['chrome_profile'])
    driver = webdriver.Chrome(PATH, options = chrome_options)
    driver.get('https://manage.eateasily.com/')
    driver.find_element_by_class_name("submit").click()
    driver.find_element_by_class_name("close-modal").click()
    driver.get(URL)
    pageCount = 1
    maxPageCount = int(driver.find_element_by_class_name('pageof').text.replace("Page 1 Of ",""))

    while pageCount <= maxPageCount:
        orders = driver.find_elements_by_class_name("odd") + driver.find_elements_by_class_name("even")
        orderRows = [[element.text for element in order.find_elements_by_tag_name('td')] for order in orders]
        orderLinks = [[order.get_attribute('rel')] for order in orders]
        orders = [row + link for row, link in zip(orderRows, orderLinks)]
        orders = sorted(orders, key=lambda x: int(x[0]))
        for order in orders:
            ORDER_EXCEL_ROW = []
            orderTime = datetime.strptime(order[6], "%I:%M %p %d %b %Y")
            if orderTime<= startDate:
                maxPageCount = pageCount
                break
            if orderTime <= endDate:
                ORDER_DATE = str(orderTime.date())
                ORDER_TIME = str(orderTime.time())
                ORDER_MEAL = ""
                if time(4,00,00) <= orderTime.time() <= time(10,59,59):
                    ORDER_MEAL = "Breakfast"
                elif time(11,00,00) <= orderTime.time() <= time(16,29,59):
                    ORDER_MEAL = "Lunch"
                elif time(16,30,00) <= orderTime.time() <= time(18,59,59):
                    ORDER_MEAL = "Snacks"
                elif time(19,00,00) <= orderTime.time() <= time(23,59,59) or time(00,00,00) <= orderTime.time() <= time(3,59,59):
                    ORDER_MEAL = "Dinner"
                ORDER_ID = str(order[1].split('\n')[1].replace("[#","").replace("]",""))
                LOCALITY = str(order[2].replace(" [%s]" % restaurant['eateasy']['username'], ""))
                BILL_AMOUNT = float(order[5].replace(" AED",""))
                link = order[-1]
                driver.execute_script("window.open('');")
                driver.switch_to.window(driver.window_handles[-1])
                driver.get(link)
                # CUSTOMER PERSONAL INFO
                customerPersonal = driver.find_element_by_xpath('//*[@id="content"]/div[4]/h2[1]').text
                CUSTOMER_PHONE = re.findall(r"\((.*?)\)", customerPersonal)[0].replace(" ","")
                CUSTOMER_NAME = str(customerPersonal.replace(" ( " + CUSTOMER_PHONE + " )", "").split('\n')[0])
                CUSTOMER_PHONE = str("+971" + CUSTOMER_PHONE[1:])
                # DELIVERY MODE & DRIVER CONTACT INFO
                ORDER_DELIVERY_MODE = ""
                DRIVER_NAME = ""
                DRIVER_PHONE = ""
                CUSTOMER_ADDRESS = ""
                driverDetails = {}
                try:
                    ORDER_DELIVERY_MODE = "Delivery"
                    driverDetails = driver.find_element_by_id("div_list")
                    driverDetails = driverDetails.find_elements_by_tag_name('tr')[1]
                    driverLink = driverDetails.find_element_by_tag_name('a').get_attribute('href')
                    driverDetails = re.findall(r"\((.*?)\)", driverDetails.text)[0].split(" - ")
                    DRIVER_NAME = driverDetails[0]
                    DRIVER_PHONE = driverDetails[1]
                except NoSuchElementException:
                    ORDER_DELIVERY_MODE = "Takeout"
                # ITEM DETAILS
                items = driver.find_elements_by_class_name("odd") + driver.find_elements_by_class_name("even")
                orderItems = [[element.text for element in item.find_elements_by_tag_name('td')] for item in items]
                orderItems = {
                    str(item[0].split('\n')[0]) if len(item[0].split('\n'))<=2 else str(item[0].split('\n')[0] + item[0].split('\n')[1])
                    .split("[")[0]: {
                        'quantity': int(item[1]),
                        'billed': float(item[3])
                    } for item in orderItems
                }
                ORDER_ITEMS = str(orderItems)
                # # list_sold_items = [[item['name'], item['quantity'], item['price']*item['quantity']] for item in orderItems]
                PAYMENT_TYPE = driver.find_element_by_id("payment_type").text
                if "Prepaid Order" in PAYMENT_TYPE or "Paid Online" in PAYMENT_TYPE:
                    PAYMENT_TYPE = "Online"
                else:
                    PAYMENT_TYPE = "COD"
                CUSTOMER_INSTRUCTIONS = ''
                # GET ADDRESS IF AVAILABLE
                if len(driverDetails) != 0:
                    DRIVER_NAME = driverDetails[0]
                    DRIVER_PHONE = "+" + driverDetails[1]
                    driver.execute_script("window.open('');")
                    driver.switch_to.window(driver.window_handles[-1])
                    driver.get(driverLink)
                    if "careem" in driverLink:
                        CUSTOMER_ADDRESS = str(driver.find_element_by_id("dropoff_content").text.replace("#floor/room:",""))
                    elif "quikup" in driverLink:
                        waypoint = WebDriverWait(driver,10).until(EC.presence_of_element_located((By.CLASS_NAME, 'waypoint-marker-header')))
                        waypoint.click()
                        address = WebDriverWait(driver,10).until(EC.presence_of_element_located((By.CLASS_NAME, 'leaflet-popup-content')))
                        CUSTOMER_ADDRESS = str(driver.find_element_by_class_name("leaflet-popup-content").text)
                    else:
                        print("No driver")
                    if CUSTOMER_ADDRESS == '' or CUSTOMER_ADDRESS is None:
                        CUSTOMER_ADDRESS = LOCALITY
                    driver.close()
                    driver.switch_to.window(driver.window_handles[1])
                CUSTOMER_ADDRESS = CUSTOMER_ADDRESS.replace('"', "").replace("'","").replace("\n","")
                ORDER_PLATFORM = "Smiles"
                coords = getPoints(CUSTOMER_ADDRESS)
                ORDER_LATITUDE = coords[0]
                ORDER_LONGITUDE = coords[1]
                new_order = {
                    ORDER_ID : {
                        "platform": ORDER_PLATFORM,
                        "time": ORDER_TIME,
                        "date": ORDER_DATE,
                        "deliverMode": ORDER_DELIVERY_MODE,
                        "mealTime": ORDER_MEAL,
                        "customerName": CUSTOMER_NAME,
                        "customerPhone": CUSTOMER_PHONE,
                        "customerAddress": CUSTOMER_ADDRESS,
                        "latitude": ORDER_LATITUDE,
                        "longitude": ORDER_LONGITUDE,
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
                    CUSTOMER_NAME, CUSTOMER_PHONE, CUSTOMER_ADDRESS, ORDER_LATITUDE,
                    ORDER_LONGITUDE, BILL_AMOUNT, PAYMENT_TYPE, ORDER_ITEMS
                ]
                LIST_OF_ORDERS.append(ORDER_EXCEL_ROW)
                map_of_orders |= new_order
                driver.close()
                driver.switch_to.window(driver.window_handles[0])
        # NEXT BUTTON
        driver.implicitly_wait(1)
        try:
            nextButton = WebDriverWait(driver,10).until(EC.presence_of_element_located((By.LINK_TEXT, 'Next »')))
            pageCount+=1
            driver.execute_script("arguments[0].click();", nextButton)
        except TimeoutException:
            print('Next Button not found')
            break
    driver.quit()
    return LIST_OF_ORDERS, map_of_orders
