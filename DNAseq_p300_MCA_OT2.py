
#   ____  ______   ___      ____  _   _____                      
#  / __ \/_  __/  |__ \    / __ \/ | / /   |     ________  ____ _
# / / / / / /_______/ /   / / / /  |/ / /| |    / ___/ _ \/ __ `/
#/ /_/ / / /_____/ __/   / /_/ / /|  / ___ |   (__  )  __/ /_/ / 
#\____/ /_/     /____/  /_____/_/ |_/_/  |_|  /____/\___/\__, /  
#                                                          /_/   
# Claseek library prep protocol, expects 3-5ug of DNA in 90ul of Tris
#
#
# BEFORE BEGINNING
# Set OT-2 to calibrate to the bottom of wells 
# Calibrate OT-2  
# Fill 12-row trough, prepare claseek kit end-conversion and adapter ligation mixes.

from opentrons import labware, instruments, modules, robot

#set robot gantry speed
robot.head_speed(x=300, y=300, z=90, a=90, b=40, c=40)


#To enable debug mode (all wait peroiods run for 1 min only) change debug value to 1
debug = 0

#module placements
trough = labware.load('trough-12row', 1)
magmodule = modules.load('magdeck', 7)
plate = labware.load('biorad-hardshell-96-PCR', 7, share=True)
p200rack = labware.load('tiprack-200ul', 3)
p200rack2 = labware.load('tiprack-200ul', 9)
enzrack = labware.load('biorad-hardshell-96-PCR', 5)
tempmodule = modules.load('tempdeck', 10)
tempplate = labware.load('alum-block-pcr-strips', 10, share=True)

#set spri size selection parameters
if debug == 1:
	spri_incubation_time = 1 #min
	spri_elution_time = 1 #min
	spri_settle_time = 1 #min
	spri_dry_time = 1 #min
	offset_height = 1 #mm
	incu_time1 = 1 #min
	incu_time2 = 1 #min

else: 
	spri_incubation_time = 10 #min
	spri_elution_time = 10 #min
	spri_settle_time = 2 #min
	spri_dry_time = 5 #min
	offset_height = 2 #mm
	incu_time1 = 5 #min
	incu_time2 = 7.5 #min


#trough reag locations
spri = trough.wells('A1')
eth = trough.wells('A2')
tris = trough.wells('A3')

#enzymatic reaction incubation temps and times
incu_temp1 = 20 #Celcius
incu_temp2 = 72 #Celcius

#protocol-specific variables
sample_volume = 90 #ul
eth_volume = 150 #ul
claseek_sample_volume = 25 #ul
claseek_end_conversion_mix_volume = 25 #ul
claseek_adapter_ligation_mix_volume = 20 #ul
final_cleanup_volume = 50 #ul
final_elution_volume = 30 #ul

# pipetting extras
small_aspiration_extra = 10 #ul
large_aspiration_extra = 50 #ul

#temporary variable to hold the current reaction volume
#reaction_volume
reaction_volume = sample_volume

#reagent IDs
end_mix = enzrack.wells('A1').bottom()
lig_mix = enzrack.wells('A2').bottom()

#pipettor
p300 = instruments.P300_Multi(
	mount='left',
	tip_racks=[p200rack, p200rack2],
	aspirate_flow_rate=60,
    dispense_flow_rate=60,
    min_volume=20)

#magnetic block selection protocol 
def select():
	robot.home()
	p300.delay(minutes=spri_incubation_time)
	magmodule.engage(offset=offset_height)
	p300.delay(minutes=spri_settle_time)

#resuspends large volume
def resuspend(location):
	p300.pick_up_tip()
	p300.mix(5, 200, location)
	p300.drop_tip()

#adjust flow rate for more accurate spri
def transferspri(vol, location_final, mixvol):
	p300.set_flow_rate(aspirate=30, dispense=30)
	p300.transfer(vol, spri, location_final, mix_after=(3,mixvol), touch_tip=True)
	p300.set_flow_rate(aspirate=60, dispense=60)

def prep(reaction_volume):
	
	#preheat tempdeck
	tempmodule.set_temperature(incu_temp1)
	
	#reset magnetic module from any previous run state
	magmodule.disengage()

	#resuspend SPRI
	resuspend(spri.bottom())
	
	return reaction_volume

def shear_clean(reaction_volume):
	
	#1X SPRI 
	transferspri(reaction_volume, plate.wells('A1'), 2*reaction_volume - small_aspiration_extra)
	
	#update reaction_volume
	reaction_volume += reaction_volume
	
	select()

	#Move/save spri waste to enzyme plate column 12
	p300.transfer(reaction_volume + small_aspiration_extra, plate.wells('A1').bottom(), enzrack.wells('A4'))

	#wash with 80%EtOH
	p300.transfer(eth_volume, eth, plate.wells('A1'))
	p300.transfer(eth_volume + large_aspiration_extra, plate.wells('A1').bottom(), p300.trash_container.top())
	robot.home()
	p300.delay(minutes=spri_dry_time)
	magmodule.disengage()

	#elute in 25ul for Claseek kit input volume 
	#//////////////////mixing (claseek_sample_volume - small_aspiration_extra) = 15ul is below p300 threshold and pipette will skip mixing 
	p300.transfer(claseek_sample_volume, tris, plate.wells('A1').top(), mix_after=(5,claseek_sample_volume), blow_out=True)

	#update reaction_volume
	reaction_volume = claseek_sample_volume

	robot.home()
	p300.delay(minutes= spri_elution_time)
	magmodule.engage(offset= offset_height)
	p300.delay(minutes= spri_settle_time)
		
	p300.transfer(reaction_volume + small_aspiration_extra, plate.wells('A1').bottom(), tempplate.wells('A1').bottom())
	magmodule.disengage()

	return reaction_volume

