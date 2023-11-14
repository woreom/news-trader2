## Import Libraries
from typing import Any, Callable
import functools
import pytz
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

def log(*args, file_path: str='log.txt'):
    timezone = pytz.timezone('Asia/Tehran')
    now = datetime.now(timezone)
    # open the file in append mode
    with open(file_path, 'a') as f:
        # write to the file
        f.write(f'[{now.strftime("%d/%m/%Y %H:%M:%S")}]{" ".join(map(str,args))}\n')
    
    print(f'[{now.strftime("%d/%m/%Y %H:%M:%S")}]{" ".join(map(str,args))}')

def try_on_internet(counter_limit: int):
    def decorator(func: Callable[..., Any]) -> Any:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any):
            counter = 0
            success = False
            while not success and counter<counter_limit:
                success, value = func(*args, **kwargs)
                counter+=1
            return success, value
        return wrapper
    return decorator

def log_it(func: Callable[..., Any]) -> Any:
    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any):
        value = func(*args, **kwargs)
        log(f"{func.__name__} returned {value}")
        return value
    return wrapper

@try_on_internet(counter_limit=10)
def test():
    print("i. Here")
    return False, None