import sys
import time
import json
import base64
from random import choice, random

from config import TaskList
from recognizer import TTShituRecognizer
from config import TaskList

from selenium import webdriver
from selenium.common.exceptions import NoAlertPresentException, TimeoutException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager

class HJConfig(object):

    _DEFAULT_CONFIG_PATH = './accounts.json'

    def __init__(self, path=_DEFAULT_CONFIG_PATH):
        with open(path, 'r') as handle:
            self._apikey = json.load(handle)["HDJX"]
        assert 'username' in self._apikey.keys() and 'password' in self._apikey.keys()

    @property
    def username(self):
        return self._apikey["username"]

    @property
    def password(self):
        return self._apikey["password"]


class ClientNeedsLogin(Exception):
    pass

class Client(object):

    _BASE_URL = "http://haijia.bjxueche.net/"
    _ELECT_URL = "http://haijia.bjxueche.net/ych2.aspx"

    def __init__(self, config):
        self._account = HJConfig()
        self._config = config
        self._driver = self._get_driver()
        self._tasks = None

    def _get_driver(self):
        webdriver = self._config.get("webdriver", "None")
        if webdriver == "Chrome":
            return self._chrome_driver() 
        else:
            raise RuntimeError(f"Unsupported driver: {webdriver}")

    def _chrome_driver(self):
        options = webdriver.ChromeOptions()
        options.add_argument("--ignore-certificate-errors")
        options.add_argument("--test-type")
        if sys.platform.startswith('linux'):
            options.add_argument('--headless')
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
        driver = webdriver.Chrome(ChromeDriverManager().install(), chrome_options=options)
        return driver

    def register_task(self, tasks):
        self._tasks = TaskList(tasks)

    def _oauth_login(self, max_retry=3):
        print("Trying to login...")
        retry = max_retry
        while retry:
            try:
                self._oauth_login_inner()
                WebDriverWait(self._driver, 2).until(EC.alert_is_present())
                self._sleep_rand()
                prompt = self._driver.switch_to.alert.text
                print(f"Login failed due to: {prompt}")
                TTShituRecognizer.get_instance().report_last_error()
                self._driver.switch_to.alert.dismiss()
            except (NoAlertPresentException, TimeoutException):
                print("Login succeeded.")
                return
            finally:
                retry -= 1
        raise RuntimeError("Recognizer max retry exceeded")

    def _redirect(self):
        print("Redirecting to elective page...")
        self._driver.get(Client._ELECT_URL)
        if self._driver.current_url != Client._ELECT_URL:
            raise ClientNeedsLogin
        self._sleep_rand()
            

    def _oauth_login_inner(self):
        self._driver.get(Client._BASE_URL)
        self._sleep_rand()
        self._driver.find_element_by_id('txtUserName').send_keys(self._account.username)
        self._sleep_rand()
        self._driver.find_element_by_id('txtPassword').send_keys(self._account.password)
        self._sleep_rand()
        
        recognizer = TTShituRecognizer.get_instance()
        valid_elem = self._driver.find_element_by_id("ValidIMG")
        img_captcha_base64 = self._driver.execute_async_script("""
            var ele = arguments[0], callback = arguments[1];
            ele.addEventListener('load', function fn(){
            ele.removeEventListener('load', fn, false);
            var cnv = document.createElement('canvas');
            cnv.width = this.width; cnv.height = this.height;
            cnv.getContext('2d').drawImage(this, 0, 0);
            callback(cnv.toDataURL('image/jpeg').substring(22));
            }, false);
            ele.dispatchEvent(new Event('load'));
            """, valid_elem)
        recog_result = recognizer.recognize(base64.b64decode(img_captcha_base64))

        self._driver.find_element_by_id('txtIMGCode').send_keys(recog_result)
        self._sleep_rand()
        self._driver.find_element_by_id('BtnLogin').click()
        self._sleep_rand()

    def _get_available_session(self):
        for elem in self._driver.find_elements_by_class_name("CellCar"):
            if elem.text == "无":
                continue
            sess_date = int(elem.get_attribute("yyrq"))
            sess_time = int(elem.get_attribute("yysd")) - 2003
            task = self._tasks.query_session(sess_date, sess_time)
            if not task:
                continue
            if elem.text == "已约":
                print(f"Task {sess_date}, {sess_date} is ALREADY DONE.")
                task.finished = True
                continue
            else:
                print(f"Session {sess_date}, {sess_time} is AVAILABLE {elem.text}!")
                return (elem, task) 
        print("No available session...")
        return None

    def _try_elect(self, elem):
        print("Trying to elect...")
        self._sleep_rand()
        elem.click()
        WebDriverWait(self._driver, 5).until(EC.visibility_of_element_located((By.CLASS_NAME, 'DivCNBH')))
        avail_cars = self._driver.find_elements_by_class_name("DivCNBH")
        print(f"Available cars: {' '.join([c.text for c in avail_cars])}")
        if not avail_cars:
            return False
        car = choice(avail_cars)
        self._sleep_rand()
        car.click()
        try:
            WebDriverWait(self._driver, 2).until(EC.alert_is_present())
            self._sleep_rand()
            prompt = self._driver.switch_to.alert.text
            assert prompt == "确定预约该时段训练吗?"
            self._driver.switch_to.alert.accept()
            WebDriverWait(self._driver, 5).until(EC.alert_is_present())
            self._sleep_rand()
            prompt = self._driver.switch_to.alert.text
            assert prompt == "预约成功!"
            self._driver.switch_to.alert.dismiss()
            print("Succeeded!")
            return True
        except (NoAlertPresentException, TimeoutException):
            print("Failed!")
            return False
        except:
            raise ClientNeedsLogin
            
    def execute(self):
        loop_counter = 0
        need_login = True
        while self._tasks:
            try:
                print(f"{'-'*8} Entering loop {loop_counter} {'-'*8}")
                if not self._check_time():
                    print("Website not in service time...")
                    time.sleep(60)
                    continue
                if need_login:
                    self._oauth_login()
                    need_login = False
                self._redirect()
                avail_sess = self._get_available_session()
                if avail_sess:
                    elem, task = avail_sess
                    success_flag = self._try_elect(elem)
                    if success_flag:
                        task.finished = True
                self._tasks.remove_finished()
                time.sleep(self._config.get("refreshinterval", 5))
            except KeyboardInterrupt as e:
                print("KeyboardInterrupt received.")
                break
            except ClientNeedsLogin:
                del self._driver
                self._driver = self._get_driver()
                need_login = True
            finally:
                loop_counter += 1
        else:
            print("Done!")

    def close(self):
        self._driver.quit()

    def _sleep_rand(self):
        sec = self._config.get("randomwait", 0.5)
        time.sleep(sec*(random()+0.2))

    def _check_time(self, start_time=(7, 35, 30), end_time=(21, 59, 30)):
        tlocal = time.localtime()
        tlocal_time = (tlocal.tm_hour, tlocal.tm_min, tlocal.tm_sec)
        return start_time <= tlocal_time <= end_time