def list_average(coord_list:list) -> float:
    return sum(coord_list) / len(coord_list)

################################
# HD Full (2.2)
################################
def HF_pcb_center_finder( module_offsets_raw:dict, side:str, correction:dict ) -> dict :
    return {
                'x' : list_average(module_offsets_raw[side]['pcb']['x']),
                'y' : list_average(module_offsets_raw[side]['pcb']['y'])
            }

def HF_sensor_center_finder( module_offsets_raw:dict, side:str, correction:dict ) -> dict :
    return {
                'x' : list_average(module_offsets_raw[side]['sensor']['x']) - correction['x']*(1 if side == 'R' else -1.),
                'y' : list_average(module_offsets_raw[side]['sensor']['y']) - correction['y']*(1 if side == 'R' else -1.)
            }

def HF_baseplate_center_finder( module_offsets_raw:dict, side:str, correction:dict ) -> dict :
    return {
                'x' : module_offsets_raw['measured_ref']["x"] - (correction['Reference']["x"] - correction[side]["x"]),
                'y' : module_offsets_raw['measured_ref']["y"] - (correction['Reference']["y"] - correction[side]["y"])
            }

################################
# HD Left (1.1)
################################
def HL_pcb_center_finder( module_offsets_raw:dict, side:str, correction:dict ) -> dict :
    return {
                'x' : module_offsets_raw[side]['pcb']['x']['M4'] - correction['x']*(1 if side == 'R' else -1.),
                'y' : module_offsets_raw[side]['pcb']['y']['M4'] - correction['y']*(1 if side == 'R' else -1.),
            }

def HL_sensor_center_finder( module_offsets_raw:dict, side:str, correction:dict ) -> dict :
    return {
                'x' : list_average(module_offsets_raw[side]['sensor']['x'].values()) - correction['x']*(1 if side == 'R' else -1.),
                'y' : list_average(module_offsets_raw[side]['sensor']['y'].values()) - correction['y']*(1 if side == 'R' else -1.)
            }

def HL_baseplate_center_finder( module_offsets_raw:dict, side:str, correction:dict ) -> dict :
    return {
                'x' : module_offsets_raw['measured_ref']["x"] - (correction['Reference']["x"] - correction[side]["x"]),
                'y' : module_offsets_raw['measured_ref']["y"] - (correction['Reference']["y"] - correction[side]["y"])
            }

################################
# HD Right (1.1)
################################
def HR_pcb_center_finder( module_offsets_raw:dict, side:str, correction:dict ) -> dict :
    return {
                'x' : module_offsets_raw[side]['pcb']['x']['M4'] - correction['x']*(1 if side == 'R' else -1.),
                'y' : module_offsets_raw[side]['pcb']['y']['M4'] - correction['y']*(1 if side == 'R' else -1.),
            }

def HR_sensor_center_finder( module_offsets_raw:dict, side:str, correction:dict ) -> dict :
    return {
                'x' : list_average(module_offsets_raw[side]['sensor']['x'].values()) - correction['x']*(1 if side == 'R' else -1.),
                'y' : list_average(module_offsets_raw[side]['sensor']['y'].values()) - correction['y']*(1 if side == 'R' else -1.)
            }

def HR_baseplate_center_finder( module_offsets_raw:dict, side:str, correction:dict ) -> dict :
    return {
                'x' : module_offsets_raw['measured_ref']["x"] - (correction['Reference']["x"] - correction[side]["x"]),
                'y' : module_offsets_raw['measured_ref']["y"] - (correction['Reference']["y"] - correction[side]["y"])
            }

################################
# HD Bottom (1.1)
################################
def HB_pcb_center_finder( module_offsets_raw:dict, side:str, correction:dict ) -> dict :
    return {
                'x' : module_offsets_raw[side]['pcb']['x']['FD4'] - correction['x']*(1 if side == 'R' else -1.),
                'y' : module_offsets_raw[side]['pcb']['y']['FD4'] - correction['y']*(1 if side == 'R' else -1.),
            }

