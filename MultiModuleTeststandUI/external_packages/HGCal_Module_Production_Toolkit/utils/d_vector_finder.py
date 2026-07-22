import math

################################
# HD Full (2.2)
################################
def HF_pcb_d_vector_finder( module_offsets_raw:dict, side:str ) -> dict :

    # HF pcb
    # center1 = (P1+P3)/2
    # center2 = (P2+P4)/2
    # direction vector = center1 - center2
    local_center1_x = ( module_offsets_raw[side]['pcb']['x'][0] + module_offsets_raw[side]['pcb']['x'][2] ) * 0.5
    local_center1_y = ( module_offsets_raw[side]['pcb']['y'][0] + module_offsets_raw[side]['pcb']['y'][2] ) * 0.5
    local_center2_x = ( module_offsets_raw[side]['pcb']['x'][1] + module_offsets_raw[side]['pcb']['x'][3] ) * 0.5
    local_center2_y = ( module_offsets_raw[side]['pcb']['y'][1] + module_offsets_raw[side]['pcb']['y'][3] ) * 0.5

    d_vector_x = local_center1_x - local_center2_x
    d_vector_y = local_center1_y - local_center2_y

    # Always plus for x component
    if d_vector_x < 0.:
        d_vector_x = - d_vector_x
        d_vector_y = - d_vector_y

    length = math.sqrt( d_vector_x**2 + d_vector_y**2 )

    # Return unit vector
    return {
                'd_vector_x' : d_vector_x/length,
                'd_vector_y' : d_vector_y/length
            }

def HF_sensor_d_vector_finder( module_offsets_raw:dict, side:str, correction = None ) -> dict :

    # HF sensor
    # direction vector = S1 - S2
    d_vector_x = module_offsets_raw[side]['sensor']['x'][0] - module_offsets_raw[side]['sensor']['x'][1]
    d_vector_y = module_offsets_raw[side]['sensor']['y'][0] - module_offsets_raw[side]['sensor']['y'][1]

    # Always plus for x component
    if d_vector_x < 0.:
        d_vector_x = - d_vector_x
        d_vector_y = - d_vector_y

    # Angle rotation as correction
    theta = correction['theta'] * math.pi / 180.
    d_vector_x_corr = d_vector_x * math.cos(theta) - d_vector_y * math.sin(theta)
    d_vector_y_corr = d_vector_y * math.cos(theta) + d_vector_x * math.sin(theta)

    length = math.sqrt( d_vector_x_corr**2 + d_vector_y_corr**2 )

    # Return unit vector
    return {
                'd_vector_x' : d_vector_x_corr/length,
                'd_vector_y' : d_vector_y_corr/length
            }

def HF_baseplate_d_vector_finder( module_offsets_raw:dict, side:str, correction = None ) -> dict :

    # HF baseplate
    # direction vector =TTT1 - TTT2
    d_vector_x = module_offsets_raw['measured_ref']['x'] - module_offsets_raw['measured_sup_ref']['x']
    d_vector_y = module_offsets_raw['measured_ref']['y'] - module_offsets_raw['measured_sup_ref']['y']

    # Always plus for x component
    if d_vector_x < 0.:
        d_vector_x = - d_vector_x
        d_vector_y = - d_vector_y

    length = math.sqrt( d_vector_x**2 + d_vector_y**2 )

    # Return unit vector
    return {
                'd_vector_x' : d_vector_x/length,
                'd_vector_y' : d_vector_y/length
            }

################################
# HD Left (1.1)
################################
def HL_pcb_d_vector_finder( module_offsets_raw:dict, side:str, correction = None ) -> dict :

    # HF pcb
    # direction vector = M1 - M4
    d_vector_x = module_offsets_raw[side]['pcb']['x']['M1'] - module_offsets_raw[side]['pcb']['x']['M4']
    d_vector_y = module_offsets_raw[side]['pcb']['y']['M1'] - module_offsets_raw[side]['pcb']['y']['M4']

    # Always plus for x component
    if d_vector_x < 0.:
        d_vector_x = - d_vector_x
        d_vector_y = - d_vector_y

    length = math.sqrt( d_vector_x**2 + d_vector_y**2 )

    # Return unit vector
    return {
                'd_vector_x' : d_vector_x/length,
                'd_vector_y' : d_vector_y/length
            }

