from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from time import sleep
import opensea.database as db
import time

from PIL import Image


def get_images():

    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1920,1080")

    driver = webdriver.Chrome("/usr/local/bin/chromedriver", options=chrome_options)

    aws_db = db.connect_mongo()
    all_collections = aws_db.list_collection_names()

    # filter all_collections to only include collections that have "bestvalue_opensea_listings" in the name
    all_collections = [
        collection
        for collection in all_collections
        if "bestvalue_opensea_listings" in collection
    ]

    for collection in all_collections:
        col = collection.replace("_bestvalue_opensea_listings", "")
        driver.get(f"http://localhost:5002/predicted/{col}")

        start_time = time.time()

        # wait for title to not say "Updating..."
        while driver.title == "Updating...":
            sleep(5)

            # if timer over 4 minutes, break
            if time.time() - start_time > 240:
                break

        image_path = f"./sc_for_twitter/screenshot_{col}.png"

        sleep(5)  # make sure all images are loaded

        driver.get_screenshot_as_file(image_path)

        im = Image.open(image_path)
        w, h = im.size

        im.crop((260, 0, w - 100, h - 100)).save(image_path, quality=95)

        print(f"done {col}")

    driver.quit()
