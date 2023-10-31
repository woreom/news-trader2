## Import Libraries
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

    