def HL_sensor_d_vector_finder( module_offsets_raw:dict, side:str, correction = None ) -> dict :

    # HF sensor
    # direction vector = M26 - M3
    d_vector_x = module_offsets_raw[side]['sensor']['x']['M26'] - module_offsets_raw[side]['sensor']['x']['M3']
    d_vector_y = module_offsets_raw[side]['sensor']['y']['M26'] - module_offsets_raw[side]['sensor']['y']['M3']

    # Always plus for x component
    if d_vector_x < 0.:
        d_vector_x = - d_vector_x
        d_vector_y = - d_vector_y

    # Angle rotation as correction
    theta = correction['theta'] * math.pi / 180.
    d_vector_x_corr = d_vector_x * math.cos(theta) - d_vector_y * math.sin(theta)
    d_vector_y_corr = d_vector_y * math.cos(theta) + d_vector_x * math.sin(theta)

    length = math.sqrt( d_vector_x_corr**2 + d_vector_y_corr**2 )

    # Return unit vector
    return {
                'd_vector_x' : d_vector_x_corr/length,
                'd_vector_y' : d_vector_y_corr/length
            }

def HL_baseplate_d_vector_finder( module_offsets_raw:dict, side:str, correction = None ) -> dict :

    # HF baseplate
    # direction vector =TTT1 - TTT2
    d_vector_x = module_offsets_raw['measured_ref']['x'] - module_offsets_raw['measured_sup_ref']['x']
    d_vector_y = module_offsets_raw['measured_ref']['y'] - module_offsets_raw['measured_sup_ref']['y']

    # Always plus for x component
    if d_vector_x < 0.:
        d_vector_x = - d_vector_x
        d_vector_y = - d_vector_y

    length = math.sqrt( d_vector_x**2 + d_vector_y**2 )

    # Return unit vector
    return {
                'd_vector_x' : d_vector_x/length,
                'd_vector_y' : d_vector_y/length
            }

################################
# HD Right (1.1)
################################
def HR_pcb_d_vector_finder( module_offsets_raw:dict, side:str, correction = None ) -> dict :

    # HF pcb
    # direction vector = M3 - M4
    d_vector_x = module_offsets_raw[side]['pcb']['x']['M3'] - module_offsets_raw[side]['pcb']['x']['M4']
    d_vector_y = module_offsets_raw[side]['pcb']['y']['M3'] - module_offsets_raw[side]['pcb']['y']['M4']

    # Always plus for x component
    if d_vector_x < 0.:
        d_vector_x = - d_vector_x
        d_vector_y = - d_vector_y

    length = math.sqrt( d_vector_x**2 + d_vector_y**2 )

    # Return unit vector
    return {
                'd_vector_x' : d_vector_x/length,
                'd_vector_y' : d_vector_y/length
            }

def HR_sensor_d_vector_finder( module_offsets_raw:dict, side:str, correction = None ) -> dict :

    # HF sensor
    # direction vector = M13 - M6
    d_vector_x = module_offsets_raw[side]['sensor']['x']['M13'] - module_offsets_raw[side]['sensor']['x']['M6']
    d_vector_y = module_offsets_raw[side]['sensor']['y']['M13'] - module_offsets_raw[side]['sensor']['y']['M6']

    # Always plus for x component
    if d_vector_x < 0.:
        d_vector_x = - d_vector_x
        d_vector_y = - d_vector_y

    # Angle rotation as correction
    theta = correction['theta'] * math.pi / 180.
    d_vector_x_corr = d_vector_x * math.cos(theta) - d_vector_y * math.sin(theta)
    d_vector_y_corr = d_vector_y * math.cos(theta) + d_vector_x * math.sin(theta)

    length = math.sqrt( d_vector_x_corr**2 + d_vector_y_corr**2 )

    # Return unit vector
    return {
                'd_vector_x' : d_vector_x_corr/length,
                'd_vector_y' : d_vector_y_corr/length
            }

