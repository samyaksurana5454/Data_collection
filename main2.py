import folium
import smartcar
from flask import Flask, redirect, request, jsonify, render_template
from flask_cors import CORS
import csv
import time
import schedule
import threading


app = Flask(__name__)
CORS(app)

def write_to_csv(data):
    with open('vehicle_car_data.csv', mode='a') as file:
        writer = csv.writer(file)
        writer.writerow(data)


# define a function that takes latitude and longitude as input and returns a folium map
def create_map(latitude, longitude, icon_image_url):
    # create a custom marker icon using the car image
    car_icon = folium.features.CustomIcon(
        icon_image=icon_image_url,
        icon_size=(50, 50)
    )

    # create a folium map centered at the given latitude and longitude
    mylocation = [latitude, longitude]
    my_map = folium.Map(mylocation, zoom_start=15)

    # add a marker for the car location using the custom marker icon
    folium.Marker(
        mylocation,
        popup='<i>Location</i>',
        icon=car_icon
    ).add_to(my_map)

    # return the folium map object
    return my_map

def update_location(lock, access):
    with lock:
        # get the latest location data from the vehicle
        vehicles = smartcar.get_vehicles(access.access_token)
        location = vehicles.vehicles[0].location()

        # write the location data to a CSV file
        with open("vehicle_car_data.csv", "a", newline="") as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow([location.latitude, location.longitude])

def run_scheduler(lock, access):
    # schedule the update_location function to run every second
    schedule.every(1).seconds.do(update_location, lock=lock, access=access)

    # keep running the scheduler indefinitely
    while True:
        schedule.run_pending()
        time.sleep(10)

# global variable to save our access_token
access = None
lock = threading.Lock()
client = smartcar.AuthClient(
    client_id="0079ad0b-1c9b-4b74-ac0d-1b39619a4014",
    client_secret="fb5b3be4-0859-4f40-bad0-2b2fa203f41b",
    redirect_uri="http://localhost:8000/exchange",
    mode="simulated",

)
@app.route("/")
def hello_world():
    return '<p><button onclick="window.location.href=\'/login\'">Login</button></p>'

@app.route("/login", methods=["GET"])
def login():
    scope = ['read_vehicle_info', 'read_odometer', 'read_location', 'read_tires', 'read_battery', 'read_charge']
    auth_url = client.get_auth_url(scope)
    return redirect(auth_url)

@app.route('/exchange', methods=['GET'])
def exchange():
    code = request.args.get('code')
    global access
    access = client.exchange_code(code)
    return redirect('/vehicle')

@app.route('/vehicle', methods=['GET'])
def get_vehicle():
    global access
    vehicles = smartcar.get_vehicles(access.access_token)
    vehicle_ids = vehicles.vehicles
    vehicle = smartcar.Vehicle(vehicle_ids[0], access.access_token)

    # refresh the data every second and write it to the CSV file
    while True:
        attributes = vehicle.attributes()
        odometer = vehicle.odometer()
        location = vehicle.location()
        pressure = vehicle.tire_pressure()
        battery=vehicle.battery()
        capacity=vehicle.battery_capacity()
        charge=vehicle.charge()
        data = [attributes.make, attributes.model, attributes.year, odometer.distance, location.latitude, location.longitude, pressure.back_left, pressure.back_right, pressure.front_left, pressure.front_right,battery.range,battery.percent_remaining,capacity.capacity,charge.is_plugged_in, charge.state]
        write_to_csv(data)
        time.sleep(1)



    car_image_url = 'C:/Users/pragy/Downloads/icons8-carpool-30.png'
    my_map = create_map(location.latitude, location.longitude, car_image_url)


    map_html = my_map._repr_html_()


    run_scheduler()


    return render_template('vehicle.html',
                           make=attributes.make,
                           model=attributes.model,
                           year=attributes.year,
                           distance=odometer.distance,
                           latitude=location.latitude,
                           longitude=location.longitude,
                           back_left_pressure=pressure.back_left,
                           back_right_pressure=pressure.back_right,
                           front_left_pressure=pressure.front_left,
                           front_right_pressure=pressure.front_right,
                           Battery_range=battery.range,
                           percent_remaining=battery.percent_remaining,
                           battery_capacity=capacity.capacity,
                           plugged_in=charge.is_plugged_in,
                           charge_status=charge.state,
                           map_html=map_html)

@app.errorhandler(Exception)
def handle_error(error):
    response = jsonify({"error": str(error)})
    response.status_code = 500
    return response

if __name__ == "__main__":
    app.run(port=8000)
    # authenticate and get the access token
    auth_url = client.get_auth_url()
    print("Go to the following URL to authorize access:")
    print(auth_url)
    code = input("Enter the authorization code: ")
    access = client.exchange_code(code)

    # start the scheduler
    run_scheduler()