def HB_sensor_center_finder( module_offsets_raw:dict, side:str, correction:dict ) -> dict :

    # Calculate the center of M15 and M24
    center_x = ( module_offsets_raw[side]['sensor']['x']['M15'] + module_offsets_raw[side]['sensor']['x']['M24'] )*0.5
    center_y = ( module_offsets_raw[side]['sensor']['y']['M15'] + module_offsets_raw[side]['sensor']['y']['M24'] )*0.5

    # Unit of the direction vector
    v_direct_x = module_offsets_raw[side]['sensor']['x']['M15'] - module_offsets_raw[side]['sensor']['x']['M24']
    v_direct_y = module_offsets_raw[side]['sensor']['y']['M15'] - module_offsets_raw[side]['sensor']['y']['M24']
    length_direct = ( v_direct_x**2 + v_direct_y**2 ) ** 0.5
    v_direct_x = v_direct_x / length_direct
    v_direct_y = v_direct_y / length_direct

    # Unit of the normal vector
    v_normal_x = v_direct_y
    v_normal_y = -v_direct_x

    # Make sure the normal vector points up when putting the module on the right and points down when putting the module on the left
    if (side == 'R' and v_normal_y < 0.) or (side == 'L' and v_normal_y > 0.):
        v_normal_x = (-1) * v_normal_x
        v_normal_y = (-1) * v_normal_y

    return {
                'x' : center_x + v_normal_x*correction['length'],
                'y' : center_y + v_normal_y*correction['length']
           }

def HB_baseplate_center_finder( module_offsets_raw:dict, side:str, correction:dict ) -> dict :
    return {
                'x' : module_offsets_raw['measured_ref']["x"] - (correction['Reference']["x"] - correction[side]["x"]),
                'y' : module_offsets_raw['measured_ref']["y"] - (correction['Reference']["y"] - correction[side]["y"])
            }

################################
# LD Right (1.2)
################################
def LR_pcb_center_finder( module_offsets_raw:dict, side:str, correction:dict ) -> dict :
    return {
                'x' : module_offsets_raw[side]['pcb']['x']['FD4'] - correction['x']*(1 if side == 'R' else -1.),
                'y' : module_offsets_raw[side]['pcb']['y']['FD4'] - correction['y']*(1 if side == 'R' else -1.),
            }

def LR_sensor_center_finder( module_offsets_raw:dict, side:str, correction:dict ) -> dict :
    return {
                'x' : list_average(module_offsets_raw[side]['sensor']['x'].values()) - correction['x']*(1 if side == 'R' else -1.),
                'y' : list_average(module_offsets_raw[side]['sensor']['y'].values()) - correction['y']*(1 if side == 'R' else -1.)
            }

def LR_baseplate_center_finder( module_offsets_raw:dict, side:str, correction:dict ) -> dict :
    return {
                'x' : module_offsets_raw['measured_ref']["x"] - (correction['Reference']["x"] - correction[side]["x"]),
                'y' : module_offsets_raw['measured_ref']["y"] - (correction['Reference']["y"] - correction[side]["y"])
            }

################################
# LD Left (1.2)
################################
def LL_pcb_center_finder( module_offsets_raw:dict, side:str, correction:dict ) -> dict :
    return {
                'x' : module_offsets_raw[side]['pcb']['x']['FD2'] - correction['x']*(1 if side == 'R' else -1.),
                'y' : module_offsets_raw[side]['pcb']['y']['FD2'] - correction['y']*(1 if side == 'R' else -1.),
            }

def LL_sensor_center_finder( module_offsets_raw:dict, side:str, correction:dict ) -> dict :
    return {
                'x' : list_average(module_offsets_raw[side]['sensor']['x'].values()) - correction['x']*(1 if side == 'R' else -1.),
                'y' : list_average(module_offsets_raw[side]['sensor']['y'].values()) - correction['y']*(1 if side == 'R' else -1.)
            }

def LL_baseplate_center_finder( module_offsets_raw:dict, side:str, correction:dict ) -> dict :
    return {
                'x' : module_offsets_raw['measured_ref']["x"] - (correction['Reference']["x"] - correction[side]["x"]),
                'y' : module_offsets_raw['measured_ref']["y"] - (correction['Reference']["y"] - correction[side]["y"])
            }