def HR_baseplate_d_vector_finder( module_offsets_raw:dict, side:str, correction = None ) -> dict :

    # HF baseplate
    # direction vector =TTT1 - TTT2
    d_vector_x = module_offsets_raw['measured_ref']['x'] - module_offsets_raw['measured_sup_ref']['x']
    d_vector_y = module_offsets_raw['measured_ref']['y'] - module_offsets_raw['measured_sup_ref']['y']

    # Always plus for x component
    if d_vector_x < 0.:
        d_vector_x = - d_vector_x
        d_vector_y = - d_vector_y

    length = math.sqrt( d_vector_x**2 + d_vector_y**2 )

    # Return unit vector
    return {
                'd_vector_x' : d_vector_x/length,
                'd_vector_y' : d_vector_y/length
            }

################################
# HD Bottom (1.1)
################################
def HB_pcb_d_vector_finder( module_offsets_raw:dict, side:str, correction = None ) -> dict :

    # HF pcb
    # direction vector = FD3 - FD1
    d_vector_x = module_offsets_raw[side]['pcb']['x']['FD3'] - module_offsets_raw[side]['pcb']['x']['FD1']
    d_vector_y = module_offsets_raw[side]['pcb']['y']['FD3'] - module_offsets_raw[side]['pcb']['y']['FD1']

    # Always plus for x component
    if d_vector_x < 0.:
        d_vector_x = - d_vector_x
        d_vector_y = - d_vector_y

    length = math.sqrt( d_vector_x**2 + d_vector_y**2 )

    # Return unit vector
    return {
                'd_vector_x' : d_vector_x/length,
                'd_vector_y' : d_vector_y/length
            }

def HB_sensor_d_vector_finder( module_offsets_raw:dict, side:str, correction = None ) -> dict :

    # HF sensor
    # direction vector = M15 - M24
    d_vector_x = module_offsets_raw[side]['sensor']['x']['M15'] - module_offsets_raw[side]['sensor']['x']['M24']
    d_vector_y = module_offsets_raw[side]['sensor']['y']['M15'] - module_offsets_raw[side]['sensor']['y']['M24']

    # Always plus for x component
    if d_vector_x < 0.:
        d_vector_x = - d_vector_x
        d_vector_y = - d_vector_y

    # Angle rotation as correction
    theta = correction['theta'] * math.pi / 180.
    d_vector_x_corr = d_vector_x * math.cos(theta) - d_vector_y * math.sin(theta)
    d_vector_y_corr = d_vector_y * math.cos(theta) + d_vector_x * math.sin(theta)

    length = math.sqrt( d_vector_x_corr**2 + d_vector_y_corr**2 )

    # Return unit vector
    return {
                'd_vector_x' : d_vector_x_corr/length,
                'd_vector_y' : d_vector_y_corr/length
            }

def HB_baseplate_d_vector_finder( module_offsets_raw:dict, side:str, correction = None ) -> dict :

    # HF baseplate
    # direction vector =TTT1 - TTT2
    d_vector_x = module_offsets_raw['measured_ref']['x'] - module_offsets_raw['measured_sup_ref']['x']
    d_vector_y = module_offsets_raw['measured_ref']['y'] - module_offsets_raw['measured_sup_ref']['y']

    # Always plus for x component
    if d_vector_x < 0.:
        d_vector_x = - d_vector_x
        d_vector_y = - d_vector_y

    length = math.sqrt( d_vector_x**2 + d_vector_y**2 )

    # Return unit vector
    return {
                'd_vector_x' : d_vector_x/length,
                'd_vector_y' : d_vector_y/length
            }

################################
# LD Right (1.2)
################################
def LR_pcb_d_vector_finder( module_offsets_raw:dict, side:str, correction = None ) -> dict :

    # HF pcb
    # direction vector = FD2 - FD4
    d_vector_x = module_offsets_raw[side]['pcb']['x']['FD2'] - module_offsets_raw[side]['pcb']['x']['FD4']
    d_vector_y = module_offsets_raw[side]['pcb']['y']['FD2'] - module_offsets_raw[side]['pcb']['y']['FD4']

    # Always plus for x component
    if d_vector_x < 0.:
        d_vector_x = - d_vector_x
        d_vector_y = - d_vector_y

    length = math.sqrt( d_vector_x**2 + d_vector_y**2 )

    # Return unit vector
    return {
                'd_vector_x' : d_vector_x/length,
                'd_vector_y' : d_vector_y/length
            }

