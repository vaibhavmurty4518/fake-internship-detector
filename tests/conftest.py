import os, sys
os.environ["INTERNSHIELD_OFFLINE"] = "1"
os.environ["COMPANY_CACHE_ENABLED"] = "0"
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
