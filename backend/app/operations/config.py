import os
from app.core.config import settings

def config(name,default=''):
    return os.environ.get(name,str(getattr(settings,name,default)))