def claseek(reaction_volume):

	robot.home()
	tempmodule.wait_for_temp()

	#begin Claseek end-conversion
	#/////////////////mixing is double, second mix cycle raises tips above wells
	p300.transfer(claseek_end_conversion_mix_volume, end_mix, tempplate.wells('A1').top(), mix_after=(3, reaction_volume + claseek_end_conversion_mix_volume - small_aspiration_extra), blow_out=True)

	#update reaction_volume	
	reaction_volume += claseek_end_conversion_mix_volume
	
	robot.home()
	#claseek incubation @20 C
	p300.delay(minutes= incu_time1)

	robot.home()
	tempmodule.set_temperature(incu_temp2)
	tempmodule.wait_for_temp()

	#claseek incubation @72 C
	p300.delay(minutes= incu_time2)
	tempmodule.deactivate()

	#move samples to magdeck for 25C incubation
	p300.transfer(reaction_volume + small_aspiration_extra, tempplate.wells('A1').bottom(), plate.wells('A2'), blow_out=True)
	p300.transfer(claseek_adapter_ligation_mix_volume, lig_mix, plate.wells('A2').bottom(), mix_after=(3, reaction_volume + claseek_adapter_ligation_mix_volume - small_aspiration_extra))

	#update reaction_volume
	reaction_volume += claseek_adapter_ligation_mix_volume

	#claseek incubation @25 aka RT
	robot.home()
	p300.delay(minutes= incu_time2)

	return reaction_volume

def spriclean(reaction_volume):

	#prep: disengage magmodule and resuspend SPRI
	magmodule.disengage()
	resuspend(spri.bottom())

	#Double 1X SPRI cleanup (1/2)
	transferspri(reaction_volume, plate.wells('A2').bottom(), 2*reaction_volume - small_aspiration_extra)
	
	#update reaction_volume
	reaction_volume += reaction_volume
	
	select()
	
	p300.transfer(reaction_volume + small_aspiration_extra, plate.wells('A2').bottom(), enzrack.wells('A5'))
	p300.transfer(eth_volume, eth, plate.wells('A2'))
	p300.transfer(eth_volume + large_aspiration_extra, plate.wells('A2').bottom(), p300.trash_container.top())
	robot.home()
	p300.delay(minutes= spri_dry_time)
	
	magmodule.disengage()
	p300.transfer(final_cleanup_volume, tris, plate.wells('A2'), mix_after=(5,final_cleanup_volume - small_aspiration_extra), blow_out=True)
	
	reaction_volume = final_cleanup_volume

	select()

	p300.transfer(reaction_volume + small_aspiration_extra, plate.wells('A2'), plate.wells('A3').top(), blow_out=True)
	magmodule.disengage()

	#Resuspend SPRI
	resuspend(spri.bottom())

	#Double 1X SPRI cleanup (2/2)
	transferspri(reaction_volume, plate.wells('A3').bottom(), 2*reaction_volume - small_aspiration_extra)

	reaction_volume += reaction_volume

	select()

	p300.transfer(reaction_volume, plate.wells('A3').bottom(), enzrack.wells('A6'))
	p300.transfer(eth_volume, eth, plate.wells('A3'))
	p300.transfer(eth_volume + large_aspiration_extra, plate.wells('A3').bottom(), p300.trash_container.top())

	magmodule.disengage()

	robot.home()
	p300.delay(minutes= spri_dry_time)

	p300.transfer(final_elution_volume, tris, plate.wells('A3').bottom(), mix_after=(5, final_elution_volume - small_aspiration_extra), blow_out=True)
	
	reaction_volume = final_elution_volume

	select()

	return reaction_volume

def store():
	p300.pick_up_tip()
	p300.aspirate(final_elution_volume+small_aspiration_extra, plate.wells('A3').bottom())
	p300.move_to(enzrack.wells('A12').bottom())

	robot.pause(msg= '****************SAMPLES HELD IN CURRENT TIPS. UNPAUSE TO EJECT****************')

	p300.dispense(final_elution_volume+large_aspiration_extra)
	p300.touch_tip(enzrack('A4'))
	robot.home()

	p300.drop_tip()

	#Final samples in A12 1.5mL "enzrack" plate 

def dnaseq():
	reaction_volume = sample_volume
	afterprep_volume = prep(reaction_volume)
	aftershear_volume = shear_clean(afterprep_volume)
	afterclaseek_volume = claseek(aftershear_volume)
	afterspriclean_volume = spriclean(afterclaseek_volume)
	store()

######################### MAIN FUNCTION ##########################

dnaseq()







