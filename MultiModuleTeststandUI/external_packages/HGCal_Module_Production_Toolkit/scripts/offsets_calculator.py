from utils.center_finder import *
from utils.d_vector_finder import *
from utils.io_tool import get_offsets_raw_from_textfile, ragular_all_numbers, write_to_csv

import os
import yaml
import math

def get_angle_from_two_vectors(v1:dict, v2:dict) -> float:

    length_1 = math.sqrt( v1['d_vector_x'] ** 2 + v1['d_vector_y'] ** 2 )
    length_2 = math.sqrt( v2['d_vector_x'] ** 2 + v2['d_vector_y'] ** 2 )

    dot = v1['d_vector_x']*v2['d_vector_x'] + v1['d_vector_y']*v2['d_vector_y']

    cos_theta = dot / (length_1*length_2)

    return abs( math.acos(cos_theta) ) * 180. / math.pi

def calculate_centor_offsets(modules:dict, offsets_raw:dict) -> dict:

    with open(os.getenv('FRAMEWORK_PATH') + "/data/pcb.yaml", 'r') as pcb_correction_file:
        pcb_correction = yaml.safe_load(pcb_correction_file)

    with open(os.getenv('FRAMEWORK_PATH') + "/data/sensor.yaml", 'r') as sensor_correction_file:
        sensor_correction = yaml.safe_load(sensor_correction_file)

    with open(os.getenv('FRAMEWORK_PATH') + "/data/tray.yaml", 'r') as baseplate_correction_file:
        baseplate_correction = yaml.safe_load(baseplate_correction_file)

    offsets = {}

    for module in modules:

        module_list = module.split("-")

        module      = module_list[0]
        module_type = module_list[0][4:6]
        tray_index  = module_list[1]
        tray_side   = module_list[2]

        baseplate_centers = globals()[f"{module_type}_baseplate_center_finder"](offsets_raw, tray_side, baseplate_correction[tray_index])

        # Identify if the sensor or pcb exists. The program will calculate the center offset for only existing sensor or pcb.
        offsets[module] = {"center_offsets" : { "pcb":[0., 0.], "sensor":[0., 0.] }}

        try:
            pcb_centers       = globals()[f"{module_type}_pcb_center_finder"](offsets_raw, tray_side, pcb_correction[module_type])

            offsets[module]["center_offsets"]["pcb"] = \
                               [ ( pcb_centers   ["x"] - baseplate_centers["x"] )*(1. if tray_side == "R" else -1.),
                                 ( pcb_centers   ["y"] - baseplate_centers["y"] )*(1. if tray_side == "R" else -1.) ]
        except Exception as e:
            pass

        try:
            sensor_centers    = globals()[f"{module_type}_sensor_center_finder"](offsets_raw, tray_side, sensor_correction[module_type])

            offsets[module]["center_offsets"]["sensor"] = \
                           [ ( sensor_centers["x"] - baseplate_centers["x"] )*(1. if tray_side == "R" else -1.),
                             ( sensor_centers["y"] - baseplate_centers["y"] )*(1. if tray_side == "R" else -1.) ]
        except Exception as e:
            pass

    return offsets

def calculate_angle_offsets(modules:dict, offsets_raw:dict) -> dict:

    with open(os.getenv('FRAMEWORK_PATH') + "/data/sensor.yaml", 'r') as sensor_correction_file:
        sensor_correction = yaml.safe_load(sensor_correction_file)

    offsets = {}
    for module in modules:

        module_list = module.split("-")

        module      = module_list[0]
        module_type = module_list[0][4:6]
        tray_index  = module_list[1]
        tray_side   = module_list[2]

        baseplate_d_vector = globals()[f"{module_type}_baseplate_d_vector_finder"](offsets_raw, tray_side)

        # Identify if the sensor or pcb exists. The program will calculate the angle offset for only existing sensor or pcb.
        try:
            pcb_d_vector       = globals()[f"{module_type}_pcb_d_vector_finder"](offsets_raw, tray_side)
            pcb_angle_offsets  = get_angle_from_two_vectors(pcb_d_vector, baseplate_d_vector)

            # Assign the angle rotation direction (counterclockwise : "+", clockwise : "-")
            if pcb_d_vector['d_vector_y'] < baseplate_d_vector['d_vector_y']:
                pcb_angle_offsets = -pcb_angle_offsets

        except Exception as e:
            pcb_angle_offsets = 0.

        try:
            sensor_d_vector    = globals()[f"{module_type}_sensor_d_vector_finder"](offsets_raw, tray_side, sensor_correction[module_type])
            sensor_angle_offsets = get_angle_from_two_vectors(sensor_d_vector, baseplate_d_vector)

            # Assign the angle rotation direction (counterclockwise : "+", clockwise : "-")
            if sensor_d_vector['d_vector_y'] < baseplate_d_vector['d_vector_y']:
                sensor_angle_offsets = -sensor_angle_offsets

        except Exception as e:
            sensor_angle_offsets = 0.

        offsets[module] = {}
        offsets[module]["angle_offsets"] = {
                "pcb"    : pcb_angle_offsets,
                "sensor" : sensor_angle_offsets
                }

    return offsets

def offsets_calculator(modules:list, textfile:str) -> dict:

    module_offsets_raw = get_offsets_raw_from_textfile(os.getenv('FRAMEWORK_PATH') + f'/input/{textfile}', modules[0].split('-')[0][4:6])

    offsets = calculate_centor_offsets(modules, module_offsets_raw)
    offsets = ragular_all_numbers(offsets, factor=1000)

    angle_offsets = calculate_angle_offsets (modules, module_offsets_raw)
    angle_offsets = ragular_all_numbers(angle_offsets)

    for k, v in angle_offsets.items():
        offsets[k].update(v)

    return offsets

if __name__ == '__main__':

    modules = [
        "320MHR1WCNT0155-AT04-L",
        "320MHR1WCNT0156-AT04-R"
        ]


    txtfile = 'M222M223.txt'

    offsets = offsets_calculator(modules, txtfile)

    print(offsets)

    #write_to_csv(offsets, 'test.csv' )
