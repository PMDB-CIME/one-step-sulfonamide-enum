from opentrons import protocol_api

metadata = {
    'protocolName': 'Reagent Transfer - Amine and SulfonylCl Combinations',
    'author': 'OpentronsAI',
    'description': 'Transfer two reagent classes to create 96 unique combinations',
    'source': 'OpentronsAI'
}

requirements = {
    'robotType': 'Flex',
    'apiLevel': '2.25'
}

def run(protocol: protocol_api.ProtocolContext):
    # Load trash bin
    trash = protocol.load_trash_bin('A3')
    
    # Load labware - using custom Greiner 96 well plates
    source_plate = protocol.load_labware('greiner_96_wellplate_200ul', 'D1', 'Source Plate')
    dest_plate = protocol.load_labware('greiner_96_wellplate_200ul', 'D2', 'Destination Plate')
    
    # Load tip racks
    tiprack_1 = protocol.load_labware('opentrons_flex_96_filtertiprack_50ul', 'C1')
    tiprack_2 = protocol.load_labware('opentrons_flex_96_filtertiprack_50ul', 'C2')
    tiprack_3 = protocol.load_labware('opentrons_flex_96_filtertiprack_50ul', 'C3')
    
    # Load pipettes
    left_pipette = protocol.load_instrument(
        'flex_1channel_50',
        mount='left',
        tip_racks=[tiprack_1, tiprack_2]
    )
    right_pipette = protocol.load_instrument(
        'flex_8channel_50',
        mount='right',
        tip_racks=[tiprack_3]
    )
    
    # Define liquids
    # Amines
    amine_1 = protocol.define_liquid(name='Amine 1', description='Amine 1', display_color='#FF0000')
    amine_2 = protocol.define_liquid(name='Amine 2', description='Amine 2', display_color='#FF3300')
    amine_3 = protocol.define_liquid(name='Amine 3', description='Amine 3', display_color='#FF6600')
    amine_4 = protocol.define_liquid(name='Amine 4', description='Amine 4', display_color='#FF9900')
    amine_5 = protocol.define_liquid(name='Amine 5', description='Amine 5', display_color='#FFCC00')
    amine_6 = protocol.define_liquid(name='Amine 6', description='Amine 6', display_color='#FFFF00')
    amine_7 = protocol.define_liquid(name='Amine 7', description='Amine 7', display_color='#CCFF00')
    amine_8 = protocol.define_liquid(name='Amine 8', description='Amine 8', display_color='#99FF00')
    
    # SulfonylCl
    sulfonyl_1 = protocol.define_liquid(name='SulfonylCl 1', description='SulfonylCl 1', display_color='#0000FF')
    sulfonyl_2 = protocol.define_liquid(name='SulfonylCl 2', description='SulfonylCl 2', display_color='#0033FF')
    sulfonyl_3 = protocol.define_liquid(name='SulfonylCl 3', description='SulfonylCl 3', display_color='#0066FF')
    sulfonyl_4 = protocol.define_liquid(name='SulfonylCl 4', description='SulfonylCl 4', display_color='#0099FF')
    sulfonyl_5 = protocol.define_liquid(name='SulfonylCl 5', description='SulfonylCl 5', display_color='#00CCFF')
    sulfonyl_6 = protocol.define_liquid(name='SulfonylCl 6', description='SulfonylCl 6', display_color='#00FFFF')
    sulfonyl_7 = protocol.define_liquid(name='SulfonylCl 7', description='SulfonylCl 7', display_color='#00FFCC')
    sulfonyl_8 = protocol.define_liquid(name='SulfonylCl 8', description='SulfonylCl 8', display_color='#00FF99')
    sulfonyl_9 = protocol.define_liquid(name='SulfonylCl 9', description='SulfonylCl 9', display_color='#00FF66')
    sulfonyl_10 = protocol.define_liquid(name='SulfonylCl 10', description='SulfonylCl 10', display_color='#00FF33')
    sulfonyl_11 = protocol.define_liquid(name='SulfonylCl 11', description='SulfonylCl 11', display_color='#00FF00')
    sulfonyl_12 = protocol.define_liquid(name='SulfonylCl 12', description='SulfonylCl 12', display_color='#33FF00')
    
    # Load liquids into source plate
    source_plate['A1'].load_liquid(liquid=amine_1, volume=50)
    source_plate['B1'].load_liquid(liquid=amine_2, volume=50)
    source_plate['C1'].load_liquid(liquid=amine_3, volume=50)
    source_plate['D1'].load_liquid(liquid=amine_4, volume=50)
    source_plate['E1'].load_liquid(liquid=amine_5, volume=50)
    source_plate['F1'].load_liquid(liquid=amine_6, volume=50)
    source_plate['G1'].load_liquid(liquid=amine_7, volume=50)
    source_plate['H1'].load_liquid(liquid=amine_8, volume=50)
    
    source_plate['A2'].load_liquid(liquid=sulfonyl_1, volume=50)
    source_plate['B2'].load_liquid(liquid=sulfonyl_2, volume=50)
    source_plate['C2'].load_liquid(liquid=sulfonyl_3, volume=50)
    source_plate['D2'].load_liquid(liquid=sulfonyl_4, volume=50)
    source_plate['E2'].load_liquid(liquid=sulfonyl_5, volume=50)
    source_plate['F2'].load_liquid(liquid=sulfonyl_6, volume=50)
    source_plate['G2'].load_liquid(liquid=sulfonyl_7, volume=50)
    source_plate['H2'].load_liquid(liquid=sulfonyl_8, volume=50)
    source_plate['A3'].load_liquid(liquid=sulfonyl_9, volume=50)
    source_plate['B3'].load_liquid(liquid=sulfonyl_10, volume=50)
    source_plate['C3'].load_liquid(liquid=sulfonyl_11, volume=50)
    source_plate['D3'].load_liquid(liquid=sulfonyl_12, volume=50)
    
    # Transfer volume
    transfer_vol = 5
    
    # Step 1-12: Transfer SulfonylCl compounds to destination plate
    # Step 1: SulfonylCl 1 to A01-A08
    sulfonyl_dest_1 = [dest_plate.wells_by_name()[well] for well in 
                       ['A1', 'A2', 'A3', 'A4', 'A5', 'A6', 'A7', 'A8']]
    left_pipette.transfer(transfer_vol, source_plate['A2'], sulfonyl_dest_1, new_tip='once')
    
    # Step 2: SulfonylCl 2 to A09-B04
    sulfonyl_dest_2 = [dest_plate.wells_by_name()[well] for well in 
                       ['A9', 'A10', 'A11', 'A12', 'B1', 'B2', 'B3', 'B4']]
    left_pipette.transfer(transfer_vol, source_plate['B2'], sulfonyl_dest_2, new_tip='once')
    
    # Step 3: SulfonylCl 3 to B05-B12
    sulfonyl_dest_3 = [dest_plate.wells_by_name()[well] for well in 
                       ['B5', 'B6', 'B7', 'B8', 'B9', 'B10', 'B11', 'B12']]
    left_pipette.transfer(transfer_vol, source_plate['C2'], sulfonyl_dest_3, new_tip='once')
    
    # Step 4: SulfonylCl 4 to C01-C08
    sulfonyl_dest_4 = [dest_plate.wells_by_name()[well] for well in 
                       ['C1', 'C2', 'C3', 'C4', 'C5', 'C6', 'C7', 'C8']]
    left_pipette.transfer(transfer_vol, source_plate['D2'], sulfonyl_dest_4, new_tip='once')
    
    # Step 5: SulfonylCl 5 to C09-D04
    sulfonyl_dest_5 = [dest_plate.wells_by_name()[well] for well in 
                       ['C9', 'C10', 'C11', 'C12', 'D1', 'D2', 'D3', 'D4']]
    left_pipette.transfer(transfer_vol, source_plate['E2'], sulfonyl_dest_5, new_tip='once')
    
    # Step 6: SulfonylCl 6 to D05-D12
    sulfonyl_dest_6 = [dest_plate.wells_by_name()[well] for well in 
                       ['D5', 'D6', 'D7', 'D8', 'D9', 'D10', 'D11', 'D12']]
    left_pipette.transfer(transfer_vol, source_plate['F2'], sulfonyl_dest_6, new_tip='once')
    
    # Step 7: SulfonylCl 7 to E01-E08
    sulfonyl_dest_7 = [dest_plate.wells_by_name()[well] for well in 
                       ['E1', 'E2', 'E3', 'E4', 'E5', 'E6', 'E7', 'E8']]
    left_pipette.transfer(transfer_vol, source_plate['G2'], sulfonyl_dest_7, new_tip='once')
    
    # Step 8: SulfonylCl 8 to E09-F04
    sulfonyl_dest_8 = [dest_plate.wells_by_name()[well] for well in 
                       ['E9', 'E10', 'E11', 'E12', 'F1', 'F2', 'F3', 'F4']]
    left_pipette.transfer(transfer_vol, source_plate['H2'], sulfonyl_dest_8, new_tip='once')
    
    # Step 9: SulfonylCl 9 to F05-F12
    sulfonyl_dest_9 = [dest_plate.wells_by_name()[well] for well in 
                       ['F5', 'F6', 'F7', 'F8', 'F9', 'F10', 'F11', 'F12']]
    left_pipette.transfer(transfer_vol, source_plate['A3'], sulfonyl_dest_9, new_tip='once')
    
    # Step 10: SulfonylCl 10 to G01-G08
    sulfonyl_dest_10 = [dest_plate.wells_by_name()[well] for well in 
                        ['G1', 'G2', 'G3', 'G4', 'G5', 'G6', 'G7', 'G8']]
    left_pipette.transfer(transfer_vol, source_plate['B3'], sulfonyl_dest_10, new_tip='once')
    
    # Step 11: SulfonylCl 11 to G09-H04
    sulfonyl_dest_11 = [dest_plate.wells_by_name()[well] for well in 
                        ['G9', 'G10', 'G11', 'G12', 'H1', 'H2', 'H3', 'H4']]
    left_pipette.transfer(transfer_vol, source_plate['C3'], sulfonyl_dest_11, new_tip='once')
    
    # Step 12: SulfonylCl 12 to H05-H12
    sulfonyl_dest_12 = [dest_plate.wells_by_name()[well] for well in 
                        ['H5', 'H6', 'H7', 'H8', 'H9', 'H10', 'H11', 'H12']]
    left_pipette.transfer(transfer_vol, source_plate['D3'], sulfonyl_dest_12, new_tip='once')
    
    # Step 13-20: Transfer Amine compounds to destination plate
    # Step 13: Amine 1
    amine_dest_1 = [dest_plate.wells_by_name()[well] for well in 
                    ['A8', 'B4', 'B12', 'C8', 'D4', 'D12', 'E8', 'F4', 'F12', 'G8', 'H4', 'H12']]
    left_pipette.transfer(transfer_vol, source_plate['A1'], amine_dest_1, new_tip='always')
    
    # Step 14: Amine 2
    amine_dest_2 = [dest_plate.wells_by_name()[well] for well in 
                    ['A7', 'B3', 'B11', 'C7', 'D3', 'D11', 'E7', 'F3', 'F11', 'G7', 'H3', 'H11']]
    left_pipette.transfer(transfer_vol, source_plate['B1'], amine_dest_2, new_tip='always')
    
    # Step 15: Amine 3
    amine_dest_3 = [dest_plate.wells_by_name()[well] for well in 
                    ['A6', 'B2', 'B10', 'C6', 'D2', 'D10', 'E6', 'F2', 'F10', 'G6', 'H2', 'H10']]
    left_pipette.transfer(transfer_vol, source_plate['C1'], amine_dest_3, new_tip='always')
    
    # Step 16: Amine 4
    amine_dest_4 = [dest_plate.wells_by_name()[well] for well in 
                    ['A5', 'B1', 'B9', 'C5', 'D1', 'D9', 'E5', 'F1', 'F9', 'G5', 'H1', 'H9']]
    left_pipette.transfer(transfer_vol, source_plate['D1'], amine_dest_4, new_tip='always')
    
    # Step 17: Amine 5
    amine_dest_5 = [dest_plate.wells_by_name()[well] for well in 
                    ['A4', 'A12', 'B8', 'C4', 'C12', 'D8', 'E4', 'E12', 'F8', 'G4', 'G12', 'H8']]
    left_pipette.transfer(transfer_vol, source_plate['E1'], amine_dest_5, new_tip='always')
    
    # Step 18: Amine 6
    amine_dest_6 = [dest_plate.wells_by_name()[well] for well in 
                    ['A3', 'A11', 'B7', 'C3', 'C11', 'D7', 'E3', 'E11', 'F7', 'G3', 'G11', 'H7']]
    left_pipette.transfer(transfer_vol, source_plate['F1'], amine_dest_6, new_tip='always')
    
    # Step 19: Amine 7
    amine_dest_7 = [dest_plate.wells_by_name()[well] for well in 
                    ['A2', 'A10', 'B6', 'C2', 'C10', 'D6', 'E2', 'E10', 'F6', 'G2', 'G10', 'H6']]
    left_pipette.transfer(transfer_vol, source_plate['G1'], amine_dest_7, new_tip='always')
    
    # Step 20: Amine 8
    amine_dest_8 = [dest_plate.wells_by_name()[well] for well in 
                    ['A1', 'A9', 'B5', 'C1', 'C9', 'D5', 'E1', 'E9', 'F5', 'G1', 'G9', 'H5']]
    left_pipette.transfer(transfer_vol, source_plate['H1'], amine_dest_8, new_tip='always')