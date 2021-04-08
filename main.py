from hdjxClient import Client
from recognizer import TTShituRecognizer
from config import Parser

def main():
    parser = Parser()
    config = parser.parse_config("client")
    client = Client(config)
    tasks = parser.parse_tasks()
    client.register_task(tasks)
    try:
        client.execute()
    except Exception as e:
        raise e
    finally:
        client.close()

if __name__ == "__main__":
    main()