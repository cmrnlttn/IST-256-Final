#it takes 10-20 seconds to run...

#APIs used:
#https://developers.amadeus.com/self-service/category/air/api-doc/flight-offers-search
#https://rapidapi.com/apidojo/api/hotels4/
#https://openweathermap.org/api/one-call-api
import requests
import json
import folium 
from IPython.display import display, HTML
import pandas as pd
from __future__ import print_function
from ipywidgets import interact, interactive, fixed, interact_manual
import ipywidgets as widgets
from datetime import datetime
import string

display(HTML("<h1><strong>Cam's Vacation Planner</strong></h1><p>Please fill out the following information to get started!</p>"))
def main(start_date, end_date, Origin, Search):
    num_adults = '1'
    token = get_token()
    print('Token Accquired...')
    hotel_ids, hotel_names = hotel_search(start_date, end_date, Search, num_adults)
    print('Hotel IDs Accquired...')
    try:
        bundled_prices, per_night_prices, amenities_lists, hotel_lats, hotel_lons = hotel_details(hotel_ids, start_date, end_date, num_adults)
    except KeyError:
        print('ERROR! Please check your selected dates')
        return
    print('Gathering Prices... ')
    origin_lat, origin_lon = geocode(Origin)
    origin_airport, origin_3 = airport_code_getter(origin_lat, origin_lon, token)
    airport, destination_3 = airport_code_getter(hotel_lats[0], hotel_lons[0], token)
    print('Waiting in TSA Line...')
    depart_flight = flight_search(token, origin_3, destination_3, start_date, num_adults, nonstop_bool, max_results)
    print('Grabbing a Coffee...')
    Search = string.capwords(Search)
    display(HTML(f"<h2><strong>Hotels in {Search}</strong></h2>"))
    hotels_map(hotel_lats, hotel_lons, hotel_names, per_night_prices, bundled_prices, amenities_lists)
    display(HTML(f"<h2>Departing Flights on {start_date} From {origin_3} to {destination_3}</h2>"))
    display(flight_display(*depart_flight))
    return_flight = flight_search(token,  destination_3, origin_3, start_date, num_adults, nonstop_bool, max_results)
    display(HTML(f"<h2>Returning Flights on {end_date} From {destination_3} to {origin_3}</h2>"))
    display(flight_display(*return_flight))
    highs, lows, dates, c_of_rain, description = weather(hotel_lats, hotel_lons)
    display(HTML(f"<h2><strong>{Search} 8 Day Weather Forecast</strong></h2>"))
    display(weather_display(highs, lows, dates, c_of_rain, description))
    return
num_results = '10' #number of hotel results
nonstop_bool = 'false'
max_results = 5 #number for flight results

def get_token(): #gets the auth token for the amadues APIs
    key = 'NosXauZkIe36P8L4WHZ15hefX0etfeG1'
    secret = 'ntenfsb1HH8m9tsW'
    auth_url = 'https://test.api.amadeus.com/v1/security/oauth2/token'
    auth_headers = {'Content-Type' : 'application/x-www-form-urlencoded'}
    data = {'grant_type' : 'client_credentials', 'client_id' : key, 'client_secret' : secret}
    response = requests.request('POST', auth_url, headers=auth_headers, data=data)
    token = json.loads(response.text)['access_token']
    return token
    
def geocode(location): #gets the lat and long for the origin city 
    key = 'e4b996f13773a2dd179dab40c1d71492'
    url = 'http://api.positionstack.com/v1/forward'
    params ={'access_key':key,
    'query': location,
    'country': 'US',
    'limit': 1,}
    response = requests.request("GET", url, params=params)
    json_data = json.loads(response.text)
    return json_data['data'][0]['latitude'], json_data['data'][0]['longitude']
    