def LR_sensor_d_vector_finder( module_offsets_raw:dict, side:str, correction = None ) -> dict :

    # HF sensor
    # direction vector = M7 - M6
    d_vector_x = module_offsets_raw[side]['sensor']['x']['M7'] - module_offsets_raw[side]['sensor']['x']['M6']
    d_vector_y = module_offsets_raw[side]['sensor']['y']['M7'] - module_offsets_raw[side]['sensor']['y']['M6']

    # Always plus for x component
    if d_vector_x < 0.:
        d_vector_x = - d_vector_x
        d_vector_y = - d_vector_y

    # Angle rotation as correction
    theta = correction['theta'] * math.pi / 180.
    d_vector_x_corr = d_vector_x * math.cos(theta) - d_vector_y * math.sin(theta)
    d_vector_y_corr = d_vector_y * math.cos(theta) + d_vector_x * math.sin(theta)

    length = math.sqrt( d_vector_x_corr**2 + d_vector_y_corr**2 )

    # Return unit vector
    return {
                'd_vector_x' : d_vector_x_corr/length,
                'd_vector_y' : d_vector_y_corr/length
            }

def LR_baseplate_d_vector_finder( module_offsets_raw:dict, side:str, correction = None ) -> dict :

    # HF baseplate
    # direction vector =TTT1 - TTT2
    d_vector_x = module_offsets_raw['measured_ref']['x'] - module_offsets_raw['measured_sup_ref']['x']
    d_vector_y = module_offsets_raw['measured_ref']['y'] - module_offsets_raw['measured_sup_ref']['y']

    # Always plus for x component
    if d_vector_x < 0.:
        d_vector_x = - d_vector_x
        d_vector_y = - d_vector_y

    length = math.sqrt( d_vector_x**2 + d_vector_y**2 )

    # Return unit vector
    return {
                'd_vector_x' : d_vector_x/length,
                'd_vector_y' : d_vector_y/length
            }

################################
# LD Left (1.2)
################################
def LL_pcb_d_vector_finder( module_offsets_raw:dict, side:str, correction = None ) -> dict :

    # HF pcb
    # direction vector = FD2 - FD4
    d_vector_x = module_offsets_raw[side]['pcb']['x']['FD2'] - module_offsets_raw[side]['pcb']['x']['FD4']
    d_vector_y = module_offsets_raw[side]['pcb']['y']['FD2'] - module_offsets_raw[side]['pcb']['y']['FD4']

    # Always plus for x component
    if d_vector_x < 0.:
        d_vector_x = - d_vector_x
        d_vector_y = - d_vector_y

    length = math.sqrt( d_vector_x**2 + d_vector_y**2 )

    # Return unit vector
    return {
                'd_vector_x' : d_vector_x/length,
                'd_vector_y' : d_vector_y/length
            }

def LL_sensor_d_vector_finder( module_offsets_raw:dict, side:str, correction = None ) -> dict :

    # HF sensor
    # direction vector = M4 - M1
    d_vector_x = module_offsets_raw[side]['sensor']['x']['M4'] - module_offsets_raw[side]['sensor']['x']['M1']
    d_vector_y = module_offsets_raw[side]['sensor']['y']['M4'] - module_offsets_raw[side]['sensor']['y']['M1']

    # Always plus for x component
    if d_vector_x < 0.:
        d_vector_x = - d_vector_x
        d_vector_y = - d_vector_y

    # Angle rotation as correction
    theta = correction['theta'] * math.pi / 180.
    d_vector_x_corr = d_vector_x * math.cos(theta) - d_vector_y * math.sin(theta)
    d_vector_y_corr = d_vector_y * math.cos(theta) + d_vector_x * math.sin(theta)

    length = math.sqrt( d_vector_x_corr**2 + d_vector_y_corr**2 )

    # Return unit vector
    return {
                'd_vector_x' : d_vector_x_corr/length,
                'd_vector_y' : d_vector_y_corr/length
            }

def LL_baseplate_d_vector_finder( module_offsets_raw:dict, side:str, correction = None ) -> dict :

    # HF baseplate
    # direction vector =TTT1 - TTT2
    d_vector_x = module_offsets_raw['measured_ref']['x'] - module_offsets_raw['measured_sup_ref']['x']
    d_vector_y = module_offsets_raw['measured_ref']['y'] - module_offsets_raw['measured_sup_ref']['y']

    # Always plus for x component
    if d_vector_x < 0.:
        d_vector_x = - d_vector_x
        d_vector_y = - d_vector_y

    length = math.sqrt( d_vector_x**2 + d_vector_y**2 )

    # Return unit vector
    return {
                'd_vector_x' : d_vector_x/length,
                'd_vector_y' : d_vector_y/length
            }

