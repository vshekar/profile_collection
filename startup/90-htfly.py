#Plans for operation of the HTfly device.

#Define parameters for future alignment routine, for D3 hole
#HTFLY_X_START = 0.50
#HTFLY_Y_START = -2.9

LOAD_HTFLY_POS_X = -285
EXPOSED_HTFLY_POS_X = 285

#Define vertical position of row 3
row3_y_vert = -2.9

def htfly_move_to_load():
    if htfly.x.position != LOAD_HTFLY_POS_X:
        print("Moving to load position")
        yield from bps.mv(htfly.x, LOAD_HTFLY_POS_X)
    else:
        print("Already there!")


def htfly_exp_row(row_num, htfly_vel, hslit_size, al_thickness):
    '''
    Function to expose a single row on the HTFly device, specifying velocity, 
    slit size, and attenuation. Moves device back to load position after exposure.
    Leaves FE shutter and pre-shutter open after run.

    Parameters
    ----------
    row_num: integer
        Row number on HTFly exposure cell. 
        Must be in the range 1 - 6

    htfly_vel: float
        HTFly fast x stage velocity in mm/sec.
        Must be between 1 - 500 mm/sec

    hslit_size: float
        BIFS ADC horizontal slit size in mm.
        Must be > 0.

    al_thickness: integer
        Aluminum attenuator thickness in um.
        Must be an entry in the list [762, 508, 305, 203, 152, 76, 25, 0]
    
    '''

    #Calculate exposure time in milliseconds, rounded to 3 decimal places
    htfly_exp_time = round((hslit_size / htfly_vel) * 1000, 3)
    
    #Set HTFly velocity.
    if htfly_vel <= 0:
        raise ValueError(f"You entered {htfly_vel} mm/s. Enter a velocity greater than 0 mm/sec!")
    if htfly_vel > 500:
        raise ValueError(f"You entered {htfly_vel} mm/s. Enter a velocity less than or equal to 500 mm/sec!")
    else:
        print(f"Setting htfly_x stage velocity to {htfly_vel} mm/sec.")
        yield from bps.mv(htfly.x.velocity, htfly_vel)
        
    #Set ADC slit size, trap exception if a negative number is entered or value > 6 is entered
    if hslit_size <= 0:
        raise ValueError(f"You entered {hslit_size} mm slit size. Enter a positive horizontal slit size!")
    elif hslit_size > 6:
        raise ValueError(f"You entered {hslit_size} mm slit size. Enter a horizontal slit size smaller than 6 mm!")
    else:        
        print(f"Moving the ADC horizontal slit size to {hslit_size} mm.")
        yield from bps.mv(adcslits.xgap, hslit_size)
            
    #Move to desired row number, throw exception if row /= 1-6
    if row_num == 1:
        print("moving to row 1")
        yield from bps.mv(htfly.y, row3_y_vert-18)
    elif row_num == 2:
        print("moving to row 2")
        yield from bps.mv(htfly.y, row3_y_vert-9)
    elif row_num == 3:
        print("moving to row 3")
        yield from bps.mv(htfly.y, row3_y_vert)
    elif row_num == 4:
        print("moving to row 4")
        yield from bps.mv(htfly.y, row3_y_vert+9)
    elif row_num == 5:
        print("moving to row 5")
        yield from bps.mv(htfly.y, row3_y_vert+18)
    elif row_num == 6:
        print("moving to row 6")
        yield from bps.mv(htfly.y, row3_y_vert+27)
    else:
        raise ValueError(f"You entered row {row_num}. Row value must be in the range 1 - 6!")
    
    #Move filter wheel to desired attenuation, and fail if not in the list of available attenuations.
    if al_thickness in [762, 508, 305, 203, 152, 76, 25, 0]:
        print(f"Moving filter wheel to {al_thickness} um Al attenuation.")
        yield from bps.mv(filter_wheel.thickness, al_thickness)
    else:
        raise ValueError(f"{al_thickness} is not an available attenuator. Choose from: 762, 508, 305, 203, 152, 76, 25, or 0")

    #More elegant solution that reviews the filter_wheel list of dictionaries. It appears to run.
    #However RunEngine crashes w/ TypeError: Nonetype is not iterable.
    #if not any(d['thickness'] == al_thickness for d in filter_wheel.wheel_positions):
    #    raise ValueError("Attenuator must be one of: 762, 508, 305, 203, 152, 76, 25, or 0")
    #else:
    #    print("Moving filter wheel to " + str(al_thickness) + "um Al attenuation.")
    #    yield from bps.mv(filter_wheel.thickness, al_thickness)

    #Check that HTFly is at load position and move it there before opening shutters.
    if htfly.x.position != LOAD_HTFLY_POS_X:
        print("Moving to load position.")
        yield from bps.mv(htfly.x, LOAD_HTFLY_POS_X)
    
    #Check state of pps_shutter and pre_shutter and open if needed.
    #This nomenclature allows the shutters to remain open after RE completes.
    if EpicsSignalRO(pps_shutter.enabled_status.pvname).get() == 0:
        raise Exception("Can't open photon shutter! Check that the hutch is interlocked and the shutter is enabled.")
    
    if pps_shutter.status.get() == 'Not Open':
        print("The photon shutter was closed and is now being opened.")
        pps_shutter.set('Open')
        yield from bps.sleep(3)   #Allow some wait time for the shutter opening to finish
        
    if pre_shutter.status.get() == 'Not Open':
        print("The pre-shutter was closed and is now being opened.")
        pre_shutter.set('Open')
        yield from bps.sleep(3)   #Allow some wait time for the shutter opening to finish

    print("Pre-shutter and PPS shutter are open. Opening the sample shutter and Uniblitz.")
  
    yield from bps.mv(diode_shutter, 'open')
    yield from bps.mv(dg, 30)               #set Uniblitz opening time
    yield from bps.mv(dg.fire, 1)           #fire Uniblitz
    
    print(f"Row {row_num} is being exposed at {htfly_vel} mm/sec and a {hslit_size} mm horizontal slit.")
    print(f"This corresponds to an exposure time of {htfly_exp_time} milliseconds.")
    yield from bps.mv(htfly.x, EXPOSED_HTFLY_POS_X)
    
    #Cleanup: close shutters, return to load position.
    print("Closing sample shutter and returning to load position")
    yield from bps.mv(diode_shutter, 'close')
    yield from bps.mv(dg, 0)    #Close Uniblitz shutter after exposure
    yield from bps.sleep(1)
    yield from bps.mv(htfly.x, LOAD_HTFLY_POS_X)
    print("All done, ready for another row!")
