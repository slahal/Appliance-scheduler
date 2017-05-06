import pandas
import datetime
import numpy
import copy

from flask import Flask, request, g, render_template, Response, jsonify
from flask import session, flash, redirect, url_for, make_response

app = Flask(__name__)

xl = pandas.ExcelFile("HouseHoldElectricity.xlsx")

data_frame = xl.parse(xl.sheet_names[0], skiprows=3)


reduced_devices = {}


def calculate_power(current_power, percentage_decrease):
    """
    calculates the new power.
    """
    required_power = current_power - (current_power * percentage_decrease)/100.
    return int(required_power)


def make_round(x, base=5):
    """
    Rounds the time in interval of 5 min.
    """
    return int(base * round(float(x)/base))


def get_index(current_time):
    """
    Return index of the current timing.
    """
    current_hour = current_time.hour
    current_minute = make_round(current_time.minute)
    if current_minute == 60:
        current_minute = 00
    current_second = 00

    rounded_time = datetime.time(current_hour, current_minute, current_second)
    #rounded_time = datetime.time(06, 30, 00)

    idx = numpy.where(data_frame['Time'].values == rounded_time)
    #idx = numpy.where(data_frame['Time'].values == datetime.time(07, 05, current_second))

    return [idx[0][0], rounded_time]


def create_device_list(device, is_new):
    global reduced_devices
    length = len(reduced_devices)
    if is_new:
        reduced_devices[length] = [device]
    else:
        reduced_devices[length-1].append(device)


def subset_sum(numbers, target, min_power, partial=[]):
    """
    Displays the values and names of devices.
    Requested power is target.
    """
    s = sum(partial)

    # check if the partial sum is equals to target
    display_vals = {
        161: "FAN/AC",
        184: "Refrigerator/Microwave",
        230: "gyeser",
        207: "TV"
    }

    if min_power < 300:
        if s <= target:
            is_new = 1
            #print "%s = %s < %s" % (partial, sum(partial), target)
            for p in partial:
                if p in display_vals.keys():
                    create_device_list(display_vals[p], is_new)
                    is_new = 0
            #print
    else:
        if s <= target and s >= min_power:
            is_new = 1
            #print "%s = %s < %s" % (partial, sum(partial), target)
            for p in partial:
                if p in display_vals.keys():
                    create_device_list(display_vals[p], is_new)
                    is_new = 0
            #print
    if s >= target:
        return  # if we reach the number why bother to continue

    for i in range(len(numbers)):
        n = numbers[i]
        remaining = numbers[i+1:]
        subset_sum(remaining, target, min_power, partial + [n])


def main(percentage_decrease):
    """
    params:
        pdp: power decrease percentage.
        time: time at which they want to reduce the power.
    """
    current_time = datetime.datetime.now().time()
    idx, rounded_time = get_index(current_time)
    

    analyse_dict = {}

    device_list = []

    device = {
        "gyeser": {
            "power": 230,
            "active": data_frame['Gyeser'].values[idx]
        },
        "Refrigerator": {
            "power": 184,
            "active": data_frame['Refrigerator'].values[idx]
        },
        "Microwave": {
            "power": 184,
            "active": data_frame['Microwave'].values[idx]
        },
        "FAN": {
            "power": 161,
            "active": data_frame['FAN'].values[idx]
        },
        "AC": {
            "power": 161,
            "active": data_frame['AC'].values[idx]
        },
        "TV": {
            "power": 207,
            "active": data_frame['TV'].values[idx]
        }
    }

    for key, value in device.items():
        for i in range(value['active']):
            device_list.append(value['power'])

    current_power = data_frame['Power'].values[idx]
    required_power = calculate_power(current_power, percentage_decrease)
    if required_power < 200:
        min_power = required_power
    else:
        min_power = calculate_power(required_power, percentage_decrease*2)

    subset_sum(device_list, required_power, min_power)

    global reduced_devices
    if not reduced_devices:
        reduced_devices = {-1: "All devices should be turned off."}
    else:
        print reduced_devices


    final=copy.deepcopy(reduced_devices)
    reduced_devices = {}

    analyse_dict['required_power'] = required_power
    analyse_dict['current_power'] = current_power
    analyse_dict['current_time'] = current_time
    analyse_dict['min_power'] = min_power
    analyse_dict['rounded_time'] = rounded_time
    analyse_dict['reduced_devices'] = final

    return analyse_dict


# Flask routes.


@app.route('/')
def index():
    '''
    Entry point.
    '''
    #main(20)
    return render_template("index.html")


@app.route('/poweranalysis', methods=['GET', 'POST'])
def power_analyse():
    '''
    Entry point.
    '''
    if request.method == 'POST':
        percentage_decrease = int(request.form['percentage_decrease'])
        analyse_dict = main(percentage_decrease)
        return render_template("poweranalysis.html", analyse_dict=analyse_dict)
    return render_template("index.html")


@app.errorhandler(404)
def not_found(error):
    '''
    Handles if 404 occurs.
    '''
    return render_template("404.html")


if __name__ == "__main__":
    app.run()