################################
# LD Five (1.1)
################################
def L5_pcb_d_vector_finder( module_offsets_raw:dict, side:str, correction = None ) -> dict :

    # HF pcb
    # direction vector = FD2 - FD4
    d_vector_x = module_offsets_raw[side]['pcb']['x']['FD2'] - module_offsets_raw[side]['pcb']['x']['FD4']
    d_vector_y = module_offsets_raw[side]['pcb']['y']['FD2'] - module_offsets_raw[side]['pcb']['y']['FD4']

    # Always plus for x component
    if d_vector_x < 0.:
        d_vector_x = - d_vector_x
        d_vector_y = - d_vector_y

    length = math.sqrt( d_vector_x**2 + d_vector_y**2 )

    # Return unit vector
    return {
                'd_vector_x' : d_vector_x/length,
                'd_vector_y' : d_vector_y/length
            }

def L5_sensor_d_vector_finder( module_offsets_raw:dict, side:str, correction = None ) -> dict :

    # HF sensor
    # direction vector = M8 - M1
    d_vector_x = module_offsets_raw[side]['sensor']['x']['M8'] - module_offsets_raw[side]['sensor']['x']['M1']
    d_vector_y = module_offsets_raw[side]['sensor']['y']['M8'] - module_offsets_raw[side]['sensor']['y']['M1']

    # Always plus for x component
    if d_vector_x < 0.:
        d_vector_x = - d_vector_x
        d_vector_y = - d_vector_y

    # Angle rotation as correction
    theta = correction['theta'] * math.pi / 180.
    d_vector_x_corr = d_vector_x * math.cos(theta) - d_vector_y * math.sin(theta)
    d_vector_y_corr = d_vector_y * math.cos(theta) + d_vector_x * math.sin(theta)

    length = math.sqrt( d_vector_x_corr**2 + d_vector_y_corr**2 )

    # Return unit vector
    return {
                'd_vector_x' : d_vector_x_corr/length,
                'd_vector_y' : d_vector_y_corr/length
            }

def L5_baseplate_d_vector_finder( module_offsets_raw:dict, side:str, correction = None ) -> dict :

    # HF baseplate
    # direction vector =TTT1 - TTT2
    d_vector_x = module_offsets_raw['measured_ref']['x'] - module_offsets_raw['measured_sup_ref']['x']
    d_vector_y = module_offsets_raw['measured_ref']['y'] - module_offsets_raw['measured_sup_ref']['y']

    # Always plus for x component
    if d_vector_x < 0.:
        d_vector_x = - d_vector_x
        d_vector_y = - d_vector_y

    length = math.sqrt( d_vector_x**2 + d_vector_y**2 )

    # Return unit vector
    return {
                'd_vector_x' : d_vector_x/length,
                'd_vector_y' : d_vector_y/length
            }

################################
# LD Top (1.1)
################################
def LT_pcb_d_vector_finder( module_offsets_raw:dict, side:str, correction = None ) -> dict :

    # HF pcb
    # direction vector = FD1 - FD3
    d_vector_x = module_offsets_raw[side]['pcb']['x']['FD1'] - module_offsets_raw[side]['pcb']['x']['FD3']
    d_vector_y = module_offsets_raw[side]['pcb']['y']['FD1'] - module_offsets_raw[side]['pcb']['y']['FD3']

    # Always plus for x component
    if d_vector_x < 0.:
        d_vector_x = - d_vector_x
        d_vector_y = - d_vector_y

    length = math.sqrt( d_vector_x**2 + d_vector_y**2 )

    # Return unit vector
    return {
                'd_vector_x' : d_vector_x/length,
                'd_vector_y' : d_vector_y/length
            }

