from qube_box_setup_helper import QubeBoxSetupHelper
import logging
import sys

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('target', type=str)
    parser.add_argument('--hard', action='store_true')
    args = parser.parse_args()

    # Get sequencer client
    setup_helper = QubeBoxSetupHelper(args.target)
    sequencer = setup_helper.get_sequencer_client()

    # Setup logger
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    # reset
    if args.hard:
        sequencer.reset_wave_subsystem()
    else:
        sequencer.clear_and_terminate()