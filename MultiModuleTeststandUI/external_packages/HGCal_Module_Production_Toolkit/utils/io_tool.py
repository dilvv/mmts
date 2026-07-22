import re
import csv
import copy
import numpy as np

template_HF = {
    "L" : {

        "pcb" : {
            "x" : [],
            "y" : []
        },
        "sensor" : {
            "x" : [],
            "y" : []
        }
    },
    "R" : {
        "pcb" : {
            "x" : [],
            "y" : []
        },
        "sensor" : {
            "x" : [],
            "y" : []
        }
    },
    "measured_ref" : {
        "x" : 0.,
        "y" : 0.
    },
    "measured_sup_ref" : {
        "x" : 0.,
        "y" : 0.
    }
}

template = {
    "L" : {

        "pcb" : {
            "x" : {},
            "y" : {}
        },
        "sensor" : {
            "x" : {},
            "y" : {}
        }
    },
    "R" : {
        "pcb" : {
            "x" : {},
            "y" : {}
        },
        "sensor" : {
            "x" : {},
            "y" : {}
        }
    },
    "measured_ref" : {
        "x" : 0.,
        "y" : 0.
    },
    "measured_sup_ref" : {
        "x" : 0.,
        "y" : 0.
    }
}

def get_offsets_raw_from_textfile(filename:str, module_type:str) -> dict:

    module_offsets_raw = copy.deepcopy(template)

    if module_type == 'HF':
        module_offsets_raw = copy.deepcopy(template_HF)

    with open(filename, 'r') as f:

        for line in f.readlines():
            # Catch measured reference points
            for coord in ['X', 'Y']:
                if line.find(f"TTT1.{coord}") != -1:
                    module_offsets_raw["measured_ref"][coord.lower()] = float( line.split()[3] )
                elif line.find(f"TTT2.{coord}") != -1:
                    module_offsets_raw["measured_sup_ref"][coord.lower()] = float( line.split()[3] )

            if module_type == 'HF':
                for side in ["L", "r"]:
                    for material in ["sensor", "pcb"]:
                        for coord in ['X', 'Y']:
                            if re.search(f"{side}{material[0].capitalize()}[0-9].{coord}", line):
                                module_offsets_raw[side.capitalize()][material][coord.lower()].append(float(line.split()[3]))

            elif module_type == 'HL' or module_type == 'HR':
                for side in ["L", "R"]:
                    for material in ["sensor", "pcb"]:
                        for coord in ['X', 'Y']:
                            if re.search(f"{side}_{material}_M(0?[1-9]|[1-9][0-9]).{coord}", line):
                                module_offsets_raw[side.capitalize()][material][coord.lower()][line.split()[1].split('_')[2].split('.')[0]]=float(line.split()[3])

            elif module_type == 'LL' or module_type == 'LT':
                for side in ["L", "R"]:
                    for coord in ['X', 'Y']:
                        if re.search(f"{side}_Sensor_M(0?[1-9]|[1-9][0-9]).{coord}", line):
                            module_offsets_raw[side.capitalize()]['sensor'][coord.lower()][line.split()[1].split('_')[2].split('.')[0]]=float(line.split()[3])
                        if re.search(f"{side}_FD(0?[1-9]|[1-9][0-9]).{coord}", line):
                            module_offsets_raw[side.capitalize()]['pcb'][coord.lower()][line.split()[1].split('_')[1].split('.')[0]]=float(line.split()[3])

            elif module_type == 'LB':
                for side in ["L", "R"]:
                    for coord in ['X', 'Y']:
                        if re.search(f"{side}_sensor_M(0?[1-9]|[1-9][0-9]).{coord}", line):
                            module_offsets_raw[side.capitalize()]['sensor'][coord.lower()][line.split()[1].split('_')[2].split('.')[0]]=float(line.split()[3])
                        if re.search(f"{side}_M(0?[1-9]|[1-9][0-9]).{coord}", line):
                            module_offsets_raw[side.capitalize()]['pcb'][coord.lower()][line.split()[1].split('_')[1].split('.')[0]]=float(line.split()[3])

            elif module_type == 'HB' or module_type == 'LR' or module_type == 'L5':

                word = { 'sensor' : 'M', 'pcb' : 'FD' }

                for side in ["L", "R"]:
                    for material in ["sensor", "pcb"]:
                        for coord in ['X', 'Y']:
                            if re.search(f"{side}_{word[material]}(0?[1-9]|[1-9][0-9]).{coord}", line):
                                module_offsets_raw[side.capitalize()][material][coord.lower()][line.split()[1].split('_')[1].split('.')[0]]=float(line.split()[3])

    return module_offsets_raw

