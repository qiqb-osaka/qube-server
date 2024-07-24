from qube_box_setup_helper import QubeBoxGroup, QubeBoxSetupHelper
from quel_clock_master import QuBEMasterClient

class QubeSystemSetupHelper:
    def __init__(self, group_id):
        self.box_group = QubeBoxGroup(group_id)

        self.box_setup_helpers = {}
        for device_id in self.box_group.list_devices():
            self.box_setup_helpers[device_id] = QubeBoxSetupHelper(device_id)
        self.master_client = QuBEMasterClient(self.box_group.get_master_ip())

    def list_devices(self):
        return self.box_group.list_devices()

    def get_box_setup_helper(self, device_id):
        return self.box_setup_helpers[device_id]

    def clear_master_clock(self):
        return self.master_client.clear_clock()

    def read_master_clock(self):
        return self.master_client.read_clock()[1]
    
    def read_client_clock(self):
        return {device_id : helper.read_clock() for device_id, helper in self.box_setup_helpers.items()}
    
    def kick_client_clock(self):
        targets = []
        for device_id in self.list_devices():
            client = setup_helper.get_box_setup_helper(device_id).get_sequencer_client()
            targets.append(client.ipaddress)
        return self.master_client.kick_clock_synch(targets)
    
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('target', type=str)
    parser.add_argument('--clear_master', action='store_true')
    parser.add_argument('--sync_all', action='store_true')
    parser.add_argument('--show_clock', action='store_true')
    args = parser.parse_args()
    setup_helper = QubeSystemSetupHelper(args.target)
    
    if args.clear_master:
        setup_helper.clear_master_clock()

    if args.sync_all:
        setup_helper.kick_client_clock()        
        
    if args.show_clock:
        clock_info = {'master': setup_helper.read_master_clock()}
        clock_info.update(setup_helper.read_client_clock())
        for k, v in clock_info.items():
            print(f'{k:<10s}{v:d}')