################################
# LD Five (1.1)
################################
def L5_pcb_center_finder( module_offsets_raw:dict, side:str, correction:dict ) -> dict :
    return {
                'x' : module_offsets_raw[side]['pcb']['x']['FD4'] - correction['x']*(1 if side == 'R' else -1.),
                'y' : module_offsets_raw[side]['pcb']['y']['FD4'] - correction['y']*(1 if side == 'R' else -1.),
            }

def L5_sensor_center_finder( module_offsets_raw:dict, side:str, correction:dict ) -> dict :
    return {
                'x' : list_average(module_offsets_raw[side]['sensor']['x'].values()) - correction['x']*(1 if side == 'R' else -1.),
                'y' : list_average(module_offsets_raw[side]['sensor']['y'].values()) - correction['y']*(1 if side == 'R' else -1.)
            }

def L5_baseplate_center_finder( module_offsets_raw:dict, side:str, correction:dict ) -> dict :
    return {
                'x' : module_offsets_raw['measured_ref']["x"] - (correction['Reference']["x"] - correction[side]["x"]),
                'y' : module_offsets_raw['measured_ref']["y"] - (correction['Reference']["y"] - correction[side]["y"])
            }

################################
# LD Bottom (2.0)
################################
def LB_pcb_center_finder( module_offsets_raw:dict, side:str, correction:dict ) -> dict :
    return {
                'x' : module_offsets_raw[side]['pcb']['x']['M4'] - correction['x']*(1 if side == 'R' else -1.),
                'y' : module_offsets_raw[side]['pcb']['y']['M4'] - correction['y']*(1 if side == 'R' else -1.),
            }

def LB_sensor_center_finder( module_offsets_raw:dict, side:str, correction:dict ) -> dict :

    # Calculate the center of M11 and M18
    center_x = ( module_offsets_raw[side]['sensor']['x']['M11'] + module_offsets_raw[side]['sensor']['x']['M18'] )*0.5
    center_y = ( module_offsets_raw[side]['sensor']['y']['M11'] + module_offsets_raw[side]['sensor']['y']['M18'] )*0.5

    return {
                'x' : center_x - correction['x']*(1 if side == 'R' else -1.),
                'y' : center_y - correction['y']*(1 if side == 'R' else -1.)
            }

def LB_baseplate_center_finder( module_offsets_raw:dict, side:str, correction:dict ) -> dict :
    return {
                'x' : module_offsets_raw['measured_ref']["x"] - (correction['Reference']["x"] - correction[side]["x"]),
                'y' : module_offsets_raw['measured_ref']["y"] - (correction['Reference']["y"] - correction[side]["y"])
            }

################################
# LD Top (1.1)
################################
def LT_pcb_center_finder( module_offsets_raw:dict, side:str, correction:dict ) -> dict :

    # Calculate the center of FD1 and FD3
    center_x = ( module_offsets_raw[side]['pcb']['x']['FD1'] + module_offsets_raw[side]['pcb']['x']['FD3'] )*0.5
    center_y = ( module_offsets_raw[side]['pcb']['y']['FD1'] + module_offsets_raw[side]['pcb']['y']['FD3'] )*0.5

    return {
                'x' : center_x - correction['x']*(1 if side == 'R' else -1.),
                'y' : center_y - correction['y']*(1 if side == 'R' else -1.),
            }

def LT_sensor_center_finder( module_offsets_raw:dict, side:str, correction:dict ) -> dict :

    # Calculate the center of M10 and M19
    center_x = ( module_offsets_raw[side]['sensor']['x']['M10'] + module_offsets_raw[side]['sensor']['x']['M19'] )*0.5
    center_y = ( module_offsets_raw[side]['sensor']['y']['M10'] + module_offsets_raw[side]['sensor']['y']['M19'] )*0.5

    return {
                'x' : center_x - correction['x']*(1 if side == 'R' else -1.),
                'y' : center_y - correction['y']*(1 if side == 'R' else -1.)
            }

def LT_baseplate_center_finder( module_offsets_raw:dict, side:str, correction:dict ) -> dict :
    return {
                'x' : module_offsets_raw['measured_ref']["x"] - (correction['Reference']["x"] - correction[side]["x"]),
                'y' : module_offsets_raw['measured_ref']["y"] - (correction['Reference']["y"] - correction[side]["y"])
            }