def get_flatness_raw_from_textfile(filename:str, tray_side:str) -> tuple:

    x = []
    y = []
    z = []

    with open(filename) as f:

        start = False
        for line in f.readlines():
            if re.search(f'Step Name: Plane_AT0[0-9]_{tray_side}_[Mm]odule', line) or re.search(f'Feature Name: Plane_{tray_side}', line):
                start = True
                continue

            if line.find('Focus1') != -1 and start:
                line_list = line.split()
                x.append(line_list[2])
                y.append(line_list[3])
                z.append(line_list[4])

            elif len(x) > 0:
                break

    x = np.array(x, dtype='float64')
    y = np.array(y, dtype='float64')
    z = np.array(z, dtype='float64')

    return x, y, z

def ragular_all_numbers(obj, factor:float = 1.):
    if isinstance(obj, dict):
        return {k: ragular_all_numbers(v, factor) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [ragular_all_numbers(v, factor) for v in obj]
    elif isinstance(obj, (int, float)):
        return round(obj*factor, 4)
    else:
        return obj

def write_to_csv(module_qc_dict: dict, outfile, which:str ='all') -> None :

    module_list = []

    fields = [
            'module',
            'sensor_center_offset_x',
            'sensor_center_offset_y',
            'pcb_center_offset_x',
            'pcb_center_offset_y',
            'pcb_to_sensor_center_offset_x',
            'pcb_to_sensor_center_offset_y',
            'sensor_angle_offset',
            'pcb_angle_offset',
            "Vacuum_thickness",
            "Vacuum_min_height",
            "Vacuum_max_height",
            "Vacuum_flatness",
#            "NoVacuum_thickness",
#            "NoVacuum_min_height",
#            "NoVacuum_max_height",
#            "NoVacuum_flatness",
        ]

    for module_name, module_qc in module_qc_dict.items():

        module_list.append({
            fields[0] : module_name,
            fields[1] : module_qc['center_offsets']['sensor'][0],
            fields[2] : module_qc['center_offsets']['sensor'][1],
            fields[3] : module_qc['center_offsets']['pcb'][0],
            fields[4] : module_qc['center_offsets']['pcb'][1],
            fields[5] : module_qc['center_offsets']['pcb'][0] - module_qc['center_offsets']['sensor'][0],
            fields[6] : module_qc['center_offsets']['pcb'][1] - module_qc['center_offsets']['sensor'][1],
            fields[7] : module_qc['angle_offsets']['sensor'],
            fields[8] : module_qc['angle_offsets']['pcb'],
            fields[9] : module_qc['Vacuum']['thickness'],
            fields[10] : module_qc['Vacuum']['min_height'],
            fields[11] : module_qc['Vacuum']['max_height'],
            fields[12] : module_qc['Vacuum']['flatness'],
#            fields[11] : module_qc['NoVacuum']['thickness'],
#            fields[12] : module_qc['NoVacuum']['min_height'],
#            fields[13] : module_qc['NoVacuum']['max_height'],
#            fields[14] : module_qc['NoVacuum']['flatness'],
            })

    with open(outfile, mode='w', newline='') as file:
        writer = csv.DictWriter(file, fieldnames=fields)
        writer.writeheader()

        for row in module_list:
            writer.writerow(row)
