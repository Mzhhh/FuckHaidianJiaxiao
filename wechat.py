import json
import requests
from config import Task

class Notifier:

    _BASE_URL = "https://sc.ftqq.com/"
    _DEFAULT_KEY_PATH = "./accounts.json"

    def __init__(self, path=_DEFAULT_KEY_PATH):
        with open(path, 'r') as handle:
            self._key = json.load(handle).get("ServerChan", None)

    def __bool__(self):
        return self._key is not None

    def notify(self, task):
        assert bool(self)
        print("Sending wechat notification...")
        r = requests.get(
            Notifier._BASE_URL + f"/{self._key}.send",
            params={"text": f"{task} is ELECTED!"},
            
        )
        if r.ok:
            content = r.json() 
            if content["errmsg"] == "success":
                print("Wechat notification successfully send!")
            else:
                print(f"Oops, notification failed due to connection error {content['errmsg']}")
        else:
            print(f"Oops, notification failed due to connection error <{r.status_code}>")

    _instance = None

    def enabled():
        return bool(Notifier.get_instance())
    
    def get_instance():
        if not Notifier._instance:
            Notifier._instance = Notifier(Notifier._DEFAULT_KEY_PATH)
            return Notifier._instance
        else:
            assert isinstance(Notifier._instance, Notifier)
            return Notifier._instance