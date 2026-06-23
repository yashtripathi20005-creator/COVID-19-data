import requests
import pandas as pd
from datetime import datetime, timedelta
import json

class COVIDDataFetcher:
    def __init__(self):
        self.base_url = "https://disease.sh/v3/covid-19"
        self.cache = {}
        self.cache_time = {}
        self.cache_duration = 300  # 5 minutes cache
        
    def _get_cached_data(self, key):
        """Get data from cache if valid"""
        if key in self.cache and key in self.cache_time:
            if (datetime.now() - self.cache_time[key]).seconds < self.cache_duration:
                return self.cache[key]
        return None
    
    def _set_cache_data(self, key, data):
        """Set data in cache"""
        self.cache[key] = data
        self.cache_time[key] = datetime.now()
    
    def get_global_stats(self):
        """Get global COVID-19 statistics"""
        cache_key = "global_stats"
        cached = self._get_cached_data(cache_key)
        if cached is not None:
            return cached
            
        try:
            response = requests.get(f"{self.base_url}/all")
            response.raise_for_status()
            data = response.json()
            
            stats = {
                'total_cases': data.get('cases', 0),
                'total_deaths': data.get('deaths', 0),
                'total_recovered': data.get('recovered', 0),
                'active_cases': data.get('active', 0),
                'critical_cases': data.get('critical', 0),
                'total_tests': data.get('tests', 0),
                'population': data.get('population', 0),
                'last_updated': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            
            self._set_cache_data(cache_key, stats)
            return stats
        except requests.RequestException as e:
            print(f"Error fetching global stats: {e}")
            return None
    
    def get_country_stats(self, country=None):
        """Get COVID-19 statistics by country"""
        cache_key = f"country_stats_{country}" if country else "all_countries"
        cached = self._get_cached_data(cache_key)
        if cached is not None:
            return cached
            
        try:
            if country:
                response = requests.get(f"{self.base_url}/countries/{country}")
            else:
                response = requests.get(f"{self.base_url}/countries")
            response.raise_for_status()
            data = response.json()
            
            self._set_cache_data(cache_key, data)
            return data
        except requests.RequestException as e:
            print(f"Error fetching country stats: {e}")
            return None
    
    def get_historical_data(self, country='all', days=30):
        """Get historical COVID-19 data"""
        cache_key = f"historical_{country}_{days}"
        cached = self._get_cached_data(cache_key)
        if cached is not None:
            return cached
            
        try:
            response = requests.get(f"{self.base_url}/historical/{country}?lastdays={days}")
            response.raise_for_status()
            data = response.json()
            
            # Process historical data into DataFrames
            if country == 'all':
                # For all countries, we get a different response structure
                processed_data = self._process_global_historical(data, days)
            else:
                processed_data = self._process_country_historical(data, days)
            
            self._set_cache_data(cache_key, processed_data)
            return processed_data
        except requests.RequestException as e:
            print(f"Error fetching historical data: {e}")
            return None
    
    def _process_global_historical(self, data, days):
        """Process global historical data"""
        if not data:
            return None
            
        dates = []
        cases = []
        deaths = []
        recovered = []
        
        for date_str, stats in data.get('cases', {}).items():
            dates.append(date_str)
            cases.append(stats)
            
        for date_str, stats in data.get('deaths', {}).items():
            deaths.append(stats)
            
        for date_str, stats in data.get('recovered', {}).items():
            recovered.append(stats)
        
        # Create DataFrame
        df = pd.DataFrame({
            'date': pd.to_datetime(dates),
            'cases': cases,
            'deaths': deaths[:len(dates)],
            'recovered': recovered[:len(dates)]
        })
        df = df.sort_values('date')
        
        return df
    
    def _process_country_historical(self, data, days):
        """Process country-specific historical data"""
        if not data or 'timeline' not in data:
            return None
            
        timeline = data['timeline']
        dates = []
        cases = []
        deaths = []
        recovered = []
        
        for date_str, stats in timeline.get('cases', {}).items():
            dates.append(date_str)
            cases.append(stats)
            
        for date_str, stats in timeline.get('deaths', {}).items():
            deaths.append(stats)
            
        for date_str, stats in timeline.get('recovered', {}).items():
            recovered.append(stats)
        
        # Create DataFrame
        df = pd.DataFrame({
            'date': pd.to_datetime(dates),
            'cases': cases,
            'deaths': deaths[:len(dates)],
            'recovered': recovered[:len(dates)]
        })
        df = df.sort_values('date')
        
        # Add daily new cases and deaths
        df['new_cases'] = df['cases'].diff().fillna(0)
        df['new_deaths'] = df['deaths'].diff().fillna(0)
        
        return df
    
    def get_country_list(self):
        """Get list of all countries"""
        cache_key = "country_list"
        cached = self._get_cached_data(cache_key)
        if cached is not None:
            return cached
            
        try:
            response = requests.get(f"{self.base_url}/countries")
            response.raise_for_status()
            data = response.json()
            
            countries = [{'name': country['country'], 'code': country.get('countryInfo', {}).get('iso2', '')} 
                        for country in data]
            countries.sort(key=lambda x: x['name'])
            
            self._set_cache_data(cache_key, countries)
            return countries
        except requests.RequestException as e:
            print(f"Error fetching country list: {e}")
            return []
