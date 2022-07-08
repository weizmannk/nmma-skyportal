import time

seconds = 10


def Timer(seconds):
    print("please wait for update skyportal token : \n start in : {seconds} seconds")
    for i in range(seconds):
        time.sleep(1)
        print(seconds)
        seconds -= 1
    if seconds == 0:
        print("End")
