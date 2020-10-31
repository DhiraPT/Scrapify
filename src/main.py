import os
import requests
import sqlite3
from sqlite3 import Error
from datetime import datetime, timezone, timedelta
import json
import time
import shutil
import sys
from watermark import watermark_with_transparency
#from view_db import view_items_db, view_models_db


def create_connection(db_file):
    """ create a database connection to a SQLite database """
    conn = None
    try:
        conn = sqlite3.connect(db_file)
        return conn
    except Error as e:
        print(e)
    return conn

def create_table(conn, create_table_sql):
    """ create a table from the create_table_sql statement
    :param conn: Connection object
    :param create_table_sql: a CREATE TABLE statement
    :return:
    """
    try:
        c = conn.cursor()
        c.execute(create_table_sql)
    except Error as e:
        print(e)

def create_db():
    sql_create_items_table = """ CREATE TABLE IF NOT EXISTS items (
                                    itemid integer PRIMARY KEY,
                                    item_name text NOT NULL,
                                    item_url text NOT NULL,
                                    categories text NOT NULL,
                                    description text NOT NULL,
                                    brand text,
                                    stock integer NOT NULL,
                                    imageURLs text NOT NULL,
                                    updated_at datetime NOT NULL
                                ); """

    sql_create_models_table = """CREATE TABLE IF NOT EXISTS models (
                                    modelid integer PRIMARY KEY,
                                    model_name text NOT NULL,
                                    price integer NOT NULL,
                                    stock integer NOT NULL,
                                    itemid integer NOT NULL,
                                    imageURL text NOT NULL,
                                    updated_at datetime NOT NULL,
                                    FOREIGN KEY (itemid) REFERENCES items (itemid)
                                );"""

    # create a database connection
    conn = create_connection(shop_dir+'/scraped_data.db')

    # create tables
    if conn is not None:
        # create items table
        create_table(conn, sql_create_items_table)

        # create models table
        create_table(conn, sql_create_models_table)
        
    else:
        print("Error! cannot create the database connection.")

def get_shopid(shop_username, session):
    url = 'https://shopee.co.id/api/v2/shop/get?username='+shop_username
    response = session.get(url)
    response_json = response.json()
    if response_json["data"] == None:
        print("Shop does not exist.")
        return None
    return response_json["data"]["shopid"]