def hotel_search(start_date, end_date, Search, num_adults): #uses input params to find hotels in the destination
    #city, returns all of the hotel IDs
    search_url = "https://hotels4.p.rapidapi.com/locations/v2/search"
    querystring = {"query": Search,"locale":"en_US","currency":"USD"}
    headers = {"X-RapidAPI-Host": "hotels4.p.rapidapi.com",
        "X-RapidAPI-Key": "24498f5024msh4c0ee081635aa1ep1ae140jsnaac63c2f286b"}
    response = requests.request("GET", search_url, headers=headers, params=querystring)
    json_data = json.loads(response.text)
    destination_id = json_data['suggestions'][0]['entities'][0]['destinationId']
    
    list_url = "https://hotels4.p.rapidapi.com/properties/list"
    querystring = {"destinationId": destination_id,"pageNumber":"1","pageSize": num_results,"checkIn": start_date,
                   "checkOut": end_date,"adults1":num_adults,"sortOrder":"BEST_SELLER","locale":"en_US","currency":"USD"}
    response = requests.request("GET", list_url, headers=headers, params=querystring)
    json_data = json.loads(response.text)
    hotel_ids = []
    hotel_names = []
    for ids in json_data['data']['body']['searchResults']['results']:
        hotel_ids.append(ids['id'])
        hotel_names.append(ids['name'])
        
    return hotel_ids, hotel_names

def hotel_details(hotel_ids, start_date, end_date, num_adults): #passes the list of hotel 
    #IDs, gathers details about each hotel and returns details
    url = "https://hotels4.p.rapidapi.com/properties/get-details"
    headers = {"X-RapidAPI-Host": "hotels4.p.rapidapi.com",
        "X-RapidAPI-Key": "24498f5024msh4c0ee081635aa1ep1ae140jsnaac63c2f286b"}
    bundled_prices = []
    per_night_prices = []
    amenities_lists = []
    hotel_lats = []
    hotel_lons=[]
    for hotel_id in hotel_ids:
        querystring = {"id": hotel_id,"checkIn": start_date,"checkOut": end_date,"adults1": num_adults,
                       "currency":"USD","locale":"en_US"}
        response = requests.request("GET", url, headers=headers, params=querystring)
        json_data = json.loads(response.text)
        bundled_prices.append(json_data['data']['body']['propertyDescription']
                              ['featuredPrice']['fullyBundledPricePerStay'])
        per_night_prices.append(json_data['data']['body']['propertyDescription']
                                ['featuredPrice']['currentPrice']['plain'])
        amenities_lists.append(json_data['data']['body']['overview']['overviewSections'][0]['content'])
        hotel_lats.append(json_data['data']['body']['pdpHeader']['hotelLocation']['coordinates']['latitude'])
        hotel_lons.append(json_data['data']['body']['pdpHeader']['hotelLocation']['coordinates']['longitude'])
    
    return bundled_prices, per_night_prices, amenities_lists, hotel_lats, hotel_lons

#displays all the hotel info on a folium map 
def hotels_map(hotel_lats, hotel_lons, hotel_names, prices_per_night, bundled_prices, amenities_lists):
    map_center = (hotel_lats[0], hotel_lons[0])
    hotel_map = folium.Map(location=map_center, zoom_start=11)
    for lat, lon, name, ppn, bundle, amen in zip(hotel_lats, hotel_lons, hotel_names, prices_per_night, 
                                      bundled_prices, amenities_lists):
        html = f"""<h4>{name}</h4> <h5>Price per night: ${ppn}</h5> <h6>Total Price w/ Fees: ${bundle}
        </h6> <br> <h6>Amentities:</h6>"""
        for line in amen:
            html+=str(line)
            html+='<br>'
        pos = (lat, lon)
        marker = folium.Marker(location=pos,
                              popup=folium.Popup(html,max_width=250))
        hotel_map.add_child(marker)
    display(hotel_map)
    
def aiti_code(aiti): #references the table, finds the row with the AITI code and returns the actual airline name 
    flight_df = pd.read_html('https://aspm.faa.gov/aspmhelp/index/ASQP__Carrier_Codes_and_Names.html')
    aiti_df = flight_df[0]
    
    for i, row in aiti_df.iterrows():
        if row[0] == aiti:
            return(row[2])

