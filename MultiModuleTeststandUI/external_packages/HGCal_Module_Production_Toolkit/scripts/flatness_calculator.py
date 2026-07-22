from iminuit import Minuit
from iminuit.cost import LeastSquares

import matplotlib as mpl
mpl.use('Agg')
import matplotlib.pyplot as plt

import os
import numpy as np
import math
import re
from utils.io_tool import get_flatness_raw_from_textfile, ragular_all_numbers

# 3D plane, z = ax + by + c 
def plane(x_y, a, b, c):
    x, y = x_y
    return a*x + b*y + c

def ref_plane_finding(x: np.array, y: np.array, z: np.array, z_err: np.array) -> list:

    # Fit process
    cost = LeastSquares( (x,y), z, z_err*0.06, plane )

    m = Minuit(cost, a=-1, b=2, c=1)  # starting values for a, b, c
    m.migrad()  # finds minimum of least_squares function
    m.hesse()

    chi2_ndof = m.fval / (len(z) - m.nfit)
    print ( f"Chi2/ndof = {chi2_ndof}" )

    # Best parameter
    a_bestfit = m.values[0]
    b_bestfit = m.values[1]
    c_bestfit = m.values[2]

    return [a_bestfit, b_bestfit, c_bestfit]

def target_on_ref_plane(x_target: np.array, y_target: np.array, z_target: np.array, ref_plane_coeffs=None ) -> tuple:

    distance = z_target
    # Distance between points and the bestfit plane = (ax+by+c-z)/sqrt(a^2+b^2+1)
    if ref_plane_coeffs != None:
        distance = plane( (x_target, y_target), ref_plane_coeffs[0], ref_plane_coeffs[1], ref_plane_coeffs[2] )
        distance = np.subtract(z_target, distance)
        distance = distance / math.sqrt( ref_plane_coeffs[0]**2 + ref_plane_coeffs[1]**2 + 1. )

    print("Flatness :", np.max(distance) - np.min(distance))
    print("Thickness :", np.abs(distance.mean()))

    max_index = np.argmax(distance)
    min_index = np.argmin(distance)

    return np.max(distance) - np.min(distance), np.abs(distance.mean()), distance, \
            [x_target[min_index], y_target[min_index], distance[min_index], \
            x_target[max_index], y_target[max_index], distance[max_index] ]

def make_flatness_plot(module, x, y, z, flatness, thickness, critical_points, isVacuum:bool = False, is180:bool = False) -> None:

    tag = 'Vacuum' if isVacuum else 'NoVacuum'

    fig = plt.figure( figsize=(10, 4.5), layout = 'constrained' )
    ax0 = fig.add_subplot(121, title=f'{module}_{tag}_flatness_3D', projection='3d')
    ax1 = fig.add_subplot(122, title=f'{module}_{tag}_flatness_2D')

    if is180:
        x = (-1)*x
        y = (-1)*y

    #ax0.plot_trisurf(x, y, z, cmap='YlOrRd', linewidth=0, antialiased=False)
    ax0.plot_trisurf(x, y, z, cmap='viridis', linewidth=0, antialiased=False)
    ax0.set_xlabel(f'x [mm]')
    ax0.set_ylabel(f'y [mm]')
    ax0.set_zlabel(f'z [mm]')

    scat = ax1.scatter(x, y, c=z, marker='o')
    ax1.set_xlabel(f'x [mm]')
    ax1.set_ylabel(f'y [mm]')
    ax1.text(-0.2, -0.1, f'Flatness = {flatness:.4f} mm', horizontalalignment='center', verticalalignment='center', transform=ax1.transAxes, fontsize=15 )
    ax1.text(-0.2, -0.2, f'Thickness = {thickness:.3f} mm', horizontalalignment='center', verticalalignment='center', transform=ax1.transAxes, fontsize=15 )
    fig.colorbar(scat, label=f'z [mm]')

    if not is180:
        ax1.text(critical_points[0], critical_points[1], ' {:.2f} (Min)'.format(critical_points[2]), color='r', fontsize=10)
        ax1.text(critical_points[3], critical_points[4], ' {:.2f} (Max)'.format(critical_points[5]), color='r', fontsize=10)
    else:
        ax1.text(-critical_points[0], -critical_points[1], ' {:.2f} (Min)'.format(critical_points[2]), color='r', fontsize=10)
        ax1.text(-critical_points[3], -critical_points[4], ' {:.2f} (Max)'.format(critical_points[5]), color='r', fontsize=10)

    print(' {:.2f} (Min)'.format(critical_points[2]), ' {:.2f} (Max)'.format(critical_points[5]))

    plt.savefig(os.getenv('FRAMEWORK_PATH') + f'/out/{module}_{tag}_flatness.png')
    plt.savefig(os.getenv('FRAMEWORK_PATH') + f'/out/{module}_{tag}_flatness.pdf')
    plt.close()

def flatness_calculator(module:str, textfile:str, isVacuum:bool = False, isSkip:bool = False) -> dict:

    if isSkip:
        return {
                module.split('-')[0] : {
                    "Vacuum" if isVacuum else "NoVacuum" : {
                            "flatness"   : "-",
                            "thickness"  : "-",
                            "max_height" : "-",
                            "min_height" : "-"
                        }
                    }
                }

    # Tray surface height
    ref_plane_coeffs = None
    tray_side = None
    if re.search('AT0[0-9]-[LR]', module):

        module = module.split('-')
        tray_type = module[1]
        tray_side = module[2][0]
        module    = module[0]

        x_ref, y_ref, z_ref = get_flatness_raw_from_textfile(os.getenv('FRAMEWORK_PATH') + f'/data/{tray_type}-{tray_side}.txt', tray_side)

        if not isVacuum:
            x_ref, y_ref, z_ref = get_flatness_raw_from_textfile(os.getenv('FRAMEWORK_PATH') + f'/data/AT00-{tray_side}.txt', tray_side)

        ref_plane_coeffs = ref_plane_finding(x_ref, y_ref, z_ref, np.ones( len(z_ref) ))

    # Material surface height
    x_target, y_target, z_target = get_flatness_raw_from_textfile(os.getenv('FRAMEWORK_PATH') + f"/input/{textfile}", tray_side)

    # Calculate the height in different points on the PCB surface w.r.t the given tray 
    flatness, thickness, z_target, critical_points = target_on_ref_plane(x_target, y_target, z_target, ref_plane_coeffs)

    # Make plots
    make_flatness_plot(
            module,
            x_target,
            y_target,
            z_target,
            flatness,
            thickness,
            critical_points,
            isVacuum = isVacuum,
            is180 = True if tray_side == 'L' else False
            )

    return ragular_all_numbers( {
            module : {
                "Vacuum" if isVacuum else "NoVacuum" : {
                        "flatness"   : flatness.item(),
                        "thickness"  : thickness.item(),
                        "max_height" : critical_points[5],
                        "min_height" : critical_points[2],
                        "x_points"   : x_target,
                        "y_points"   : y_target,
                        "z_points"   : z_target
                    }
                }
            } )