def get_all_itemids(shopid, session):
    itemids = []
    # First 100
    url = 'https://shopee.co.id/api/v2/search_items/?by=pop&limit=100&match_id='+str(shopid)+'&newest=0&order=desc&page_type=shop&version=2'
    response = session.get(url)
    response_json = response.json()
    items = response_json["items"]
    for i in range(len(items)):
        itemids += [items[i]["itemid"]]
    total_items = response_json["total_count"]
    # print(total_items)
    # Iterate 100 items
    for j in range(total_items//100):
        url = 'https://shopee.co.id/api/v2/search_items/?by=pop&limit=100&match_id='+str(shopid)+'&newest='+str((j+1)*100)+'&order=desc&page_type=shop&version=2'
        response = session.get(url)
        response_json = response.json()
        items = response_json["items"]
        for i in range(len(items)):
            itemids += [items[i]["itemid"]]
    print("----------------------------")
    print("There are", len(itemids), "items in the shop.")
    print("----------------------------")
    return itemids

def get_item_details(shopid, itemid, session):
    categories = []
    url = 'https://shopee.co.id/api/v2/item/get?itemid='+str(itemid)+'&shopid='+str(shopid)
    response = session.get(url)
    item = response.json()["item"]
    name = item["name"]
    #print(name)
    item_name_url = name.replace(" ", "-").replace("/", "-").replace("\\", "-").replace("---", "-")
    item_url = 'https://shopee.co.id/'+item_name_url+'-i.'+str(shopid)+'.'+str(itemid)
    #print(item_url)
    categories += [category["display_name"] for category in item["categories"]]
    #print(categories)
    #print(categories)
    description = item["description"]
    #print(description)
    #print(description)
    #discount = item["discount"]
    #print(discount)
    brand = item["brand"]
    item_stock = item["stock"]
    imageURLs = ['https://cf.shopee.co.id/file/'+str(img) for img in item["images"]]
    # print(imageURLs)
    unsorted_models = []
    models_raw = item["models"]
    models_imageURLs = item["tier_variations"][0]["images"]
    for model in models_raw:
        modelid = model["modelid"]
        model_name = model["name"]
        price = model["price"]//100000
        model_stock = model["stock"]
        tier_index = model["extinfo"]["tier_index"][0]
        if len(models_imageURLs) != 0:
            model_imageURL = 'https://cf.shopee.co.id/file/'+models_imageURLs[tier_index]
        else:
            model_imageURL = ''
        model = {"tier_index": tier_index, "modelid": modelid, "model_name": model_name, "price": price, "stock": model_stock,
                 "model_imageURL": model_imageURL}
        unsorted_models += [model]
    #print(models)
    models = sorted(unsorted_models, key=lambda k: k["tier_index"])
    return {"itemid": itemid, "item_name": name, "item_name_url": item_name_url, "item_url": item_url,
            "categories": categories, "description": description, "brand": brand, "stock": item_stock,
            "imageURLs": imageURLs, "models": models}

def save_db(item_details):
    sql_item = ''' INSERT INTO items(itemid,item_name,item_url,categories,description,brand,stock,imageURLs,updated_at)
              VALUES(?,?,?,?,?,?,?,?,?) '''
    sql_model = ''' INSERT INTO models(modelid,model_name,price,stock,itemid,imageURL,updated_at)
              VALUES(?,?,?,?,?,?,?) '''
    # create a database connection
    conn = create_connection(shop_dir+'/scraped_data.db')
    if conn is not None:
        cur = conn.cursor()
        try:
            cur.execute(sql_item, (item_details["itemid"], item_details["item_name"], item_details["item_url"], json.dumps(item_details["categories"]),
                                   item_details["description"], item_details["brand"], item_details["stock"], json.dumps(item_details["imageURLs"]),
                                datetime.now(offset)))
        
            for model in item_details["models"]:
                cur.execute(sql_model, (model["modelid"], model["model_name"], model["price"], model["stock"],
                                       item_details["itemid"], json.dumps(model["model_imageURL"]), datetime.now(offset)))
        except:
            shutil.rmtree(shop_dir)
        conn.commit()
        conn.close()
        return "Successfully saved "+item_details["item_name"]+" into the database."
    else:
        shutil.rmtree(shop_dir)
        return "Error! cannot create the database connection."

def get_itemids_in_old_db(shop_username):
    # create a database connection
    conn = create_connection(shop_dir+'/old_scraped_data.db')
    if conn is not None:
        cur = conn.cursor()
        old_itemids = [itemid[0] for itemid in cur.execute("SELECT itemid FROM items")]
        return old_itemids
    else:
        return "Error! cannot create the database connection."

def get_itemids_in_new_db(shop_username):
    # create a database connection
    conn = create_connection(shop_dir+'/scraped_data.db')
    if conn is not None:
        cur = conn.cursor()
        new_itemids = [itemid[0] for itemid in cur.execute("SELECT itemid FROM items")]
        return new_itemids
    else:
        return "Error! cannot create the database connection."

def get_item_name_in_old_db(shop_username, old_itemid):
    # create a database connection
    conn = create_connection(shop_dir+'/old_scraped_data.db')
    if conn is not None:
        cur = conn.cursor()
        cur.execute("SELECT item_name FROM items WHERE itemid=?", (old_itemid,))
        return cur.fetchone()[0]
    else:
        return "Error! cannot create the database connection."

    
if __name__ == "__main__":
    offset = timezone(timedelta(hours=7))
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/86.0.4240.111 Safari/537.36 Edg/86.0.622.51",
                "X-Requested-With": "XMLHttpRequest",
                "Referer": "https://shopee.co.id"}
    
    # SCRAPING OR VIEW SCRAPED DATA
    print("RUNNING SCRAPIFY")
    print("Made by Dhiraputta Pathama Tengara")
    print("Scraped a shop, Update the scraped data of a shop or View scraped data?")
    print("1 - Scraped a shop")
    print("2 - Update the scraped data of a shop")
    # print("3 - View scraped data")
    task = "0"
    while (task != "1") and (task != "2"):
        task = input("Input Choice Number: ")

    if task == "1":
        shopid = None
        while shopid == None:
            shop_username = input("Input Shop Username: ")
            with requests.session() as session:
                session.headers.update(headers)
                shopid = get_shopid(shop_username, session)
                # print(shopid)
            
        shop_dir = '../saved_data/'+shop_username
        if os.path.exists(shop_dir):
            print("Scraped data exist for this shop.")
            sys.exit(0)
        else:
            try:
                os.mkdir(shop_dir)
                os.mkdir(shop_dir+'/images')
            except OSError:
                print ("Creation of the directory %s failed" % (shop_dir))
            else:
                print ("Successfully created the directory %s " % (shop_dir))
        
        print("Watermark position: ")
        print("1 - Top Left")
        print("2 - Center")
        watermark_position = "0"
        while (watermark_position != "1") and (watermark_position != "2"):
            watermark_position = input("Input Choice Number: ")
        
        # Start Timer
        start_time = time.time()
        
        # Start scraping
        with requests.session() as session:
            session.headers.update(headers)
            itemids = get_all_itemids(shopid, session)
            
            # Create Database
            create_db()
            
            for itemid in itemids:
                item_details = get_item_details(shopid, itemid, session)
                print(save_db(item_details))
                
                item_img_dir = shop_dir+'/images/'+item_details["item_name_url"]+"_"+str(item_details["itemid"])
                try:
                    os.mkdir(item_img_dir)
                    os.mkdir(item_img_dir+"/item_images")
                    os.mkdir(item_img_dir+"/models_images")
                except OSError:
                    shutil.rmtree(shop_dir)
                    print ("Creation of the directory %s failed" % (item_img_dir))
                    
                for imageURL in item_details["imageURLs"]:
                    if imageURL != "":
                        watermark_with_transparency(imageURL, item_img_dir+"/item_images/"+imageURL[29:]+".png",
                                                    '../watermark_img/watermark.png', watermark_position)
                print("Successfully watermarked all "+item_details["item_name"]+"\'s images.")
                
                for model in item_details["models"]:
                    model_imageURL = model["model_imageURL"]
                    if model_imageURL != "":
                        model_image_dir = item_img_dir+"/models_images/"\
                                        +(model["model_name"].replace(" ", "-").replace("/", "-").replace("\\", "-").replace("---", "-"))\
                                        +"_"+imageURL[29:]+".png"
                        watermark_with_transparency(model_imageURL, model_image_dir,
                                                    '../watermark_img/watermark.png', watermark_position)
                print("Successfully watermarked all "+item_details["item_name"]+" models' images.")

        f = open(shop_dir+"/log.txt","w+")
        f.write(str(datetime.now(offset))+": CREATE")
        f.close()
                    
        print("Scraping finished in --- %s seconds ---" % (time.time() - start_time))

    elif task == "2":
        shop_username = input("Input Shop Username: ")
        shop_dir = '../saved_data/'+shop_username
        while os.path.exists(shop_dir) == False:
            print("Shop has not been scraped.")
            shop_username = input("Input Shop Username: ")
        
        shutil.move(shop_dir+'/scraped_data.db',shop_dir+'/old_scraped_data.db')
        old_itemids = get_itemids_in_old_db(shop_username)

        # Start Timer
        start_time = time.time()
        
        with requests.session() as session:
            session.headers.update(headers)
            shopid = get_shopid(shop_username, session)
            itemids = get_all_itemids(shopid, session)

            # Create Database
            create_db()

            f = open(shop_dir+"/log.txt","a+")
            f.write("\n")
            f.write(str(datetime.now(offset))+": UPDATE\n")
            f.write("    Items Added:\n")
            
            for itemid in itemids:
                item_details = get_item_details(shopid, itemid, session)
                print(save_db(item_details))

                # Items added
                if itemid not in old_itemids:
                    item_img_dir = shop_dir+'/images/'+item_details["item_name_url"]+"_"+str(item_details["itemid"])
                    f.write("              "+str(itemid)+' - '+item_details["item_name"]+"\n")
                    try:
                        os.mkdir(item_img_dir)
                        os.mkdir(item_img_dir+"/item_images")
                        os.mkdir(item_img_dir+"/models_images")
                    except OSError:
                        print ("Creation of the directory %s failed" % (item_img_dir))
                        
                    for imageURL in item_details["imageURLs"]:
                        if imageURL != "":
                            watermark_with_transparency(imageURL, item_img_dir+"/item_images/"+imageURL[29:]+".png",
                                                        '../watermark_img/watermark.png', watermark_position)
                    print("Successfully watermarked all "+item_details["item_name"]+"\'s images.")
                    
                    for model in item_details["models"]:
                        model_imageURL = model["model_imageURL"]
                        if model_imageURL != "":
                            model_image_dir = item_img_dir+"/models_images/"\
                                        +(model["model_name"].replace(" ", "-").replace("/", "-").replace("\\", "-").replace("---", "-"))\
                                        +"_"+imageURL[29:]+".png"
                            watermark_with_transparency(model_imageURL, model_image_dir,
                                                        '../watermark_img/watermark.png', watermark_position)
                    print("Successfully watermarked all "+item_details["item_name"]+" models' images.")

        new_itemids = get_itemids_in_new_db(shop_username)

        f.write("    Items Removed:\n")

        for old_itemid in old_itemids:
            
            # Items removed
            if old_itemid not in new_itemids:
                removed_item_name = get_item_name_in_old_db(shop_username, old_itemid)
                removed_item_name_url = removed_item_name.replace(" ", "-").replace("/", "-").replace("\\", "-").replace("---", "-")
                shutil.rmtree(shop_dir+'/images/'+removed_item_name_url+'_'+old_itemid)
                f.write("              "+str(old_itemid)+' - '+removed_item_name+"\n")

        f.close()
                    
        print("Update finished in --- %s seconds ---" % (time.time() - start_time))
        
    '''elif task == "3":
        # INPUTS FOR VIEWING SCRAPED DATA
        print("View items from a shop or models of an item from a shop?")
        print("1 - View items from a shop")
        print("2 - View models of an item from a shop")
        view_task = "0"
        while (view_task != "1") and (view_task != "2"):
            view_task = input("Input Choice Number: ")
        shop_username = input("Input Shop Username: ")
        shop_dir = '../saved_data/'+shop_username

        if view_task == "1":
            view_items_db(shop_dir)
        elif view_task == "2":
            item_name = ("Item name of the models: ")
            view_models_db(shop_dir, item_name)'''