#looks up avalible plane tickets for the depart and return days 
def flight_search(token, origin_3, dest, day, num_adults, nonStop, maxresults):
    url = 'https://test.api.amadeus.com/v2/shopping/flight-offers?'
    query = {'originLocationCode':origin_3,'destinationLocationCode':dest,'departureDate':day, 
             'adults':num_adults,'nonStop':nonStop,'max':maxresults, 'currencyCode': 'USD'}
    headers = {'Authorization': 'Bearer '+token}
    response = requests.request("GET", url, headers=headers, params=query)
    json_data = json.loads(response.text)
    flight_nums = []
    airline = []
    departs = []
    arrives = []
    time = []
    stops = []
    flight_price = []
    for i in json_data['data']:
        flight_num = str(i['itineraries'][0]['segments'][0]['number'])
        if flight_num not in flight_nums:  #without checking a flight_nums list it was returning duplicates
            aiti = i['itineraries'][0]['segments'][0]['carrierCode']
            flight_nums.append(flight_num)
            airline.append(aiti_code(aiti).split()[0])
            departs.append((i['itineraries'][0]['segments'][0]['departure']['at'])[12:-3])
            arrives.append((i['itineraries'][0]['segments'][0]['arrival']['at'])[12:-3])
            time.append((i['itineraries'][0]['duration'])[2:])
            stops.append(len((i['itineraries'][0]['segments']))-1)
            flight_price.append(i['price']['total'])
    return flight_nums, airline, departs, arrives, time, stops, flight_price

def airport_code_getter(lat, lon, token): #searches for the nearest aiport to a location, and returns 
    #the 3 letter airport code, i need this for the flight search inputs
    url = "https://test.api.amadeus.com/v1/reference-data/locations/airports?"
    query = {'latitude': lat, 'longitude': lon, 'page[limit]': 2}
    headers = {"accept": "application/vnd.amadeus+json", 'Authorization': 'Bearer '+token}
    response = requests.request("GET", url, headers=headers, params=query)
    json_data = json.loads(response.text)
    airport = json_data['data'][0]['name']
    name_3 = json_data['data'][0]['iataCode']
    return airport, name_3

#displays plane ticket info in a table
def flight_display(flight_nums, airline, departs, arrives, time, stops, flight_price): #makes a table of flight info
    for i in range(len(flight_price)):
        flight_price[i] = '$'+str(flight_price[i])
    flight_infos = [flight_nums, airline, departs, arrives, time, stops, flight_price]
    df = pd.DataFrame(flight_infos, index=['Flight#', 'Airline', 'Depart', 'Arrive', 'Flight Time', '# of Stops', 'Price $'],
                     columns=range(len(flight_nums)+1)[1:])
    return df.T

def weather(hotel_lats, hotel_lons): #gets weather forecast for destination city 
    url = 'https://api.openweathermap.org/data/2.5/onecall?'
    key = '2730b7018f493b4ba2835cc75a24e9de'
    query = {'lat':hotel_lats[0], 'lon':hotel_lons[0], 'exclude':'minutely, hourly', 'units':'imperial','appid':key}
    response = requests.request("GET", url, params=query)
    json_data = json.loads(response.text)
    highs = []
    lows = []
    dates = []
    c_of_rain = []
    description = []
    for day in json_data['daily']:
        highs.append(day['temp']['max'])
        lows.append(day['temp']['min'])
        dates.append(datetime.fromtimestamp(int(day['dt'])).strftime("%m/%d"))
        c_of_rain.append(day['pop'])
        description.append(day['weather'][0]['description'])
    return highs, lows, dates, c_of_rain, description

#displays forcast in table
def weather_display(highs, lows, dates, c_of_rain, description):
    for i in range(len(description)):
        description[i] = string.capwords(description[i])
        highs[i] = str(round(int(highs[i])))+'°F'
        lows[i] = str(round(int(lows[i])))+'°F'
        c_of_rain[i] = str(round(c_of_rain[i]*100))+'%'
    forecast = [dates, description, highs, lows, c_of_rain]
    df = pd.DataFrame(forecast, index=['Date', 'Forecast', 'High', 'Low', '% of Rain'],
                     columns=range(len(highs)+1)[1:])
    return df.T
interact_manual(main, Origin='', Search='', 
                start_date=widgets.DatePicker(description='Start: ', disabled=False), 
                end_date=widgets.DatePicker(description='End: ', disabled=False))