def LT_sensor_d_vector_finder( module_offsets_raw:dict, side:str, correction = None ) -> dict :

    # HF sensor
    # direction vector = M10 - M19
    d_vector_x = module_offsets_raw[side]['sensor']['x']['M10'] - module_offsets_raw[side]['sensor']['x']['M19']
    d_vector_y = module_offsets_raw[side]['sensor']['y']['M10'] - module_offsets_raw[side]['sensor']['y']['M19']

    # Always plus for x component
    if d_vector_x < 0.:
        d_vector_x = - d_vector_x
        d_vector_y = - d_vector_y

    # Angle rotation as correction
    theta = correction['theta'] * math.pi / 180.
    d_vector_x_corr = d_vector_x * math.cos(theta) - d_vector_y * math.sin(theta)
    d_vector_y_corr = d_vector_y * math.cos(theta) + d_vector_x * math.sin(theta)

    length = math.sqrt( d_vector_x_corr**2 + d_vector_y_corr**2 )

    # Return unit vector
    return {
                'd_vector_x' : d_vector_x_corr/length,
                'd_vector_y' : d_vector_y_corr/length
            }

def LT_baseplate_d_vector_finder( module_offsets_raw:dict, side:str, correction = None ) -> dict :

    # HF baseplate
    # direction vector =TTT1 - TTT2
    d_vector_x = module_offsets_raw['measured_ref']['x'] - module_offsets_raw['measured_sup_ref']['x']
    d_vector_y = module_offsets_raw['measured_ref']['y'] - module_offsets_raw['measured_sup_ref']['y']

    # Always plus for x component
    if d_vector_x < 0.:
        d_vector_x = - d_vector_x
        d_vector_y = - d_vector_y

    length = math.sqrt( d_vector_x**2 + d_vector_y**2 )

    # Return unit vector
    return {
                'd_vector_x' : d_vector_x/length,
                'd_vector_y' : d_vector_y/length
            }

################################
# LD Bottom (2.0)
################################
def LB_pcb_d_vector_finder( module_offsets_raw:dict, side:str, correction = None ) -> dict :

    # HF pcb
    # direction vector = M1 - M3
    d_vector_x = module_offsets_raw[side]['pcb']['x']['M1'] - module_offsets_raw[side]['pcb']['x']['M3']
    d_vector_y = module_offsets_raw[side]['pcb']['y']['M1'] - module_offsets_raw[side]['pcb']['y']['M3']

    # Always plus for x component
    if d_vector_x < 0.:
        d_vector_x = - d_vector_x
        d_vector_y = - d_vector_y

    length = math.sqrt( d_vector_x**2 + d_vector_y**2 )

    # Return unit vector
    return {
                'd_vector_x' : d_vector_x/length,
                'd_vector_y' : d_vector_y/length
            }

def LB_sensor_d_vector_finder( module_offsets_raw:dict, side:str, correction = None ) -> dict :

    # HF sensor
    # direction vector = M11 - M18
    d_vector_x = module_offsets_raw[side]['sensor']['x']['M11'] - module_offsets_raw[side]['sensor']['x']['M18']
    d_vector_y = module_offsets_raw[side]['sensor']['y']['M11'] - module_offsets_raw[side]['sensor']['y']['M18']

    # Always plus for x component
    if d_vector_x < 0.:
        d_vector_x = - d_vector_x
        d_vector_y = - d_vector_y

    # Angle rotation as correction
    theta = correction['theta'] * math.pi / 180.
    d_vector_x_corr = d_vector_x * math.cos(theta) - d_vector_y * math.sin(theta)
    d_vector_y_corr = d_vector_y * math.cos(theta) + d_vector_x * math.sin(theta)

    length = math.sqrt( d_vector_x_corr**2 + d_vector_y_corr**2 )

    # Return unit vector
    return {
                'd_vector_x' : d_vector_x_corr/length,
                'd_vector_y' : d_vector_y_corr/length
            }

def LB_baseplate_d_vector_finder( module_offsets_raw:dict, side:str, correction = None ) -> dict :

    # HF baseplate
    # direction vector =TTT1 - TTT2
    d_vector_x = module_offsets_raw['measured_ref']['x'] - module_offsets_raw['measured_sup_ref']['x']
    d_vector_y = module_offsets_raw['measured_ref']['y'] - module_offsets_raw['measured_sup_ref']['y']

    # Always plus for x component
    if d_vector_x < 0.:
        d_vector_x = - d_vector_x
        d_vector_y = - d_vector_y

    length = math.sqrt( d_vector_x**2 + d_vector_y**2 )

    # Return unit vector
    return {
                'd_vector_x' : d_vector_x/length,
                'd_vector_y' : d_vector_y/length
            }
