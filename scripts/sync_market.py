import sys
import os
import requests
from datetime import date
import time

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.db.connection import get_supabase_client

def scrape_psx_summary():
    """
    Simulates fetching latest PSX summary data.
    In a real scenario, this would hit psx.com.pk or a data provider.
    """
    print(f"[{date.today()}] Fetching PSX Market Summary...")
    
    # Example symbols to sync
    symbols = ["ENGRO", "HBL", "FFBL", "SYS", "HUBC", "OGDC", "PPL", "LUCK"]
    
    supabase = get_supabase_client()
    sync_count = 0
    
    for symbol in symbols:
        # Simulate price data
        # In reality, you'd use a scraper or API here
        try:
            # We'll fetch existing latest to perturb it slightly for demo
            res = supabase.table("stock_prices").select("*").eq("symbol", symbol).order("date", desc=True).limit(1).execute()
            
            if res.data:
                latest = res.data[0]
                new_price = float(latest['close']) * (1 + (0.02 * (time.time() % 1 - 0.5))) # Random ±1%
                
                payload = {
                    "symbol": symbol,
                    "date": date.today().isoformat(),
                    "open": round(new_price * 0.99, 2),
                    "high": round(new_price * 1.02, 2),
                    "low": round(new_price * 0.98, 2),
                    "close": round(new_price, 2),
                    "volume": latest['volume'] + 1000
                }
                
                supabase.table("stock_prices").upsert(payload).execute()
                print(f"Synced {symbol}: {payload['close']}")
                sync_count += 1
        except Exception as e:
            print(f"Error syncing {symbol}: {e}")
            
    print(f"Successfully synced {sync_count} symbols.")

if __name__ == "__main__":
    scrape_psx_summary()
